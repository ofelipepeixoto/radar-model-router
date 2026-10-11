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

## Referência estudada: Laya

`experiments/laya-study/` e `tests/test_laya_study.py` são contratos, corpus fictício, fixtures, código e documentação originais desenvolvidos para Carlos Felipe, sob a licença MIT deste projeto. O estudo referencia [NandhaKishorM/laya](https://github.com/NandhaKishorM/laya), atribuído à Convai Innovations, commit `c4a805b5160621bbfc53417126990a67d3163bc5`, versão declarada 0.4.3, Apache-2.0.

Não foi copiado código, checkpoint ou dataset Laya para este repositório. Seus três patches locais de auditoria não são importados nem aplicados no router. Os dados/outputs de fixture não demonstram qualidade ou execução dos modelos publicados. Um eventual reuso futuro de código/pesos requer preservar suas próprias licenças, autoria e avisos; a licença MIT do Radar não relicencia componentes Apache nem transfere marcas.
