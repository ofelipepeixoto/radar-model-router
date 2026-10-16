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
continua com treino desativado até a promoção e o congelamento do teste.

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
