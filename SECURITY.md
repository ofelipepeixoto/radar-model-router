# Segurança e limites operacionais

A versão 0.1.0 é laboratório local em modo sombra. Não usar em produção, expor um endpoint público ou substituir autorizações do Integration Hub. Nenhuma API paga é chamada.

O caller embutido é responsável por autenticação, tenant, capacidades reais, revisão e mínimos de risco. Nunca construir `Scope` ou limites de orçamento a partir do payload remoto. A CLI assume acesso local autorizado; não oferece autenticação.

`hermes_request` apenas transforma uma cópia de request quando opt-in explícito e provider/API mode/modelo são conhecidos. O wrapper deve receber decisão recém-obtida para a mesma identidade, e não uma decisão enviada pelo usuário. Nenhuma tool é autorizada pelo tier. Não registrar requests completos ou mensagens no wrapper.

O ledger conserva reservas desconhecidas e aceita reconciliação tardia. Overrun é gravado e sinalizado; gastos futuros veem o valor real. Não zerar uma reserva após timeout sem comprovação do provedor. Ledger e limite são mecanismos locais, não autorização financeira nem integração paga homologada. Cada operação futura deve definir teto de tokens, tarifa/currency verificada, limite e reserva antes da chamada.

Inicializar o estado uma vez antes de workers concorrentes. Há permissões POSIX 0700/0600 e recusa de symlink direto no diretório/key/db. O diretório pai e o caminho precisam ser locais e confiáveis: não é proteção contra adversário com acesso ao mesmo usuário ou TOCTOU. SQLite é para host com volume persistente, não filesystem efêmero de functions. Backups devem incluir a chave de identidade. Não rotacionar/excluir chave com reservas pendentes.

Decisões expiram após sete dias e são limpas no próximo acesso; identidade pode ser reutilizada depois da janela. Reservas não expiram automaticamente e podem crescer: manutenção financeira é futura. IDs HMAC continuam sendo dados pseudonimizados, não anonimização garantida. Não inserir nomes pessoais nos IDs.

Comunicar problemas por issue sem prompts, chaves, documentos ou logs sensíveis. Antes de anexar evidência, usar dados sintéticos. Sem garantia de segurança formal, multi-host ou compliance.
