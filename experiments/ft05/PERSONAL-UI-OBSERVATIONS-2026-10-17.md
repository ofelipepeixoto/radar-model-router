# FT05 — observações manuais na interface pessoal (17/10/2026)

Fonte: saídas textuais compartilhadas pelo operador nesta conversa. As mensagens abaixo são fictícias e foram escolhidas interativamente após observar resultados anteriores. A inferência ocorreu no Colab Pro pela interface `personal_ui.py`; esta página não foi gerada por leitura direta do Drive. Os tempos são os mostrados pela interface, e o primeiro carregamento do modelo não integra esses tempos.

| Caso | Mensagem enviada | Referência de leitura | Saída exibida | Tempo |
| --- | --- | --- | --- | ---: |
| 1 | Minha encomenda ainda não chegou. A entrega estava prevista para hoje e preciso recebê-la antes do fim do dia. | entrega / alta | entrega / alta | 182 ms |
| 2 | Minha encomenda ainda não chegou. A etiqueta da caixa está borrada e receio que ela seja devolvida, mas ainda não tenho uma data definida para recebê-la. | entrega / media | entrega / media | 189 ms |
| 3 | Quero cancelar um pedido que ainda está em separação. Não há horário de envio definido e não preciso resolver isso hoje. | cancelamento / media sugerida inicialmente; leitura ambígua por "não preciso resolver isso hoje" | cancelamento / baixa | 190 ms |
| 4 | Quero cancelar meu pedido, que ainda está em separação. Preciso de ajuda para registrar o cancelamento; não há horário de despacho definido. | cancelamento / media | cancelamento / alta | 220 ms |
| 5 | Quero cancelar meu pedido antes do despacho, que está marcado para daqui a 20 minutos. Preciso impedir o envio agora. | cancelamento / alta | cancelamento / alta | 176 ms |

A interface carregou o modelo, aceitou as mensagens e exibiu categoria, urgência e tempo. A divergência clara no caso 4 reforça a investigação da superpriorização de pedidos de cancelamento sem prazo iminente. O caso 3 deve ser adjudicado por revisores antes de contar como erro, pois a frase final pode sugerir planejamento. Estes cinco casos não formam uma amostra independente nem uma métrica de acerto. Não os incorporar a treino, validação ou teste congelado. O corpus original ainda não tem aprovação humana; o adaptador não está validado para atendimento real.

Próximo passo de qualidade: amostra representativa permitida, com rótulos independentes e relatório privado, conforme `INDEPENDENT-EVAL.md`. O tutorial público em PR #9 ainda precisa de homologação completa em outra conta e Drive.
