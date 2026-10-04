# Autoria e procedência

Os módulos `radar_router/contracts.py`, `policy.py`, `ledger.py`, `service.py`, `adapters.py`, `cli.py`, `evaluate.py`, testes, templates e documentação específicos do Radar Model Router são contribuições originais desenvolvidas para **Carlos Felipe / ofelipepeixoto**.

`radar_router/vendor/jev_policy.py` foi copiado sem alterações de `policy.py` do projeto **Jev Hermes Router**, de **Bruno Okamoto · Pixel Educação**:

- Repositório: https://github.com/okjpg/jev-hermes-router
- Commit: `6742031202f58395bd8b19bd2678581ae93587e2`
- Arquivo: `policy.py`
- Licença: MIT; copyright (c) 2026 Bruno Okamoto.
- Aviso integral em `radar_router/vendor/LICENSE`.

A reutilização efetiva limita-se à função numérica `decide` e constantes associadas, por meio de wrapper original que valida contrato e impõe risco/piso. O módulo upstream também contém ladders, prompts e claims de validação próprios: não são configuração ativa, disponibilidade confirmada nem evidência deste projeto. Não usamos o replay arredondado upstream para identidade de decisões.

Este projeto não é afiliado nem endossado pelo upstream, TypeSafe, Hermes, OpenAI, Composio ou Vercel. Autoria original de terceiros permanece preservada. A criação de um repositório independente não transforma o código de terceiros em autoria exclusiva de Carlos Felipe.
