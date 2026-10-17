# FT05 — resultado do diagnóstico posterior `posthoc-stress-001`

## Origem da evidência

O operador executou no Colab Pro, com a GPU G4, o avaliador do commit
`741aaad115ef9e122f31d5badba732b015599ad1` sobre o adaptador salvo em
`run-002-g4`. A saída textual foi compartilhada na conversa em 16/10/2026.
O avaliador gravou `predictions.json`, `report.json` e `manifest.json` na pasta
privada `posthoc-stress-001` do Drive. Esses três arquivos **não foram lidos
diretamente neste repositório**; os números abaixo vêm da saída compartilhada.

O corpus diagnóstico tem 24 mensagens sintéticas escritas após observar os
erros do teste congelado. São duas por cada combinação das quatro categorias e
três urgências. Não houve novo treino, alteração do adaptador ou avaliação cega.

## Resultado observado

| Medida | Resultado |
| --- | ---: |
| Acerto exato | 20/24 (83,3%) |
| Saída em JSON válido | 24/24 (100%) |
| Categoria correta | 24/24 (100%) |
| Urgência `alta` correta | 8/8 |
| Urgência `media` correta | 4/8 |
| Urgência `baixa` correta | 8/8 |

As quatro divergências elevaram `media` para `alta`, mantendo a categoria:

| ID | Categoria | Esperado | Produzido |
| --- | --- | --- | --- |
| `s03-entrega-media` | `entrega` | `media` | `alta` |
| `s15-cancelamento-media` | `cancelamento` | `media` | `alta` |
| `s16-cancelamento-media` | `cancelamento` | `media` | `alta` |
| `s21-outro-media` | `outro` | `media` | `alta` |

O padrão é coerente com os dois erros vistos antes no teste sintético congelado:
pedidos atuais sem prazo iminente podem ser superpriorizados. O diagnóstico
posterior **não é uma nova estimativa independente de qualidade**, porque foi
desenhado depois desses erros. Não ajustar o modelo ou a política usando esses
24 casos como alvo de otimização. Para qualquer uso com clientes, ainda faltam
rótulos revisados por pessoas, dados representativos, avaliação independente e
critérios operacionais de encaminhamento. `human_reviewed` permanece `false`.

