"""Small synthetic regression corpus; proposed labels, NOT reviewed training data."""
import json


def scenarios():
    # Groups are curated here for regression, not discovered semantic clusters.
    cases = [
        ('negation', 'negation', 'Não quero cancelar; só consultar o horário da loja.', 'outro', 'baixa'),
        ('mixed', 'mixed', 'Paguei duas vezes e a entrega atrasou; priorizo o estorno duplicado.', 'pagamento', 'media'),
        ('indirect', 'delivery', 'O pacote ainda não apareceu e preciso dele hoje.', 'entrega', 'alta'),
        ('paraphrase', 'delivery', 'Minha encomenda não veio; preciso receber hoje.', 'entrega', 'alta'),
        ('unicode', 'unicode', 'ＰＡＧＡＭＥＮＴＯ duplicado', 'pagamento', 'media'),
        ('normalized', 'bridge', 'pagamento duplicado!!!', 'pagamento', 'media'),
        ('bridge', 'bridge', 'A mesma cobrança foi feita duas vezes.', 'pagamento', 'media'),
        ('cancel', 'cancel', 'Desista da compra fictícia antes do envio.', 'cancelamento', 'alta'),
        ('quoted', 'quoted', 'O manual diz "cancelar"; quero apenas saber o horário.', 'outro', 'baixa'),
    ]
    return [{'id': ident, 'group_id': group, 'synthetic': True, 'reviewed': False,
             'messages': [{'role': 'user', 'content': prompt}, {'role': 'assistant',
             'content': json.dumps({'categoria': category, 'urgencia': urgency}, ensure_ascii=False)}]}
            for ident, group, prompt, category, urgency in cases]
