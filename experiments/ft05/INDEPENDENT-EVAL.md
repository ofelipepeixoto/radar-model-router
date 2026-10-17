# FT05 — diagnóstico de urgência e avaliação independente

## O que os resultados permitem concluir

O teste sintético congelado do piloto acertou 32/34. Seus dois erros conhecidos
eram `media` → `alta` em entrega e cancelamento. No diagnóstico posterior,
feito **depois** de ver esses erros, houve 20/24 acertos, com 4/8 casos de
urgência média classificados como alta. As quatro divergências são
`s03-entrega-media`, `s15-cancelamento-media`, `s16-cancelamento-media` e
`s21-outro-media`. Categoria e formato JSON estavam corretos nos 24 casos.
Os arquivos do diagnóstico no Drive não foram inspecionados diretamente aqui;
os resultados vêm da saída textual compartilhada pelo operador.

Uma inspeção textual do corpus sintético automático de 208 registros encontrou
`hoje` em 24 exemplos de alta e nenhum de média/baixa; `agora` em 11 de alta
e nenhum de média/baixa. São contagens de **substring no texto normalizado**,
não uma análise causal. A hipótese é que o modelo aprendeu pistas de prazo
frequentes nos exemplos sintéticos e tende a elevar problemas atuais mesmo
quando o texto afasta um prazo iminente. Os seis erros observados apoiam
investigar essa hipótese; não demonstram seu mecanismo. A prevalência real de
urgência, a taxa de falso alarme e o custo operacional ainda são desconhecidos.

Não usar os 24 casos posteriores, nem o teste congelado, para escolher novos
rótulos, ajustar o adaptador ou declarar melhoria. `reviewed` dos 216
candidatos continua `false`. Nenhuma alteração de treino é feita neste fluxo.

## Protocolo de avaliação privada

1. O responsável pelos dados cria **fora do repositório** um CSV UTF-8 com
   cabeçalho exato `id,text`: uma linha por pedido real, previamente
   anonimizado e autorizado, de um período e canal definidos. Incluir todos os
   pedidos elegíveis daquele recorte, inclusive casos difíceis, sem selecionar
   por rótulo ou pelo desempenho do modelo. IDs não podem conter nomes ou
   números de conta. O scanner de e-mail, números longos e tokens do script é
   apenas um alerta; **não anonimiza**. Revisar permissões e retenção da fonte.
2. `prepare` valida IDs e textos, rejeita repetição exata normalizada e
   coincidência exata com os textos sintéticos conhecidos, sorteia 60 mensagens
   com semente fixa e registra hash, tamanho da população e descrição do
   recorte. A fonte real não é publicada no GitHub. A amostra aleatória preserva
   aproximadamente a distribuição da população, mas 60 casos podem ser
   insuficientes para estimar classes raras com precisão.
3. Entregar `reviewer-a.csv` e `reviewer-b.csv` **separadamente** a duas pessoas
   habilitadas. Cada uma lê a política em `CANDIDATE-REVIEW.md` e preenche
   `categoria`, `urgencia`, `reason`, `reviewer_id` sem ver o adaptador, a
   resposta da outra pessoa, o teste sintético ou o resultado da avaliação.
   Valores: `entrega|pagamento|cancelamento|outro` e `alta|media|baixa`.
   Para intenção inconclusiva, usar `indefinida` nos dois campos e explicar.
   Um terceiro revisor, distinto dos dois, preenche `adjudication.csv`
   **somente** nas linhas em que os dois rótulos divergirem. O script rejeita
   linhas faltantes, conflitos sem decisão e revisão pelo mesmo ID.
4. Executar `seal` antes de `predict`. O selo guarda hashes das fichas e do
   ouro e não pode ser sobrescrito. Rótulos `indefinida` contam na cobertura da
   amostra, mas não no denominador de acerto. A presença de IDs nas fichas é
   uma declaração auditável, **não prova técnica** de que pessoas distintas
   fizeram a revisão.
5. `predict` carrega o adaptador salvo e o modelo base na revisão fixada,
   confere corpus/split congelados e versões, faz apenas inferência e grava
   previsões e hashes em pasta privada nova. `score` exige o selo e o manifesto
   de inferência correspondente; informa acerto, JSON válido, matrizes de
   categoria/urgência, `false_high` e `missed_high`. Nenhum passo treina.

Exemplo de execução no Colab Pro, com o Drive já montado, dependências
validadas e a branch desta PR clonada; caminhos são exemplos privados:

```sh
python3 experiments/ft05/independent_eval.py prepare \
  /content/drive/MyDrive/FT05/private/source-anonymized.csv \
  /content/drive/MyDrive/FT05/private/eval-001 \
  --n 60 --seed 3407 \
  --frame 'Pedidos de suporte do canal X, 01 a 15/10/2026 UTC, todos os elegíveis'

# Após duas revisões reais e adjudicação dos desacordos:
python3 experiments/ft05/independent_eval.py seal \
  /content/drive/MyDrive/FT05/private/eval-001 \
  /content/drive/MyDrive/FT05/private/eval-001-sealed

python3 experiments/ft05/independent_eval.py predict \
  /content/drive/MyDrive/FT05/private/eval-001 \
  /content/drive/MyDrive/FT05/private/eval-001-sealed \
  /content/drive/MyDrive/FT05/piloto-auto-001/run-002-g4 \
  /content/drive/MyDrive/FT05/private/eval-001-predictions \
  --corpus /content/drive/MyDrive/FT05/piloto-auto-001/synthetic-machine-checked.jsonl \
  --frozen /content/drive/MyDrive/FT05/piloto-auto-001/frozen

python3 experiments/ft05/independent_eval.py score \
  /content/drive/MyDrive/FT05/private/eval-001 \
  /content/drive/MyDrive/FT05/private/eval-001-sealed \
  /content/drive/MyDrive/FT05/private/eval-001-predictions/predictions.json \
  /content/drive/MyDrive/FT05/private/eval-001-report
```

Não copiar mensagens, fichas, previsões ou erros de clientes para este
repositório público. Um segundo conjunto direcionado a fronteiras de urgência
pode ser construído **separadamente e antes de inferência**, mas sua taxa não
deve ser combinada com a da amostra aleatória. O resultado de 60 mensagens é
exploratório: documentar prevalência, desacordos e exclusões, e definir em
separado custos e limiares de falso alarme e de urgências perdidas antes de
qualquer teste com tráfego real. A avaliação não dispensa os gates de dados de
treino nem autoriza ativação no roteador.
