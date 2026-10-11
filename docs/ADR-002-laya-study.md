# ADR 002 — Estudo Laya com contrato e fixtures offline

Data de referência: 2026-10-11. Estado: **B — STUDY; implementação opcional para
revisão**, sem adoção de checkpoint ou integração operacional.

## Contexto

A auditoria `Auditoria-Laya-2026-10-11.md` recomendou estudar decisões finitas,
abstenção, identidade das avaliações e limites de contexto no router existente.
Não demonstrou ganho de qualidade em tarefas Radar PT-BR que justificasse um
novo serviço, MCP, repositório ou classificador no Portal Camaleão. O responsável
autorizou executar a primeira etapa do estudo.

O router atual recebe metadados e aplica uma política estática. Seu contrato
`Prediction` representa quatro probabilidades de tier, esforço, continuidade e
stakes. O preset `router_questions()` de Laya representa dificuldade, domínio,
necessidade de ferramentas e sensibilidade; não há equivalência direta. Uma
tradução entre eles seria uma interpretação nova que precisa de avaliação.

Os projetos existentes continuam responsáveis por política, ledger, evidência,
integrações e revisão. O `Scope` do router é um contrato de caller confiável, não
um autenticador ou autorização de ação. O estudo não amplia capacidades do Hub
ou do Control Plane.

## Decisão

Adicionar somente um módulo em `experiments/laya-study/`, com biblioteca padrão
Python e entrada local congelada. O estudo é removível, sem import obrigatório
de Laya/Torch no core e sem alterar a policy, o ledger ou o adapter Hermes.

O corpus contém 24 casos PT-BR fictícios, divididos em 12 de desenvolvimento e
12 de reserva, com rótulos produzidos por agente. As observações são fixtures
estáticas de quatro tiers (`leve`, `padrao`, `pesado`, `maximo`) e estados de
abstenção, truncamento ou ausência de execução. Elas não são resultados de Laya,
não são encaminhadas à `Prediction` do router e não liberam ferramentas.

`manifest.json` vincula corpus, perguntas incluindo ordem das opções, schema e fixtures
por SHA-256. O runner valida seus dados e imprime somente um relatório JSON de
resultados/metadados, sem os textos dos casos. A descrição em JSON Schema serve
como documentação do contrato; a execução permanece em biblioteca padrão.

Para o baseline, o runner chama a política existente com `RouteInput` a partir
dos metadados e `Scope` local do tenant sintético `laya-study`. Piso e revisão
vêm da configuração do ensaio, nunca das probabilidades. Essa chamada não
cria estado persistente nem demonstra identidade verificada.

## Interpretação das métricas

Baseline e fixture consultam fontes de informação distintas: metadados anotados
versus probabilidades escritas para o ensaio. O texto não é classificado por
nenhum dos lados. As contagens verificam comportamento do contrato e da
comparação com expectativas sintéticas, sem demonstrar ganho de modelo.

Rótulos de agente não são avaliação humana, reserva pequena não é validação
estatística e hashes não provam a verdade de um rótulo. Nenhum resultado daqui
comprova acurácia PT-BR, confiança calibrada, redução de revisão, latência de
checkpoint ou economia de API. Não há checkpoint carregado ou inferência a
contabilizar. Estados sem resultado, abstidos ou truncados continuam explícitos.

A reserva é pública e conhecida neste ensaio. A concordância bruta inclui todo
`observed`; a seletiva inclui somente `gate="passed"`. Ausência de resultado
fica fora das duas. O limiar 0,85 é um exemplo fixo de contrato sem calibração,
não uma promessa de acerto. O candidato nunca é aplicado ao router.

Uma avaliação futura deverá definir informação disponível equivalente para
baseline e candidato, taxonomia humana revisada, critérios de erro e custos,
e conjuntos de desenvolvimento/calibração/reserva antes da medição. Não adaptar
o candidato à reserva para apresentar uma melhora.

## Alternativas consideradas

| Alternativa | Decisão nesta etapa |
|---|---|
| Instalar checkpoints Laya no router | Adiar até revisar cadeia de pesos, ambiente, recursos e tarefa PT-BR |
| Mapear o preset Laya diretamente à `Prediction` | Rejeitar equivalência implícita; os contratos e sentidos diferem |
| Trocar a triagem do Portal Camaleão | Adiar; categorias guiadas e regras já oferecem baseline sem inferência |
| Criar outro router, serviço ou MCP | Não justificado pelo estudo; conservar responsabilidades existentes |
| Usar score como aprovação ou política de execução | Incompatível com a fronteira de confiança; revisão/autorização são externas ao modelo |
| Registrar observações como recibos genéricos no Evidence Kit | Adiar; o kit atual tem contrato documental, não um diário genérico de classificação |

## Consequências e gates posteriores

O resultado imediato é código original pequeno e revisável para testar schema,
identidade dos arquivos, negativos e contagens. Não há download, rede, API paga,
execução n8n, mudança Supabase, serviço na VPS ou benefício comercial demonstrado.

Antes de qualquer inferência real, revisar a licença e a revisão exata de código,
pesos, encoder, tokenizer e dependências; provisionar executor isolado com teto
de memória/tempo/processos e rede controlada. Medir o hardware que será usado;
os números upstream de T4 não são capacidade da VPS do Radar.

Depois, medir erro por categoria, cobertura/abstenção, calibração, truncamento,
cold/warm, memória e custo total em dados autorizados e reserva intocada. Falha
ou sinal indefinido conserva baseline e revisão. Um adapter backend futuro
precisa de contrato próprio, principal autenticado e controles de recursos;
nenhuma observação do modelo pode emitir `Scope` ou habilitar orçamento.

## Autoria, referência e reversão

Contrato, runner, perguntas, corpus, fixtures, testes e documentação deste
estudo são contribuições originais para Carlos Felipe / ofelipepeixoto, sob MIT
conforme a licença vigente do Radar Model Router. Não há código Laya copiado,
presets extraídos ou pesos redistribuídos.

Referência externa: [NandhaKishorM/laya](https://github.com/NandhaKishorM/laya/tree/c4a805b5160621bbfc53417126990a67d3163bc5),
commit `c4a805b5160621bbfc53417126990a67d3163bc5`, versão declarada 0.4.3,
Convai Innovations, Apache-2.0. A autoria original do estudo não transfere a
autoria do engine ou os direitos de modelos e datasets externos. A política
numérica Jev já incorporada mantém sua origem e licença anteriores.

Para reverter, remover o módulo opcional e seus testes, comandos específicos de
CI e referências de documentação. Preservar core, ledger e estado dos usuários.
O estudo não cria banco, reserva, workflow ou serviço externo que precise de
migração ou desativação. Encerrar o estudo se o problema, a qualidade, o custo
ou os controles não justificarem a próxima etapa.
