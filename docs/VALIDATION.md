# Validação — versão 0.1.0

Execução local em 03/10/2026 (America/Sao_Paulo; 04/10 UTC), Python 3.12, dados sintéticos. Nenhuma chamada de modelo/serviço paga foi executada.

| Check | Resultado |
|---|---|
| `python3 -m unittest discover -s tests -v` | 53 testes, OK |
| `python3 -m radar_router.evaluate` | 8/8 casos sintéticos corretos, 0 API calls |
| `node tests/n8n-contract.cjs` | Code do template → CLI Python, PASS |
| Validador estrutural da skill n8n | estrutura_valida=true, homologacao_n8n=false |
| CLI com examples/input.json | tier padrao, medium, shadow=true, paid_enabled=false |
| `python3 -m compileall -q radar_router tests` | OK |
| Comparação do vendor com upstream | Arquivo e licença sem alterações |
| Repositório GitHub | Criado em https://github.com/ofelipepeixoto/radar-model-router; independente, não fork |
| GitHub Actions | CI aprovado em Python 3.11 e 3.12 para o commit a8bfc343560377b50bd1df2d52d282620b1907da; testes, evals, CLI, contrato n8n e compile passaram |
| Hermes/OAuth/n8n real | Não instalado, conectado ou homologado |
| Vercel | Consulta autenticada retornou zero projetos; nenhum deploy |
| Composio GitHub | Conexão ativa confirmada para ofelipepeixoto, criação do repositório concluída |

## Auditoria da adaptação

O código original foi limitado à política pura upstream. Transporte, credenciais em chat, hooks globais, ladders operacionais e logs de texto do plugin não foram incorporados ao runtime. O wrapper original valida números/distribuição, impõe risco/revisão e não usa replay arredondado para idempotência.

Testes confirmam: contrato sem prompt/chave, isolamento de tenants/sessões, concorrência em decisões e budget, preservação de reserva desconhecida, reconciliação tardia e overrun persistido. O adapter é puro e opt-in, limitado ao provider/API mode/modelo declarados; não executa tools. A auditoria não prova ausência universal de falhas, qualidade de LLM, economia ou adequação a produção.

Riscos residuais: caller confiável precisa autenticar; SQLite requer host/volume seguro; início concorrente deve ocorrer após inicialização única; caminho pai precisa ser confiável; retenção é oportunística; reservas não possuem manutenção automática; capacidades reais e integrações externas continuam pendentes. Não usar ledger em functions efêmeras.

## Evidência remota

Execução aprovada: https://github.com/ofelipepeixoto/radar-model-router/actions/runs/37170716005, commit `a8bfc343560377b50bd1df2d52d282620b1907da`. Ambos os jobs `test (3.11)` e `test (3.12)` concluíram com success. Os seis checks funcionais passaram nas duas versões; nenhum provider foi chamado. A atribuição do commit está associada à conta `ofelipepeixoto`.

## Próximo gate

Para operação real, homologar caller autenticado, capacidades e wrappers no ambiente isolado. API paga e workflows operacionais continuam desabilitados. A confirmação de CI não constitui homologação Hermes/n8n nem economia real.
