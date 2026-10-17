"""Build the public Colab notebook from auditable, plain-text source cells."""
import json
from pathlib import Path


def md(source):
    return {'cell_type': 'markdown', 'metadata': {}, 'source': source.splitlines(True)}


def code(source):
    return {'cell_type': 'code', 'execution_count': None, 'metadata': {},
            'outputs': [], 'source': source.splitlines(True)}


def notebook():
    cells = [
        md('''# FT05 — treine seu próprio piloto sintético no Colab

Você usa seu **próprio Drive e sua própria sessão de GPU**. Este notebook não
carrega os pesos privados do autor. O corpus público tem 208 mensagens
sintéticas com checagem automática, **sem revisão humana**. O experimento
ensina o fluxo técnico; não valida atendimento real.

Leia [o guia](PUBLIC-COLAB-QUICKSTART.md) antes de começar. Ative uma etapa de
cada vez na Configuração e execute novamente aquela célula. Não use
“Executar tudo”. Por padrão, rede, Drive, instalação, treino e teste estão
desligados. O autor ainda não homologou este notebook em uma segunda conta.
'''),
        md('## Configuração — escolha uma pasta nova no seu Drive'),
        code('''from pathlib import Path
import importlib.metadata, json, shutil, subprocess, sys

FETCH_SOURCE = False
MOUNT_DRIVE = False
PREPARE_CORPUS = False
INSTALL_DEPS = False
RUN_TRAINING = False
RUN_SMOKE = False
GPU_BUDGET_CONFIRMED = False
DEPENDENCIES_REVIEWED = False

REPO_REF = 'feat/ft05-public-colab'  # PR de rascunho; fixar tag revisado antes de divulgar
REPO_DIR = Path('/content/radar-model-router-ft05-public')
ROOT = Path('/content/drive/MyDrive/FT05-meu-piloto-001')  # mude para pasta exclusiva sua
CORPUS = ROOT / 'synthetic-machine-checked.jsonl'
FROZEN = ROOT / 'frozen'
RUN_NAME = 'run-001'  # troque se uma tentativa anterior criou esta pasta
RUN_DIR = ROOT / RUN_NAME
SMOKE_DIR = ROOT / 'smoke-001'  # escolha pasta nova a cada teste

VERSIONS = {'unsloth': '2026.10.6', 'torch': '2.11.0+cu128',
            'transformers': '5.13.1', 'trl': '1.15.0',
            'datasets': '4.8.5', 'peft': '0.19.1'}

# Use somente textos fictícios e novos. O notebook não solicita dados de clientes.
MESSAGES = [
    {'id': 'novo-01', 'text': 'Qual é o prazo geral de entrega antes de comprar?'},
    {'id': 'novo-02', 'text': 'Minha encomenda deve chegar hoje e ainda não saiu para entrega.'},
    {'id': 'novo-03', 'text': 'Quero cancelar o pedido em separação, sem data de envio.'},
    {'id': 'novo-04', 'text': 'A renovação automática acontece hoje e quero cancelar.'},
]
print('Ações externas desligadas por padrão. Pasta escolhida:', ROOT)
'''),
        md('''## 1. Confira o ambiente

Selecione GPU na interface do Colab e confira seu saldo antes do treino.'''),
        code('''print('Python:', sys.version.split()[0])
gpu = shutil.which('nvidia-smi')
if gpu:
    result = subprocess.run([gpu, '--query-gpu=name,memory.total',
                             '--format=csv,noheader'], capture_output=True, text=True)
    print('GPU:', result.stdout.strip() if result.returncode == 0 else result.stderr.strip())
else:
    print('GPU ausente; escolha um runtime com GPU antes de treinar.')
# Importe Unsloth antes de Torch na etapa de treino/inferência.
'''),
        md('''## 2. Obtenha o código e rode testes

Ative `FETCH_SOURCE=True` na Configuração e execute a Configuração de novo.
Um clone existente não será sobrescrito. Registre o commit exibido.'''),
        code('''if FETCH_SOURCE:
    assert not REPO_DIR.exists(), 'Pasta do código já existe; use a revisão presente ou sessão limpa'
    subprocess.run(['git', 'clone', '--depth', '1', '--branch', REPO_REF,
                    'https://github.com/ofelipepeixoto/radar-model-router.git',
                    str(REPO_DIR)], check=True)
    sha = subprocess.check_output(['git', '-C', str(REPO_DIR), 'rev-parse', 'HEAD'],
                                  text=True).strip()
    print('Commit do código:', sha)
    subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v'],
                   cwd=REPO_DIR / 'experiments' / 'ft05', check=True)
else:
    print('Código desligado. Ative FETCH_SOURCE na Configuração.')
'''),
        md('''## 3. Monte o seu Drive

Ative `MOUNT_DRIVE=True` e execute a Configuração novamente. A pasta do
experimento será criada na próxima etapa. Confirme que o destino é seu.'''),
        code('''if MOUNT_DRIVE:
    assert REPO_DIR.is_dir(), 'Execute primeiro a etapa de código'
    from google.colab import drive
    drive.mount('/content/drive')
    assert ROOT.parent.is_dir(), 'Pasta principal do Drive indisponível'
    print('Destino selecionado:', ROOT)
else:
    print('Drive desligado. Ative MOUNT_DRIVE na Configuração.')
'''),
        md('''## 4. Prepare o corpus e congele o split

Ative `PREPARE_CORPUS=True` e execute a Configuração. A operação aceita
somente o corpus público fixado. Uma execução repetida valida bytes e
manifesto em vez de substituir arquivos. `human_reviewed` continua falso.'''),
        code('''if PREPARE_CORPUS:
    assert MOUNT_DRIVE and REPO_DIR.is_dir() and Path('/content/drive/MyDrive').is_dir()
    from sys import path
    ft05_dir = REPO_DIR / 'experiments' / 'ft05'
    if str(ft05_dir) not in path:
        path.insert(0, str(ft05_dir))
    from auto_pilot import write_auto_dataset
    from ft05 import prepare, load_frozen
    ROOT.mkdir(parents=True, exist_ok=True)
    audit = write_auto_dataset(CORPUS)
    if not FROZEN.exists():
        manifest = prepare(CORPUS, FROZEN, automated=True)
    parts, split_sha = load_frozen(CORPUS, FROZEN)
    assert audit['included'] == 208 and all(not row['reviewed'] for group in parts.values() for row in group)
    assert [len(parts[name]) for name in ('train', 'validation', 'test')] == [162, 12, 34]
    print('Corpus sintético:', audit['included'], 'revisão humana: NÃO')
    print('Split:', {name: len(group) for name, group in parts.items()})
    print('Corpus SHA-256:', audit['dataset_sha256'])
    print('Split SHA-256:', split_sha)
else:
    print('Preparação desligada. Ative PREPARE_CORPUS na Configuração.')
'''),
        md('''## 5. Confira e, se necessário, instale dependências

As versões vêm da execução técnica observada no Colab. Ative
`INSTALL_DEPS=True` somente após escolher usar sua sessão e revisar o
comando. A instalação pode modificar pacotes do runtime. Após reiniciar,
repita Configuração, código e montagem; o split persistido será conferido.'''),
        code('''assert REPO_DIR.is_dir() and FROZEN.is_dir(), 'Conclua as etapas 2–4'
current = {}
for package, expected in VERSIONS.items():
    try:
        current[package] = importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        current[package] = 'ausente'
    print(package, 'necessário:', expected, 'presente:', current[package])
if INSTALL_DEPS:
    assert MOUNT_DRIVE and PREPARE_CORPUS and not RUN_TRAINING
    subprocess.run([sys.executable, '-m', 'pip', 'install',
                    *[f'{name}=={version}' for name, version in VERSIONS.items()]], check=True)
    current = {name: importlib.metadata.version(name) for name in VERSIONS}
    assert current == VERSIONS, 'Pacotes divergentes após instalação'
    print('Versões conferidas. Instalação concluída.')
else:
    print('Instalação desligada. Treino requer as seis versões exatas.')
'''),
        md('''## 6. Treine o seu adaptador (opcional; usa GPU e unidades)

Somente após verificar versões e saldo, ative `RUN_TRAINING=True`,
`GPU_BUDGET_CONFIRMED=True` e `DEPENDENCIES_REVIEWED=True` na Configuração.
Reexecute a Configuração e depois esta célula. Ela faz comparação no
holdout sintético uma única vez e salva o seu LoRA no seu Drive. Nunca
reaproveite um `RUN_NAME` que já criou arquivos.'''),
        code('''if RUN_TRAINING:
    assert MOUNT_DRIVE and PREPARE_CORPUS and GPU_BUDGET_CONFIRMED and DEPENDENCIES_REVIEWED
    assert not RUN_DIR.exists(), 'Execução anterior existe; preserve-a e escolha outro RUN_NAME'
    assert not (ROOT / f'{RUN_NAME}-config.json').exists(), 'Configuração anterior existe'
    assert {name: importlib.metadata.version(name) for name in VERSIONS} == VERSIONS
    from ft05 import load_frozen
    load_frozen(CORPUS, FROZEN)
    config = json.loads((REPO_DIR / 'experiments' / 'ft05' / 'training-config.json').read_text())
    config.update(gpu_budget_approved=True, dependency_reviewed=True, package_versions=VERSIONS)
    config_path = ROOT / f'{RUN_NAME}-config.json'
    config_path.write_text(json.dumps(config, indent=2) + '\\n', encoding='utf-8')
    from train import run
    result = run(CORPUS, config_path, RUN_DIR, execute=True, frozen_dir=FROZEN)
    print('Treino sintético concluído:', result['trained'])
    print('Adaptador privado:', RUN_DIR / 'adapter')
    print('Comparação:', RUN_DIR / 'comparison.json')
else:
    print('Treinamento desligado. Nenhuma GPU é usada nesta célula.')
'''),
        md('''## 7. Teste mensagens fictícias novas (opcional)

Ative `RUN_SMOKE=True` após o treino, reexecute a Configuração e rode esta
célula. `SMOKE_DIR` precisa ser uma pasta inexistente. Troque somente textos
fictícios. O teste não calcula acurácia; observe urgências indevidas.'''),
        code('''if RUN_SMOKE:
    assert MOUNT_DRIVE and RUN_DIR.is_dir() and not SMOKE_DIR.exists()
    from personal_smoke import run as smoke_run
    report = smoke_run(MESSAGES, RUN_DIR, SMOKE_DIR, corpus=CORPUS, frozen=FROZEN)
    for row in report['results']:
        print(row['id'], row['parsed'] if row['parsed'] is not None else row['predicted_text'])
    print('JSON válido:', report['valid_json'], '/', report['n'])
    print('Saídas privadas:', SMOKE_DIR / 'manifest.json', SMOKE_DIR / 'report.json')
else:
    print('Teste desligado. Ative RUN_SMOKE após concluir o treino.')
'''),
        md('''## Termine com clareza

No Drive, confira `run.json`, `adapter/`, `comparison.json` e, se testou,
`smoke-001/manifest.json` e `report.json`. Encerre o runtime para liberar a
GPU. Um resultado sintético, mesmo alto, não autoriza atendimento real. A
revisão humana dos candidatos deste exercício permanece pendente.
'''),
    ]
    return {'cells': cells, 'metadata': {'colab': {'name': 'FT05-PUBLIC-COLAB.ipynb'},
            'kernelspec': {'display_name': 'Python 3', 'language': 'python', 'name': 'python3'},
            'language_info': {'name': 'python'}}, 'nbformat': 4, 'nbformat_minor': 5}


if __name__ == '__main__':
    destination = Path(__file__).with_name('FT05-PUBLIC-COLAB.ipynb')
    destination.write_text(json.dumps(notebook(), ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(destination)
