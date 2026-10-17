# FT05 — revisão do corpus sintético candidato

`candidates-216.jsonl` contém **216 propostas originais, sintéticas e não revisadas**.
São 18 por combinação de quatro categorias e três urgências. A distribuição foi
balanceada deliberadamente para avaliação de contrato; **não representa** o
volume ou a frequência de um atendimento real. Nenhum dado de cliente foi usado.
Os pedidos foram redigidos como mensagens plausíveis, sem inserir “fictício”,
“simulado” ou “de teste” no texto que o modelo receberia; a origem sintética
fica registrada no campo `synthetic`.
Não mesclar com a fixture de 24 casos nem com os nove cenários ambíguos da
`REVIEW-SHEET.md`. O corpus candidato não pode ativar treino diretamente: todos
os registros permanecem `reviewed: false`. O piloto separado `auto_pilot.py`
fixa esta versão por hash e cria um corpus de pesquisa com proveniência
`synthetic_machine_checked`. Esse caminho não atesta revisão humana nem substitui
esta planilha para uso operacional.

## Política proposta `ft05-support-v1`

| Rótulo | Uso nesta proposta | Rever se... |
| --- | --- | --- |
| `entrega` | Envio, prazo, rastreio, pacote, retirada e condição da remessa | O foco principal for cobrança, desistência ou outro assunto |
| `pagamento` | Cobrança, meios de pagamento, parcelas, estorno e recibo | A solicitação principal for cancelar o produto/serviço |
| `cancelamento` | Encerrar, desistir, impedir renovação e conhecer regras de cancelamento | A pergunta for só sobre um valor já cobrado |
| `outro` | Conta, acesso, segurança, interface, catálogo e informação geral | Houver intenção principal em alguma das três categorias anteriores |

`alta`: consequência imediata, prazo explícito de hoje/iminente ou incidente
ativo de acesso. `media`: problema atual que requer atendimento, sem prazo
iminente. `baixa`: informação geral ou planejamento futuro. Menção a entrega,
pagamento ou cancelamento **não torna** o caso urgente por si só. Pedidos com
múltiplas intenções pedem decisão explícita do revisor ou exclusão; não inferir
prioridade a partir de uma palavra solta.

Esta política pode divergir dos rótulos propostos na fixture original de 24
casos, que é uma demonstração não revisada. Exemplos: “como cancelar” e
“quando chega” não recebem automaticamente urgência alta aqui. Antes de
promover, o revisor precisa aceitar a política ou ajustar e versioná-la.

## Auditoria técnica desta proposta

- 216 IDs únicos, 216 textos normalizados únicos, 212 grupos propostos.
- Quatro pares de paráfrases intencionais compartilham grupo: IDs `01` e `02`
  em `entrega/alta`, `pagamento/alta`, `cancelamento/alta` e `outro/alta`.
- Outros temas podem merecer **grupos maiores** após leitura humana: cobrança
  duplicada em `pagamento/alta-01,02,05,13`; renovação iminente em
  `cancelamento/alta-01,02,06,11,14,17`; acesso suspeito em
  `outro/alta-01,02,05,12,14`; exposição entre perfis em
  `outro/alta-03,11,17`. Estes IDs são pistas de revisão, não grupos já
  aprovados. Agrupá-los pode mudar a composição do teste congelável.
- Nenhum texto normalizado coincide com a fixture de 24 ou os nove cenários.
- Nenhum par em grupos diferentes atingiu similaridade textual ≥ 0,77 pelo
  `SequenceMatcher`. Essa heurística **não detecta equivalência semântica**.
- O split preliminar, antes de revisão/exclusões, contém 153 treino, 21
  validação e 42 teste. As 12 combinações de categoria/urgência aparecem no
  teste após curadoria do ID do caso de expedição **antes de qualquer treino**.
  O split pode mudar se o revisor excluir casos ou alterar grupos; faça uma
  última inspeção de distribuição antes de congelá-lo. `entrega/alta` tem só
  um caso no teste preliminar, o que impede uma conclusão estável por essa
  combinação.
- Pontos de decisão especialmente úteis: reembolso em
  `c26-cancelamento-baixa-08` (cancelamento versus pagamento); segurança de
  conta em `c26-outro-alta-*` (categoria residual com urgência alta); a
  diferença entre dúvida geral e incidente ativo nos casos de prazo.

O resultado acima é revisão **técnica e editorial assistida por IA**; não é
revisão humana, validação de representatividade ou qualidade de um modelo.

## Como revisar no Drive da conta Colab Pro

1. Faça uma cópia de `candidates-216-review-template.csv` no Drive e abra-a
   em uma planilha. Essa cópia preenchida deve ficar privada; `reviewer_id`
   é identificador interno sem nome, e não precisa ir ao repositório público.
2. Leia cada `prompt`. Confira `proposed_category`, `proposed_urgency` e
   `proposed_group_id` pela política acima. Em `final_*`, mantenha ou corrija
   rótulos/grupo. Paráfrases do mesmo caso devem ter o mesmo grupo; casos
   independentes devem ter grupos diferentes. Não reproduza variações triviais
   apenas para aumentar a contagem.
3. Em **todas** as 216 linhas, escolha `decision=approve` ou `exclude`, escreva
   uma justificativa em `reason` (mínimo 12 caracteres), um identificador
   interno em `reviewer_id` e mantenha `policy_version=ft05-support-v1`.
   Caso a política precise mudar, revise o código/versão antes de aprovar;
   não edite o campo de versão isoladamente.
4. Exporte a planilha preenchida como CSV UTF-8. O comando abaixo gera o
   JSONL revisado em destino novo, após verificar IDs, hash do corpus,
   conteúdo, decisões, rótulos, grupos e mínimo de 200 aprovados:

   ```sh
   python3 review_candidates.py promote candidates-216.jsonl \
     /caminho/privado/dataset-reviewed.jsonl \
     /caminho/privado/candidates-216-reviewed.csv
   ```

   Se preferir operar só pelo ChatGPT, forneça a cópia preenchida do CSV para
   que o comando seja executado aqui. **Não** marque `reviewed: true` no
   JSONL candidato. O verificador exige campos completos, mas não consegue
   provar que uma pessoa realmente leu cada linha.
5. Depois da promoção, o notebook FT05 já salvo no Drive poderá apontar
   `DATASET_PATH` para esse `dataset-reviewed.jsonl`. Execute primeiro o
   congelamento (`FREEZE_REVIEWED`), confira distribuição e hashes, e só depois
   considere dependências e treino. Deixe essas flags em `False` até a
   revisão estar concluída.

Para reproduzir a planilha vazia em uma cópia de trabalho:

```sh
python3 review_candidates.py audit candidates-216.jsonl
python3 review_candidates.py export candidates-216.jsonl /tmp/review-template.csv
```

Os hashes da planilha publicada se referem exatamente ao
`candidates-216.jsonl` desta PR. Uma edição do corpus invalida a planilha:
gere uma nova versão e recomece a revisão. Nunca publique respostas de
clientes, credenciais ou a planilha preenchida no repositório público.
