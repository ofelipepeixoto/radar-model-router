# Contratos com o ecossistema

A autorização do usuário nesta etapa cobre criar o novo repositório e adaptar/testar seus componentes. Projetos existentes e produção não foram modificados.

## Radar Integration Hub

Exemplo de embedding em ambiente confiável:

```python
from radar_router.contracts import Scope
from radar_router.ledger import Ledger
from radar_router.service import Router

# IDs e pisos resolvidos pelo servidor autenticado, fora do JSON do cliente.
router = Router(Ledger("/volume-privado/router-state"))
decision = router.route(metadata, Scope(tenant="tenant-resolvido", minimum_tier=2, require_review=True))
```

A função não autentica o tenant, executa modelo ou transporta aprovação do Hub. Nenhuma alteração em `src/governance.mjs` ou runtime bridge foi realizada. O JSONL do Hub não vira MCP por interoperar com JSON.

## Hermes

`radar_router.adapters.hermes_request` é uma função pura de contrato. Ela não registra hooks. Só o wrapper confiável pode optar por usá-la. Preencher `Capabilities` com modelos/caps realmente verificados na conta e exigir correspondência exata de provider e api_mode. Fixtures `demo-*` não são modelos reais. O adapter não presume formato de effort por provedor. Teste real Hermes/OAuth permanece pendente.

## n8n

Importar `integrations/n8n/router-input.workflow.json` em laboratório como workflow inativo. Manual Trigger e Code produzem seis metadados sintéticos. Não há webhook, executeCommand, chamada HTTP, credenciais ou tenant no template. Saída `route_input` pode ser salva localmente e encaminhada à CLI por um operador. Conectar a API autenticada do Hub é uma etapa futura.

## Supabase, Sites e Vercel

Reusar Supabase/RLS para interfaces existentes somente quando houver backend governado com contratos definidos. ChatGPT Sites continua preferência para interfaces já existentes. Vercel é opção para novos projetos com necessidade de previews Git/Functions. Não migrar sites existentes como efeito colateral deste laboratório. SQLite atual não deve ser posto em disco efêmero de serverless; produção distribuída exigiria storage externo e reservas equivalentes.
