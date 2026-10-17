# FT05 — crie seu próprio adaptador no Colab

Este tutorial usa o corpus sintético **público** do projeto. Cada pessoa treina
um adaptador separado no próprio Google Drive. Não é necessário receber o
adaptador ou o Drive do autor. Seu computador só precisa abrir o navegador;
as tarefas de GPU acontecem no Colab. O classificador deste exemplo tem quatro
categorias e três níveis de urgência, todos fixos. Esta versão não ensina a
trocar domínio, classes ou modelo base.

## Antes de começar

1. Abra [FT05-PUBLIC-COLAB.ipynb](FT05-PUBLIC-COLAB.ipynb) no Colab e salve uma
   cópia na sua conta. Use um runtime com GPU; confira as unidades disponíveis.
2. Leia cada célula antes de ativar a etapa. Na configuração, escolha um nome
   de pasta **novo** para `ROOT` no seu Drive. Não use dados reais ou privados.
3. Execute as etapas na ordem: ambiente → código e testes → Drive → corpus e
   split → dependências → treinamento opcional → mensagens fictícias novas.
4. Para cada ação, mude a flag correspondente para `True`, **execute novamente
   a célula Configuração** e então execute a célula da etapa. Ao terminar,
   volte a flag para `False`; não use “Executar tudo”. O notebook inicia com
   todas as ações externas desligadas.

O corpus é gerado deterministicamente de `candidates-216.jsonl`: oito casos
ambíguos são excluídos e 208 casos recebem checagens automáticas. Eles
continuam com `reviewed: false`. O treino é um **piloto sintético** e seus
resultados não comprovam qualidade em mensagens reais. Não publique o
adaptador ou arquivos do Drive sem revisá-los.

## Resultados esperados

| Etapa | Resultado | Se falhar |
| --- | --- | --- |
| Ambiente | Python e GPU exibidos | Selecione um runtime com GPU antes do treino |
| Código | Commit exibido; `unittest` termina com `OK` | Não continue com testes falhando |
| Corpus | 208 registros; split 162/12/34; `human_reviewed: false` | Preserve a pasta e reporte o erro; não altere os rótulos para forçar o treino |
| Dependências | As seis versões coincidem com as versões fixadas | Pare antes de treinar; runtime e pacotes podem mudar |
| Treino | `run.json`, `adapter/`, comparação e previsões gravados no Drive | Não sobrescreva uma execução parcial; use novo `RUN_NAME` após diagnosticar |
| Teste | `manifest.json` e `report.json` em pasta nova | Verifique integridade e use outro nome de saída |

As versões do exemplo são as verificadas em outubro de 2026: Unsloth
2026.10.6, PyTorch 2.11.0+cu128, Transformers 5.13.1, TRL 1.15.0,
Datasets 4.8.5 e PEFT 0.19.1. A disponibilidade de GPU e compatibilidade
com runtimes futuros variam. A instalação, o download do modelo e o treino
consomem rede, tempo e unidades de computação da sua conta. Reiniciar a
sessão pode exigir executar de novo Configuração, clone e montagem do Drive;
os artefatos já salvos no Drive são preservados e validados antes de uso.

O resultado do holdout sintético é apenas uma medição do exercício. O autor
observou superpriorização em pedidos sem prazo imediato. Para avaliar seu
próprio atendimento, obtenha dados autorizados anonimizados, rótulos humanos
independentes e um protocolo separado; consulte [INDEPENDENT-EVAL.md](INDEPENDENT-EVAL.md).
Não envie mensagens de clientes ou tokens ao GitHub nem à cópia pública do
notebook. Encerre o runtime ao terminar para liberar a GPU.

## Estado de publicação

O notebook está em PR de rascunho. Seu código e suas validações locais foram
preparados; a execução integral em uma segunda conta/Drive ainda precisa de
homologação. Um botão Colab apontando para uma revisão estável será incluído
somente após essa execução e revisão da PR.
