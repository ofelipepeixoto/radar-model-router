# Ficha de revisão — cenários sintéticos

Todos os nove casos de `scenarios.py` são originais, sintéticos e **não revisados**.
São regressões deliberadas, separadas da fixture preparada; não constituem treino,
holdout representativo nem evidência de qualidade de um modelo. Não aumentar a
contagem repetindo templates. A baseline usa palavras-chave e falha em negação,
prioridade entre intenções e pedidos indiretos.

| IDs | Decisão humana necessária | Estado |
|---|---|---|
| negation, quoted | Palavra citada/negada deve influenciar categoria? Definir regra e exemplos limítrofes. | NÃO REVISADO |
| mixed | Confirmar prioridade explícita do usuário quando há duas intenções. | NÃO REVISADO |
| indirect, paraphrase | Confirmar equivalência semântica e urgência; manter no mesmo grupo. | NÃO REVISADO |
| unicode, normalized, bridge | Confirmar mesma ocorrência fictícia e grupo transitivo; NFKC une as duas primeiras. | NÃO REVISADO |
| cancel | Confirmar cancelamento indireto e urgência proposta. | NÃO REVISADO |

Para cada caso registrar: ID, rótulo proposto, rótulo revisado, justificativa,
grupo revisado, identificador interno do revisor e versão da política de rótulos.
Não preencher revisores fictícios nem marcar `reviewed=true` automaticamente.
Sem consenso, excluir o caso do treino ou esclarecer a política antes de rotular.
A heurística de normalização não detecta paráfrases: a curadoria de grupos continua
obrigatória. Fixar o holdout após revisão, antes de ajustar prompts/hiperparâmetros.
Somente depois da seleção de tarefa e de 200–500 exemplos independentes revisados
reavaliar os gates de treino; ambiente GPU e orçamento são decisões separadas.

Verificação sem dependências: na raiz,
`PYTHONPATH=experiments/ft05 python -m unittest discover -s experiments/ft05/tests -v`.
