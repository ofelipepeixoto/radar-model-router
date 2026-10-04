# Composio e Vercel no ecossistema Radar

Decisão do usuário em 03/10/2026 (America/Sao_Paulo): considerar estes plugins quando forem necessários. Isso não contrata plano, publica site nem autoriza mensagens a terceiros.

| Capacidade | Composio | Vercel |
|---|---|---|
| Papel | Descobrir ferramentas e conectar serviços externos | Hospedar interfaces/APIs e acompanhar deployments |
| Exemplos úteis | GitHub → CRM; documentos → revisão; n8n → agenda/serviços conectados | Preview de PR, interface do OaaS, dashboard, formulário de onboarding |
| Controle | Conta/escopo por app, allowlist de ações, aprovação para efeitos externos | Separar preview/produção, secrets por ambiente, build/logs e rollback |
| Limite | Disponibilidade da tool não significa conexão ativa | Projeto/deploy não prova backend ou autorização corretos |
| Roteador atual | Nenhuma conexão operacional externa | Sem deploy necessário para CLI/SQLite local |

## Ordem de escolha

1. Usar conector dedicado existente quando suficiente (GitHub, Supabase etc.).
2. Usar Composio para serviço sem cobertura ou fluxo entre apps que justifique uma conexão adicional. Descobrir tool/schema e confirmar conta ativa antes de agir.
3. Usar n8n/VPS para workflows existentes, workers e estado persistente.
4. Usar Sites para interfaces existentes; considerar Vercel para preview Git, nova interface e runtime compatível. Não duplicar deployments.
5. Avaliar AI SDK/Gateway e MCP somente se resolverem necessidade; cobrança e reservas são independentes de uma assinatura ChatGPT.

## Evidência nesta sessão

Composio: descoberta hospedada de criação GitHub disponível, conexão GitHub ativa para `ofelipepeixoto`, criação deste repositório concluída; não confundir com o conector GitHub dedicado que já acessa a conta. Vercel: consulta autenticada `list_projects` retornou lista vazia, sem paginação adicional. Nenhum projeto/deploy/domínio foi criado.

## Possibilidades por projeto

- Integration Hub: Composio como camada opcional de adapters com executor/approval existentes; Vercel para UI futura, não para hospedar o ledger local.
- Radar OaaS: preview de interface em Vercel se a arquitetura justificar; Composio para dados de CRM consentidos e drafts.
- Agência Camaleão/Help Mídias: conectar CRM/agenda/documentos conforme demanda; onboarding e painéis com preview.
- Radar Disruptivo/Jacarepaguá: drafts editoriais e consolidação de fontes; publicação depende de autorização e conectores efetivos. Nenhum envio automático implícito.
- Jurídico e Leilão: dados sensíveis/revisão permanecem governados; não abrir acesso a documentos ou execução financeira por adicionar plugin.

Fontes: descrições/schema atuais dos tools disponíveis e documentação oficial https://vercel.com/docs/mcp, https://vercel.com/docs/frameworks/frontend/astro, https://vercel.com/docs/deployments e https://vercel.com/docs/spend-management. Não foram avaliados preços, planos ou todas as features dessas plataformas.
