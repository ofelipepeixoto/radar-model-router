# FT05 — experimento incremental para radar-model-router

Preparação original, offline, sem alterar política de roteamento, ledger ou providers.
Adição isolada em `experiments/ft05/`, baseada na main
`f9533a43af86729696c5cd9980adec223beb3410`. A PR #1 foi comparada: seus
arquivos de capabilities/provider são independentes deste experimento e não
foram copiados ou alterados. Mantém trabalhos posteriores da main.

Na entrega original, 91 testes existentes do router e 8 testes deste experimento
passaram em Python 3.12.14. Contrato Node → Python existente também passou.
Treino GPU, inferência de modelo, GGUF/Ollama/llama.cpp permanecem não executados.

## Executar a parte verificada

A partir deste diretório: Python 3.11+, biblioteca padrão, sem instalação:

```sh
python3 -m unittest discover -s tests -v
python3 ft05.py synthetic.jsonl /tmp/ft05-new-run
python3 train.py synthetic.jsonl
```

Use um diretório de saída inexistente. `prepared/` registra a execução desta
entrega: 18 treino, 2 validação, 4 teste. `synthetic.jsonl` contém 24 exemplos
fictícios e **não revisados por humano**, insuficientes para treino. Não inflar
o corpus com variações triviais para alcançar 200. O gerador da fixture é
reprodutível, mas não produz evidência de qualidade operacional.

## Contrato de dados e split

Cada linha tem `id`, `group_id`, `synthetic: true`, `reviewed: boolean` e duas
mensagens `user`/`assistant`; a resposta é JSON estrito com `categoria` e `urgencia`.
Metadados são descartados ao renderizar as mensagens para o treino. Rótulos e
chaves duplicadas inválidos são recusados. O limite recomendado de 200–500 é
um gate deste experimento derivado do guia, não requisito oficial do modelo.

O split une grupos e textos normalizados transitivamente antes de particionar;
é invariável à ordem das linhas. Paráfrases precisam receber `group_id` curado;
não há detector semântico de duplicação. O particionamento é por número de
grupos, sem promessa de estratificação. Revisar distribuição por classe antes
de treino. Preserve a saída do split: mudanças no corpus podem mudar partições.
O scanner de padrões de e-mail/números/segredos é heurístico, **não anonimiza**.
Neste escopo só dados sintéticos são permitidos. `synthetic` é declaração do
operador, não prova técnica de origem.

## Corpus candidato para revisão

[`CANDIDATE-REVIEW.md`](CANDIDATE-REVIEW.md) documenta 216 exemplos
sintéticos **não revisados**, a política proposta para categoria/urgência,
grupos, auditoria técnica e a ficha CSV de decisão por caso. O utilitário
`review_candidates.py` gera a planilha e só promove para um JSONL treinável
com decisões completas e ao menos 200 casos aprovados. A revisão humana
efetiva não é inferível dos campos preenchidos. A cópia editada da planilha
fica privada, fora deste repositório público. O notebook Colab existente
contém também um piloto automático separado, descrito abaixo. A revisão humana
continua necessária para qualquer reivindicação de qualidade operacional.

## Piloto sem planilha: corpus sintético com checagem automática

Para experimentar o treino e a comparação no Colab Pro sem editar 216 linhas,
use a branch `feat/ft05-automated-synthetic` e o notebook atualizado. O script
`auto_pilot.py` fixa o SHA exato dos 216 candidatos, exclui oito pedidos
ambíguos com motivos em código, agrupa famílias semânticas conhecidas e produz
208 registros sintéticos com `reviewed: false`. Valida IDs, esquema, rótulos,
unicidade, grupos, tamanho e cobertura de todas as 12 combinações de rótulos
em treino, validação e teste. A partição é feita por grupo e gravada com hashes.

Teste local, sem Drive, rede, GPU ou instalação:

```sh
python3 -c "from auto_pilot import write_auto_dataset; print(write_auto_dataset('/tmp/ft05-synthetic-auto.jsonl'))"
python3 ft05.py /tmp/ft05-synthetic-auto.jsonl /tmp/ft05-auto-frozen --synthetic-auto
python3 train.py /tmp/ft05-synthetic-auto.jsonl
```

Escolha destinos inexistentes; se um arquivo já existir, o gerador só o aceita
quando os bytes conferirem exatamente. A execução no Colab usa uma pasta
exclusiva no Drive e grava `auto-audit.json`, dataset, manifesto e as três
partições. O manifesto registra `review_mode: synthetic_machine_checked` e
`human_reviewed: false`. O caminho de 200–500 casos efetivamente revisados
continua separado (`--training-reviewed`). Flags de instalação e treino seguem
desligadas; ativá-las exige observar GPU/saldo e verificar versões compatíveis
dos pacotes no runtime Pro. O piloto automático é uma **demonstração técnica**.
O carregador exige `use_exact_model_name=True` e confirma a origem observada:
sem essa opção, a Unsloth 2026.10.6 substituiu `Qwen/Qwen2.5-1.5B-Instruct`
por um espelho quantizado e ignorou o SHA fixado. Uma execução anterior a essa
correção é exploratória e não reproduz o modelo no commit da configuração.
As mensagens foram escritas e rotuladas sinteticamente na mesma origem; esta
checagem não estabelece verdade independente nem representatividade, e alguns
parafraseamentos sem grupo podem permanecer. Métricas do holdout sintético não
autorizam uso com clientes, ativação no roteador ou publicação de um modelo.

## Diagnóstico posterior do adaptador salvo

O padrão de urgência e o protocolo de avaliação com amostragem aleatória,
revisão cega independente e selo anterior à inferência estão em
[`INDEPENDENT-EVAL.md`](INDEPENDENT-EVAL.md). O fluxo privado
`independent_eval.py` depende de mensagens reais anonimizadas e de revisores
independentes; não converte os 216 candidatos sintéticos em dados revisados.

`posthoc-stress-v1.jsonl` contém 24 mensagens sintéticas novas, duas por cada
combinação de categoria e urgência. Foi escrito **depois** de observar dois
erros de urgência do teste congelado; portanto é um diagnóstico direcionado,
não uma avaliação cega ou revisão humana. Não foi usado para treino e seus
resultados não substituem o holdout nem sustentam uma estimativa de desempenho
real. Os textos não coincidem com os 216 candidatos originais; uma checagem
textual também recusa similaridade ≥ 0,77, mas não prova independência semântica.

Com o ambiente do Colab já instalado, GPU disponível e `run-002-g4` íntegro,
use um diretório **novo** no mesmo Drive. Esta etapa carrega a base no SHA da
execução, aplica o adaptador com PEFT, faz somente inferência e grava três
arquivos: `predictions.json`, `report.json`, `manifest.json`. Não modifica o
corpus, o teste congelado, o adaptador ou o Supabase.

```sh
python3 experiments/ft05/evaluate_saved_adapter.py \
  /content/drive/MyDrive/FT05/piloto-auto-001/run-002-g4 \
  /content/drive/MyDrive/FT05/piloto-auto-001/posthoc-stress-001 \
  --corpus /content/drive/MyDrive/FT05/piloto-auto-001/synthetic-machine-checked.jsonl \
  --frozen /content/drive/MyDrive/FT05/piloto-auto-001/frozen
```

O avaliador recusa uma execução de treino incompatível, mudanças no corpus e
split, troca de pacotes e sobrescrita da saída. Registra hashes do adaptador,
casos diagnósticos e manifesto anterior. A carga PEFT do adaptador salvo deve
ser validada no Colab real; testes locais cobrem somente dados e relatório.

## Colab Pro: fluxo reproduzível e teste congelado

Abra [`FT05.ipynb`](FT05.ipynb) no Colab com a conta Pro e informe o SHA da PR
empilhada `feat/ft05-colab-pro`. O repositório público pode ser clonado sem
entrar com a mesma conta do GitHub. O notebook não instala dependências, monta
Drive ou inicia GPU por padrão. Inspecione código, confirme GPU e saldo pela UI,
defina uma pasta exclusiva do FT05 no Drive e use apenas corpus sintético
revisado. O teste de 24 exemplos não pode ser promovido por flag. Não monte
Drive nem habilite execução de células de rede em um notebook desconhecido.

Para reproduzir a separação fora do Colab, com 200–500 linhas efetivamente
revisadas e grupos curados:

```sh
python3 ft05.py dataset-reviewed.jsonl /caminho/persistente/frozen --training-reviewed
python3 train.py dataset-reviewed.jsonl --train --frozen /caminho/persistente/frozen \
  --config /caminho/persistente/run-001-config.json \
  --output /caminho/persistente/run-001
```

O primeiro comando grava manifesto, hashes e partições train/validation/test.
O treino recusa corpus, manifesto ou partição alterados e nunca recalcula
silenciosamente o teste. O JSON de configuração contém a revisão imutável
`5fee7c4ed634dc66c6e318c8ac2897b8b9154536` do modelo Qwen; os seis
pacotes, inclusive dependências do Colab, ainda exigem versão compatível
verificada em runtime real. O notebook registra o lock do ambiente após uma
instalação explicitamente habilitada. `reviewed: true` é uma declaração do
revisor responsável: hashes e testes não comprovam revisão humana ou ausência
de paráfrases entre partições.

`model-baseline.json` mede o modelo original e `model-finetuned.json` o LoRA
no mesmo teste; `predictions-model-*.json` guarda as saídas, e
`comparison.json` emparelha IDs com melhorias/regressões e deltas de acerto
exato, F1 por categoria e urgência e JSON válido. `run.json` grava hashes do corpus, split, configuração e template, modelo
e pacotes. Ausência de `run.json` indica execução incompleta. Checkpoints de
época são gravados no diretório escolhido: no Colab, use Drive exclusivo para
persistência, aceitando a lentidão possível. O teste não serve para seleção de
hiperparâmetros; class distributions e decisões de rótulo precisam de revisão
antes do primeiro treino. Colab Pro pode consumir unidades e não garante GPU
ou duração. Não há conexão com outros projetos, Supabase ou API paga nesta etapa.

## Treino e exportação preparados, não executados

`FT05.ipynb` é um notebook Jupyter/Colab sem instalação
automática. A compatibilidade com GPU/T4/Unsloth não foi demonstrada. O script
não importa bibliotecas GPU no modo padrão. Para homologação futura:

1. Revise 200–500 exemplos sintéticos e os grupos; preserve teste congelado.
2. Confirme capacidade, orçamento e disponibilidade de GPU. T4/Colab não é
   garantido nem ilimitado; energia, armazenamento e servidor têm custo.
3. A revisão SHA do Qwen está fixada; escolha versões exatas compatíveis das
   seis bibliotecas em ambiente descartável e retenha lockfile/transitivas. Os
   campos de pacote vazios são bloqueios deliberados, não versões inventadas.
4. Revise dependências e marque gates somente após essa revisão. O script não
   instala pacotes, provisiona credenciais ou faz upload de dados.
5. `python3 train.py dataset-reviewed.jsonl --train --frozen frozen --config training-config.json`
   é a etapa explícita futura. Faz baseline do modelo em teste antes de LoRA,
   treina só em treino, calcula loss em validação e compara o mesmo teste após.
   Não usar teste para escolher hiperparâmetros. Reporta JSON válido, exact match,
   macro-F1 de categoria/urgência sobre classes observadas, matrizes de confusão e erros por ID.
6. `gguf_export_approved` é separado: exportação Unsloth pode baixar/compilar
   llama.cpp. Auditar essa cadeia antes de habilitar. Nenhum GGUF existe aqui.
7. Depois de exportar, revisar `Modelfile.example`, hash e template/EOS. Importação
   futura: `ollama create radar-ft05 -f Modelfile`; `ollama run radar-ft05`.
   Alternativa: `llama-server -m model-q4_k_m.gguf --host 127.0.0.1`.
   Confirmar nomes de flags na versão instalada. Nada foi iniciado.
8. Comparar prompts fixos em Unsloth/Ollama/llama.cpp e recusas de saídas inválidas;
   só então considerar um adapter de classificação no router. Sem ativação automática.

TRL atual documenta `processing_class`; a receita adapta esse parâmetro e
`max_length`/`max_seq_length` pela assinatura instalada. Isso não prova
compatibilidade universal. Falhas GPU/OOM/export precisam ensaio real e log.

## Fontes e autoria

Requisitos: Guia FT05, Eduardo Cavalcanti, 07/10/2026, consultado privadamente;
PDF não redistribuído. Implementação original para Carlos Felipe, com assistência
de IA; destinada a integração sob a licença do repositório após revisão.
Modelo e dependências conservam suas próprias licenças. Referências oficiais:

- https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct (card Apache-2.0, 1.54B)
- https://huggingface.co/docs/trl/sft_trainer
- https://unsloth.ai/docs/basics/inference-and-deployment/saving-to-gguf
- https://docs.ollama.com/import
- https://research.google.com/colaboratory/faq.html

Reversão: remover somente `experiments/ft05/` após integração. Não há banco,
serviço ou recurso remoto criado por este pacote.
