# Radar Model Router

Roteamento local de modelos para experimentos do ecossistema **ofelipepeixoto**, desenvolvido por **Carlos Felipe**. A versão 0.1.0 recomenda um nível de modelo conforme tarefa, continuidade e risco. Ela **não chama modelos nem serviços externos**, não executa ferramentas e não concede autorização.

Este é um repositório independente com componentes originais e uma política numérica MIT atribuída ao [Jev Hermes Router](https://github.com/okjpg/jev-hermes-router). Não representa autoria original exclusiva: leia [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Começar sem chave e sem custo de API

Requer Python 3.11 ou superior. Não é necessário instalar dependências para executar pelo checkout.

```bash
python3 -m unittest discover -s tests -v
python3 -m radar_router.cli --state-dir .router-state < examples/input.json
python3 -m radar_router.evaluate
```

Saída da entrada de exemplo: tier `padrao`, esforço `medium`, modo sombra, APIs pagas desabilitadas. Rodar novamente a mesma entrada recupera a mesma decisão. Mudar os metadados usando o mesmo tenant/sessão/turno rejeita a operação até a retenção expirar. Use outro turno para uma nova solicitação.

## O que está implementado

- Regras estáticas locais como baseline; replay opcional da política Jev com probabilidades estritamente validadas.
- Risco alto ou revisão exigida pelo caller confiável impõem tier máximo e revisão humana. Isso é recomendação, não autorização.
- Identidade composta tenant/sessão/turno, persistência SQLite e deduplicação transacional.
- IDs pseudonimizados por HMAC; nenhum prompt aceito ou armazenado pelo serviço.
- Limite de entrada de 8 KiB, schema exato, rejeição de NaN, booleanos numéricos e chaves JSON duplicadas.
- Retenção de decisões de sete dias, com limpeza ao próximo acesso; não há timer autônomo.
- Ledger experimental de orçamento inteiro em microunidades, reserva atômica, reconciliação e preservação de resultados desconhecidos.
- Adapter puro para shape de request Hermes, desabilitado por padrão; valida provider, api_mode e capabilities explícitas.
- Contrato offline de elegibilidade de provider, capacidades e abstenção conservadora; ver [ADR 0002](docs/adr/0002-provider-capabilities.md).
- Workflow n8n **inativo**, que apenas produz uma entrada sintética para o contrato; não chama Python nem usa credenciais.
- CI configurado para Python 3.11 e 3.12, testes de contrato e execução do exemplo n8n em Node.

## Estado de validação

**53 testes locais passaram** e o [CI remoto](https://github.com/ofelipepeixoto/radar-model-router/actions/runs/37170716005) aprovou Python 3.11 e 3.12, incluindo oito casos sintéticos e o contrato n8n → Python. Detalhes e commit verificado em [docs/VALIDATION.md](docs/VALIDATION.md). Hermes e n8n reais continuam não homologados. Sem economia, qualidade de LLM ou disponibilidade real de modelos comprovadas.

## Entrada e confiança

```json
{"session":"demo-session","turn":"demo-turn","task":"draft","risk":"low","current_tier":2,"continuation":false}
```

Tarefas: `lookup`, `draft`, `analysis`, `architecture`. Risco: `low` ou `high`. IDs têm até 64 caracteres. Nenhum texto livre, segredo ou tenant pode entrar no JSON.

A CLI é um laboratório local controlado pelo operador. `Scope` deve ser construído pelo backend autenticado no uso embutido; o dataclass não autentica usuários. Risco declarado pelo cliente pode aumentar o controle, mas não substituir o piso/revisão definidos pelo backend. Não expor esta CLI ou ledger diretamente como API multiusuário.

## Encaixe no ecossistema

| Destino | Estado nesta versão |
|---|---|
| Radar Integration Hub | API Python local de recomendação disponível; nenhuma alteração no Hub |
| radar-evidence-kit | Metodologia de corpus/hashes; integração documental, não SDK acoplado |
| radar-n8n-projetos | Template de entrada sintética; execução na instância não homologada |
| Hermes Agent | Função pura de request testada com fixtures; hooks reais não instalados |
| Jurídico/documental/financeiro | Fora do piloto; revisão e controles existentes preservados |
| Composio | Opção de conexão de serviços com identidade e allowlist; não integrado ao runtime |
| Vercel | Opção para interfaces/previews futuros; este SQLite precisa volume durável |

Leia [docs/ECOSYSTEM.md](docs/ECOSYSTEM.md) e [docs/PLUGINS.md](docs/PLUGINS.md).

## Limites

Sem servidor HTTP, MCP, geração LLM, classificador externo, deploy VPS/Vercel ou workflow ativado. Não existe flag de ambiente que habilite API paga. O ledger é um componente testado para integração futura: não substitui executor autenticado, limite de tokens, preço atual verificado e reserva ligada à chamada real. Não há manutenção distribuída ou SLA.

Estado local contém chave HMAC e banco, fora do Git. Inicializar um Ledger antes de iniciar workers. Fazer backup consistente do banco **e** da chave; perder a chave perde a associação às decisões/reservas. Reservas desconhecidas não expiram automaticamente. Consulte [SECURITY.md](SECURITY.md).
