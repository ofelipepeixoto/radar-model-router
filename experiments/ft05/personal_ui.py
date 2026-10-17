"""Private in-notebook UI for repeated inference on a saved FT05 adapter.

No web server, sharing link, message persistence, or training. The caller
mounts their own Drive and verifies consent for the Colab GPU session.
"""
import hashlib
import time


def launch(run_dir, corpus, frozen):
    """Load the pinned adapter once, then return a browser widget in Colab."""
    from personal_smoke import REVISION, preflight
    from ft05 import target
    from train import load_pinned_model

    checked = preflight(run_dir, corpus, frozen, versions=True)
    # Unsloth must be imported before Torch/Transformers in this runtime.
    from unsloth import FastLanguageModel
    import torch
    from peft import PeftModel
    import ipywidgets as widgets
    from IPython.display import display

    if not torch.cuda.is_available():
        raise ValueError('cuda_required')
    base, tokenizer, _ = load_pinned_model(FastLanguageModel, REVISION)
    if hashlib.sha256(tokenizer.chat_template.encode()).hexdigest() != checked['meta']['chat_template_sha256']:
        raise ValueError('chat_template_changed')
    model = PeftModel.from_pretrained(base, str(checked['adapter']), is_trainable=False)
    FastLanguageModel.for_inference(model)
    model.eval()

    box = widgets.Textarea(value='', placeholder='Digite uma mensagem fictícia...',
                           description='Mensagem:', layout=widgets.Layout(width='95%', height='110px'))
    button = widgets.Button(description='Classificar', button_style='primary')
    output = widgets.Output()

    def classify(_):
        button.disabled = True
        try:
            with output:
                output.clear_output()
                message = box.value.strip()
                if not 3 <= len(message) <= 2000:
                    print('Digite entre 3 e 2.000 caracteres.')
                    return
                prompt = tokenizer.apply_chat_template(
                    [{'role': 'user', 'content': message}], tokenize=False,
                    add_generation_prompt=True)
                inputs = tokenizer(prompt, return_tensors='pt', add_special_tokens=False).to(model.device)
                started = time.perf_counter()
                with torch.inference_mode():
                    generated = model.generate(**inputs, max_new_tokens=96, do_sample=False)
                torch.cuda.synchronize()
                raw = tokenizer.decode(
                    generated[0][inputs['input_ids'].shape[-1]:], skip_special_tokens=True)
                try:
                    labels = target(raw)
                    print('Categoria:', labels['categoria'])
                    print('Urgência:', labels['urgencia'])
                except (ValueError, TypeError):
                    print('Resposta fora do formato esperado:', raw)
                print('Tempo:', round((time.perf_counter() - started) * 1000), 'ms')
                print('Teste pessoal sintético; não é decisão automática para clientes.')
        except Exception as exc:
            with output:
                output.clear_output()
                print('Falha na inferência:', type(exc).__name__, str(exc))
        finally:
            button.disabled = False

    button.on_click(classify)
    panel = widgets.VBox([box, button, output])
    display(panel)
    print('Interface pronta. O modelo fica carregado até encerrar o runtime.')
    return panel
