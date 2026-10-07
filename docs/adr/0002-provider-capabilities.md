# ADR 0002 — Capabilities e abstenção offline

Status: estudo, 2026-10-07. Origem conceitual: auditoria FreeLLMAPI no commit
`ffef850fe8553b03f89e2f76be4cb4da2b709378`; implementação original Radar.

O contrato `provider_contract` recebe apenas metadados confiáveis: allowlist,
modo de API, janela de contexto, limite de saída e suporte explícito a JSON
Schema e streaming. Escolhe o primeiro elegível em ordem declarada. Sem
capacidade suficiente ou permissão, abstém. Não há descoberta dinâmica nem
tráfego de rede. JSON válido isoladamente não comprova conformidade ao schema;
o executor futuro precisa validar a saída antes de utilizá-la.

Somente falha confirmada **antes do despacho** permite sugerir outro provider.
Timeout, quota incerta ou saída inválida exigem abstenção e reconciliação;
não se presume custo zero, nem se tenta outra chamada. Uma política de dados
mais restritiva do consumidor deve reduzir a allowlist, nunca ser ampliada
pelo router.

O router mantém a decisão e o ledger SQLite como fonte de reservas. O contrato
offline não autoriza pagamento: um executor autenticado futuro deverá verificar
escopo e preço vigente, reservar o máximo antes da chamada, reconciliar custo
real e preservar estado desconhecido. Não há aqui autorização, execução,
validação de resposta, modelo real, gateway nem mudança no fluxo Hermes/n8n.

Reversão: fechar a PR ou retirar o módulo e os testes; nenhuma migração de
dados foi introduzida.
