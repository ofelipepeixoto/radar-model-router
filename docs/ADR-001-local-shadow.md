# ADR 001 — Roteamento local em modo sombra

Contexto: a auditoria Jev identificou gaps de schema, identidade, privacidade e gasto. O usuário autorizou repositório independente com autoria e adaptação ao ecossistema.

Decisão: criar pacote Python mínimo, baseline estático, política upstream MIT isolada, metadados sem texto, decisões SQLite e ledger experimental; não incluir cliente HTTP pago nem deployment. Capabilities precisam ser fornecidas por caller confiável.

Alternativas: habilitar plugin original; reimplementar transporte pago imediatamente; colocar middleware no Hub operacional; criar novo serviço distribuído. Elas aumentariam superfície e dependências antes de medir benefício.

Consequências: entrega sem custo de API e testes reproduzíveis; integração real e economia ainda pendentes. Autoria original de Carlos Felipe coexiste com créditos MIT de Bruno Okamoto. SQLite só serve host com volume persistente. Composio/Vercel entram como opções documentadas, sem runtime obrigatório.
