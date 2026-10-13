"""Generate explicitly unreviewed synthetic examples; not a training dataset."""
import json
from pathlib import Path
samples = {
 'entrega': ['A entrega ficticia atrasou', 'O pacote de demonstracao nao chegou', 'Quero acompanhar o envio simulado', 'O rastreio de exemplo parou', 'Quando chega minha compra ficticia?', 'A caixa de teste veio vazia'],
 'pagamento': ['Posso pagar em parcelas?', 'Aceita pagamento por cartao?', 'Como funciona o parcelamento?', 'Existe boleto de demonstracao?', 'Preciso da segunda via ficticia', 'O valor de teste foi duplicado'],
 'cancelamento': ['Quero cancelar o plano ficticio', 'Cancele minha compra de exemplo', 'Como cancelar uma assinatura simulada?', 'Desejo encerrar o contrato de teste', 'Nao quero renovar o plano de demonstracao', 'Pode interromper minha assinatura ficticia?'],
 'outro': ['Qual o horario da loja de exemplo?', 'Obrigado pela ajuda na demonstracao', 'Onde vejo o catalogo ficticio?', 'Voces atendem aos sabados?', 'Quero conhecer as cores de teste', 'Oi, tudo bem?']}
rows=[]
for category, prompts in samples.items():
 for i,prompt in enumerate(prompts):
  rows.append({'id':f'{category}-{i}', 'group_id':f'{category}-{i}', 'synthetic':True,'reviewed':False,'messages':[{'role':'user','content':prompt},{'role':'assistant','content':json.dumps({'categoria':category,'urgencia':{'entrega':'alta','pagamento':'media','cancelamento':'alta','outro':'baixa'}[category]},ensure_ascii=False)}]})
Path(__file__).with_name('synthetic.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows),encoding='utf-8')
