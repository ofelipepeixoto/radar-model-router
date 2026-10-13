# FT05 — experimento incremental para radar-model-router

Preparação original, offline, sem alterar política de roteamento, ledger ou providers.
Adição isolada em `experiments/ft05/`, baseada na main
`f9533a43af86729696c5cd9980adec223beb3410`. A PR #1 foi comparada: seus
arquivos de capabilities/provider são independentes deste experimento e não
foram copiados ou alterados. Mantém trabalhos posteriores da main.

Validação local: 91 testes existentes do router e 8 testes deste experimento
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

## Treino e exportação preparados, não executados

`FT05.ipynb` é um notebook Jupyter/Colab sintaticamente validado, sem instalação
automática. A compatibilidade com GPU/T4/Unsloth não foi demonstrada. O script
não importa bibliotecas GPU no modo padrão. Para homologação futura:

1. Revise 200–500 exemplos sintéticos e os grupos; preserve teste congelado.
2. Confirme capacidade, orçamento e disponibilidade de GPU. T4/Colab não é
   garantido nem ilimitado; energia, armazenamento e servidor têm custo.
3. Fixe revisão SHA do Qwen e versões exatas das seis bibliotecas no JSON,
   em ambiente descartável; resolva e retenha lockfile/transitivas. Os campos
   vazios são bloqueios deliberados, não versões inventadas.
4. Revise dependências e marque gates somente após essa revisão. O script não
   instala pacotes, provisiona credenciais ou faz upload de dados.
5. `python3 train.py dataset-reviewed.jsonl --train --config training-config.json`
   é a etapa explícita futura. Faz baseline do modelo em teste antes de LoRA,
   treina só em treino, calcula loss em validação e compara o mesmo teste após.
   Não usar teste para escolher hiperparâmetros. Reporta JSON válido, exact match,
   macro-F1 sobre classes observadas e matriz de confusão.
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
