# FT05 — plano para teste pessoal no Colab Pro

**Decisão:** seu computador será a interface no navegador. Toda inferência
do adaptador salvo ocorrerá na GPU do Colab Pro. Não será usada a GPU local,
WSL ou instalação de Unsloth no PC.

O projeto também será compartilhável: outras pessoas poderão criar o
**próprio** piloto com o corpus sintético público e o **próprio** Drive.
O adaptador run-002-g4 e os caminhos privados do operador servem apenas
à sua verificação pessoal; não são dependência do tutorial público.
Nesta primeira versão, cada pessoa reproduz o mesmo classificador de
quatro categorias e três urgências. Mudar domínio, classes ou modelo base
exige adaptar a política, o esquema, os dados e os testes; não anunciar
isso como uma opção pronta no notebook inicial.

## Estado conhecido em 16/10/2026 (São Paulo)

- A PR #7 contém o piloto sintético. A PR #8 acrescenta o protocolo de
  avaliação independente e depende da #7. Ambas seguem sem merge.
- O treino já concluído no Colab salvou run-002-g4 e o adaptador LoRA no
  Drive privado. O teste sintético congelado acertou 32/34.
- O diagnóstico posterior de 24 mensagens sintéticas, executado pelo
  operador, acertou 20/24, com 24/24 JSON válidos e quatro erros de
  urgência média elevada a alta. Os números vieram da saída compartilhada,
  sem leitura direta dos arquivos do Drive por este repositório.
- Trinta testes Python da PR #8 passaram no ambiente de preparação. O
  conector GitHub não retornou checks de CI para o commit consultado.
- Ainda faltam dados reais anonimizados, revisores independentes e avaliação
  real executada.

## Teste pessoal relatado em 17/10/2026 (São Paulo)

O operador executou FT05-PERSONAL-COLAB.ipynb no Colab Pro com Python
3.12.13 e NVIDIA RTX PRO 6000 Blackwell Server Edition. Relatou o commit
004c29a93d74419295404b96f5a5bb3c148c9e1e, hashes de corpus e split
íntegros, a revisão fixa da base e as seis versões de pacotes esperadas.
Os testes de código terminaram sem erro na captura enviada; a saída completa
do unittest não foi disponibilizada.

A inferência carregou os pesos e devolveu 8/8 JSON válidos. As oito
categorias previstas correspondem ao tema das mensagens fictícias do
notebook. Três mensagens sem prazo imediato receberam urgência alta:
meu-01 (etiqueta apagada sem data), meu-03 (cancelamento em separação sem
horário de despacho) e meu-05 (erro de perfil sem prazo imediato).
Os respectivos pares com prazo ou incidente atual também receberam alta:
meu-02, meu-04 e meu-06. As perguntas futuras meu-07 e meu-08 receberam
baixa. Isso é uma inspeção qualitativa posterior; não há gabarito cego nem
taxa de acerto a calcular. Não mudar rótulos ou retreinar com esses casos.

O operador relatou manifest.json e report.json na pasta privada
personal-smoke-001; o conteúdo desses arquivos não foi lido diretamente
por este repositório. A primeira inferência levou cerca de 5,0 s com
carregamento inicial e as seguintes cerca de 0,17–0,22 s, conforme a
saída compartilhada. O aviso de max_new_tokens/max_length não impediu
as oito saídas válidas. O piloto segue sem validação para atendimento real.

## Critérios de aceite

| Marco | Evidência esperada | Situação |
| --- | --- | --- |
| Código | Branch #8 fixada e 30 testes aprovados no Colab | Preparado |
| Artefatos | Corpus, split, run.json e adaptador íntegros no Drive | Verificar novamente |
| Teste pessoal | Mensagens fictícias no Colab Pro, modelo carregado, respostas e latência salvas | 8/8 JSON válidos relatados; leitura direta dos arquivos privados pendente |
| Avaliação independente | Fonte real permitida, duas revisões cegas, adjudicação e relatório | Pendente de dados e pessoas |
| Tutorial público | Notebook guiado executável por outra conta, sem artefatos privados, com saídas e limites claros | A implementar e homologar |

Os primeiros três marcos mostram funcionamento técnico no Colab. O quarto
avalia qualidade no contexto real. Nenhum marco autoriza o atendimento
automático a clientes.

## Dois percursos para quem usar o projeto

| Percurso | O que a pessoa precisa | O que entrega |
| --- | --- | --- |
| Experimentar | Conta Google, notebook público e Python; GPU somente para inferência/treino | Testes, corpus sintético, adaptador próprio se optar por treinar, mensagens de teste |
| Avaliar meu caso | Além disso, fonte real anonimizada autorizada e revisores distintos | Relatório privado de qualidade do próprio contexto |

O tutorial terá um botão Abrir no Colab, introdução curta e células numeradas:
0. Verificar ambiente; 1. Preparar fixture pública e rodar testes sem GPU;
2. Escolher uma pasta exclusiva no Drive; 3. Validar GPU e dependências;
4. Treinar adaptador próprio **por escolha explícita**; 5. Testar mensagens
novas; 6. Avaliação independente opcional. Por padrão, nenhuma célula monta
Drive, instala pacotes ou treina sem ação consciente. Cada etapa mostra
resultado esperado, erro legível e como retomar numa pasta nova.

Não exigir que iniciantes preencham SHA, caminhos internos e versões de
pacotes à mão; o notebook deve registrar automaticamente o commit efetivo
e validar as versões antes de uma etapa GPU. Para uma edição estável,
publicar um tag/release revisado e apontar o botão Colab para essa revisão,
não para uma branch móvel. O fluxo pode ser usado em Colab compatível
sem prometer GPU específica, unidades gratuitas ou desempenho igual ao
da conta Pro.

## Fase 1 — sessão Colab limpa

**Responsáveis:** Codex prepara código e pré-voo; operador abre a conta Pro
no navegador e observa GPU/saldo.

1. Abrir a cópia autorizada do notebook FT05, selecionar GPU e conferir
   unidades disponíveis. A sessão futura pode receber GPU diferente da
   RTX PRO 6000 já observada.
2. Confirmar Python 3.12, nvidia-smi, VRAM disponível e versões instaladas.
   A célula de inferência verifica CUDA após importar Unsloth antes de Torch.
   Não exibir tokens.
3. Montar apenas o Drive necessário após inspecionar as células; manter
   run-002-g4 e o teste congelado intocados.
4. Obter a branch feat/ft05-independent-eval, registrar o SHA e executar
   os 30 testes usando a biblioteca padrão. Em runtime novo, comparar
   dependências ao run.json e ao lock antes de instalar versões compatíveis.
5. Manter FREEZE_REVIEWED=False, INSTALL_DEPS=False e RUN_TRAINING=False
   por padrão. A instalação em ambiente recriado é uma ação explícita,
   apenas depois de pré-voo e resolução; não repetir treino.

**Parada:** ausência de CUDA, hashes diferentes, versões incompatíveis
ou saldo insuficiente. Registrar a falha. Não substituir silenciosamente
o modelo, o SHA, o adaptador ou o corpus.

Na cópia do notebook, o pré-voo sem instalação pode começar por:

    import sys, shutil, subprocess
    print("Python:", sys.version.split()[0])
    print("nvidia-smi:", shutil.which("nvidia-smi"))
    if shutil.which("nvidia-smi"):
        subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total",
                        "--format=csv,noheader"], check=True)

Depois de confirmar a GPU e revisar a origem da branch, obter o código
numa pasta nova da VM e testar, em células de comandos do Colab:

    !git clone --branch feat/ft05-independent-eval --single-branch https://github.com/ofelipepeixoto/radar-model-router.git /content/radar-model-router-ft05
    %cd /content/radar-model-router-ft05/experiments/ft05
    !git rev-parse HEAD
    !python3 -m unittest discover -s tests -v

Se a pasta já existe em uma sessão reaproveitada, não executar o clone de
novo por cima; registrar a revisão existente e decidir se inicia sessão
limpa. Esperado: 30 testes e OK. O código clonado na VM é efêmero; o
adaptador e saídas ficam no Drive autorizado.

## Fase 2 — integridade dos artefatos no Drive

Verificar numa célula sem carregar pesos:

- piloto-auto-001/run-002-g4/run.json;
- piloto-auto-001/run-002-g4/adapter/adapter_config.json e
  adapter_model.safetensors;
- piloto-auto-001/synthetic-machine-checked.jsonl;
- piloto-auto-001/frozen/manifest.json, train.jsonl, validation.jsonl,
  test.jsonl;
- piloto-auto-001/requirements-lock-g4.txt.

Comparar hashes de corpus/split ao run.json, nome e revisão exatos da base,
template e pacotes. **Aceite:** arquivos legíveis e hashes consistentes,
com originais preservados. A verificação deve recusar pesos incompletos
antes de gastar tempo carregando a base.

## Fase 3 — teste pessoal do adaptador

O notebook [FT05-PERSONAL-COLAB.ipynb](FT05-PERSONAL-COLAB.ipynb) chama
personal_smoke.py. Ele carrega a base Qwen2.5-1.5B-Instruct na revisão fixada, aplica
o LoRA salvo e recebe uma lista de mensagens digitadas pelo operador.
Salva em pasta nova e privada personal-smoke-001: mensagens, previsões,
latência, SHA do adaptador e versão do código. Não recebe rótulos esperados
e nunca treina.

Começar com 8–12 mensagens **novas e fictícias**, incluindo pares que
mudam apenas o prazo: etiqueta borrada sem data versus entrega hoje;
cancelamento sem despacho marcado versus renovação hoje; erro de perfil
comum versus incidente ativo de acesso. Incluir baixa urgência e um caso
ambíguo. Isso é inspeção pessoal, não estimativa independente de acerto.

**Aceite técnico:** base exata e adaptador carregados, uma previsão por
ID, JSON analisável apenas com categoria e urgencia, sem exceção, arquivos
persistidos e legíveis. **Aceite de conteúdo:** registrar todas as
divergências e saídas inválidas. Não retreinar ou ajustar rótulos do
teste congelado por causa delas.

Para usar bem as unidades do Colab, carregar o modelo uma vez, executar
as mensagens na mesma sessão e evitar reinstalações e novo treino. Não é
necessário saturar os 98 GB de VRAM observados para testar um modelo 1.5B.

## Fase 4 — avaliação real independente

**Pré-requisitos ausentes:** população autorizada de atendimentos
anonimizados, dois revisores habilitados e terceiro para conflitos.
Os projetos Supabase conectados não forneceram essa população.

1. Responsável pelos dados define período e canal e fornece CSV privado
   id,text com pelo menos 60 casos elegíveis. O script não anonimiza.
2. No Colab, somente se o processamento desses dados no Google for
   autorizado, independent_eval.py prepare sorteia 60 casos e cria duas
   fichas cegas. Nenhuma mensagem ou ficha vai para o GitHub.
3. Duas pessoas distintas revisam sem previsões ou acesso à ficha da
   outra. Uma terceira decide conflitos. Seal grava o ouro e hashes.
4. Predict carrega o mesmo adaptador, executa inferência e score mede
   cobertura, JSON válido, acerto, matrizes, falsos alertas de alta e
   urgências altas perdidas. Comandos completos em INDEPENDENT-EVAL.md.
5. Interpretar prevalência, desacordos e exclusões; uma amostra de 60
   é exploratória e pode não ter classes raras suficientes.

Se mensagens reais não puderem ir ao Colab, não enviá-las. Buscar fonte
permitida ou ambiente aprovado. Não simular revisão humana com IA. Os
216 candidatos continuam reviewed: false; não são requisito para este
ensaio de avaliação.

## Fechamento e recuperação

- Relatório final: SHA do código, GPU observada, Python/pacotes, hashes,
  tempos, contagens, erros e localização privada dos manifestos.
- Cada tentativa usa pasta nova no Drive. Em desconexão, conferir arquivos
  e hashes antes de repetir. Preservar run-002-g4 e o holdout.
- Encerrar runtime após confirmar persistência para não consumir unidades
  desnecessárias. O plano Pro não garante a mesma GPU ou duração.
- PRs permanecem em rascunho. Treino, GGUF, integração com router,
  deploy e atendimento real ficam fora deste teste.

**Próxima ação:** conferir a leitura dos dois arquivos privados do teste
pessoal e encerrar a sessão de GPU. Depois, entregar em PR separada o
notebook público guiado, testes de integridade e quickstart. Homologar o tutorial em conta/Drive separados,
com corpus público e adaptador gerado pelo próprio tutorial, antes de
criar um tag e compartilhar. A fase 4 espera fonte permitida e revisores
independentes.
