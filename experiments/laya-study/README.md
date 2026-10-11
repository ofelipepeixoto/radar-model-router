# Laya — estudo offline de decisões consultivas

Este módulo implementa a primeira etapa **B — STUDY** da auditoria Laya: validar
um contrato de observações e comparar fixtures com a política estática existente.
Não executa Laya ou qualquer outro modelo. As probabilidades são valores
sintéticos escritos para testar o estudo, não respostas de um checkpoint.

O código, perguntas, corpus, fixtures e documentação deste módulo são
contribuições originais para **Carlos Felipe / ofelipepeixoto**, sob a licença
MIT vigente neste repositório. A referência externa está descrita abaixo.

## Executar

Python 3.11 ou superior, somente biblioteca padrão. A partir da raiz do checkout:

```bash
python experiments/laya-study/study.py
python -m unittest discover -s tests -v
```

O primeiro comando lê os arquivos locais do estudo e imprime um relatório JSON
em stdout. A saída compara as fixtures com o baseline e identifica a origem
sintética das observações. Ela não contém os textos dos casos. O segundo comando
executa os testes do repositório, incluindo as regressões deste contrato quando
presentes no checkout. Testar o contrato não mede a qualidade de um modelo.

Não é necessário instalar pacote, definir chave ou iniciar serviço. O módulo
não cria ledger, reserva financeira, servidor, ferramenta MCP ou workflow n8n.
Para persistir uma execução local, o operador pode redirecionar stdout para um
arquivo fora dos caminhos rastreados; o relatório continua sendo evidência do
ensaio sintético, sem comprovar inferência.

## Arquivos e origem dos dados

| Arquivo | Papel |
|---|---|
| `corpus.json` | 24 casos fictícios PT-BR: 12 de desenvolvimento e 12 de reserva; textos, metadados e expectativas anotados por agente |
| `questions.json` | Taxonomia original dos quatro tiers e sua apresentação, incluindo a ordem das opções |
| `observations.fixture.json` | Observações sintéticas: probabilidades, abstenção, truncamento ou ausência de execução |
| `manifest.json` | SHA-256 dos bytes de corpus, perguntas, fixtures e schema, vinculando as entradas desta comparação |
| `contract.schema.json` | Descrição legível por máquina do contrato do estudo; não instala um validador externo |
| `study.py` | Validação e relatório, em biblioteca padrão, separados do runtime do router |

Os tiers são `leve`, `padrao`, `pesado` e `maximo`. Os casos e rótulos foram
produzidos por agente para esta implementação e **não receberam validação
humana especializada**. Os 12 casos de reserva demonstram a separação dos
conjuntos; seu tamanho e origem não estabelecem independência estatística,
representatividade dos clientes ou qualidade PT-BR de Laya. Não ajustar rótulos
ou limiares a partir da reserva para alegar ganho posterior.

A reserva deste ensaio contém fixtures públicas conhecidas, não um holdout
independente para avaliar um modelo real. Os metadados `trusted` são configuração
sintética local, não controles de um backend autenticado homologado.

O manifesto detecta mudanças nos arquivos vinculados. Ele não é assinatura,
identidade do anotador ou prova de que os rótulos estão corretos. Uma alteração
de perguntas, ordem das opções, corpus ou fixtures cria outro experimento:
registrar a mudança e seus novos hashes, preservando a origem da comparação.
O fingerprint canônico das perguntas nas observações é separado do hash dos
bytes em `manifest.json`; ambos preservam a ordem explícita das opções. O
relatório também identifica o código do estudo e os módulos da política por hash.

## O que a comparação significa

O baseline chama `policy.decide` com `RouteInput` formado pelos **metadados** do
caso e um `Scope` local construído pelo runner. O `Scope` usa o tenant sintético
`laya-study`; piso e revisão representam configuração confiável do laboratório.
Essa construção não autentica pessoas nem demonstra membership de um cliente.

A política já existente usa tarefa, risco, continuidade, tier atual e controles
confiáveis. Ela não interpreta o texto PT-BR. O outro lado é uma tabela estática
de probabilidades anotadas em `observations.fixture.json`; não lê o texto com
um classificador. Portanto, a comparação verifica contratos, contagem de
resultados, tratamento de abstenção e consistência com expectativas sintéticas.
Ela **não é uma disputa de desempenho entre a política e Laya com os mesmos
inputs**, nem evidência de acurácia, calibração, latência ou economia de API.

As observações de tier são propostas consultivas do estudo. Elas não são
convertidas em `Prediction`, não são fornecidas à política numérica Jev e não
substituem o resultado do router. As perguntas de `router_questions()` de Laya
produzem dificuldade, domínio, necessidade de ferramentas e sensibilidade;
esses campos não correspondem diretamente ao contrato `Prediction` do Radar.

`fixture_agreement_with_baseline` e a matriz de confusão comparam o argmax bruto
de todos os registros `observed`, inclusive os abstidos/truncados.
`selective_fixture_agreement` usa somente `gate="passed"`; `not_run` fica fora
das duas concordâncias. Nenhuma dessas métricas é acurácia de Laya. O campo
`critical_underroute_fixtures` conta propostas brutas abaixo de um baseline que
exige revisão; ele não representa ações executadas.

O vetor de probabilidades sempre segue a ordem canônica dos labels
`[leve, padrao, pesado, maximo]`. `option_order` registra a apresentação da
pergunta; não permuta esse vetor. Empates usam o primeiro label canônico.
O gate aplica abstenção, contexto, revisão, pisos e continuidade antes do
limiar ilustrativo fixo `candidate_min_probability=0.85`, sem calibração.
`abstention="passed"` sozinho não faz o gate passar. Mesmo `gate="passed"`
nunca aplica o candidato: `effective_source="baseline"` permanece fixo.
Probabilidade elevada não comprova correção nem concede autorização.

## Limites e segurança

- Somente dados sintéticos rastreados. Não substituir textos por prompts,
  documentos de clientes, credenciais ou identidades reais.
- Sem rede, download de pesos, execução de inferência, SDK pago ou dependência
  obrigatória de Laya/Torch no core. O estudo não conecta Hub, Supabase ou n8n.
- Os arquivos são lidos como dados. Paths, endpoints, credenciais e ferramentas
  não são definidos por suas probabilidades ou pelos textos do corpus.
- O runner valida o contrato local; não oferece sandbox para arquivos ou código
  hostis, autenticação ou operação multiempresa.
- O relatório de stdout omite os textos dos casos. Isso não anonimiza os arquivos
  de entrada e não torna seguro versionar dados reais.

## Próximos gates

1. Escolher uma necessidade concreta e uma taxonomia estável; obter revisão
   humana de exemplos e expectativas PT-BR. Definir métricas, erros críticos e
   critérios de abandono antes de observar a reserva.
2. Para uma comparação de qualidade, dar ao baseline e ao candidato o mesmo
   conjunto de informações permitido. Registrar qualquer uso de metadados
   fornecidos pelo operador; a comparação atual não atende esse gate.
3. Antes de inferência real, revisar código, dependências, licença e revisões
   exatas de pesos, encoder e tokenizer. Provisionar executor isolado com limites
   de memória, processo, tempo e rede; medir o hardware disponível.
4. Separar desenvolvimento, calibração e reserva. Registrar checkpoint, revisão,
   digest, dtype, perguntas/ordem, truncamento e estados de abstenção. Medir
   erros por categoria, cobertura, calibração, cold/warm e custo total.
5. Só propor adapter backend se houver ganho justificável. Falha, resultado
   indefinido ou contexto cortado preservam o baseline e encaminham revisão.
   Autorização, identidade e orçamento continuam fora do modelo.

Esses gates são trabalho futuro. Nenhuma inferência, avaliação humana, execução
de n8n ou implantação é liberada por passar nos testes deste módulo. Consulte a
[ADR 002](../../docs/ADR-002-laya-study.md) e a
[segurança do router](../../SECURITY.md).

## Referência e reversão

Referência de estudo: [NandhaKishorM/laya](https://github.com/NandhaKishorM/laya/tree/c4a805b5160621bbfc53417126990a67d3163bc5),
commit `c4a805b5160621bbfc53417126990a67d3163bc5`, versão declarada 0.4.3,
desenvolvido por Convai Innovations; código upstream sob Apache-2.0. Nenhum
código, preset, peso ou dataset Laya foi extraído para este módulo. A licença MIT
do Radar não altera termos, marcas ou autoria de Laya e suas dependências.

Reversão: remover o diretório opcional, seus testes, referências de documentação
e comandos específicos de CI. Preservar a policy, os contratos e o ledger já
existentes. Não há estado externo, serviço, workflow ou banco do estudo para
desativar. A remoção do ensaio não exige migrar dados do router.
