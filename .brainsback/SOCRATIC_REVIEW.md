# Revisão Socrática

## Task 1 — Sessões de Chat

### Pergunta 1 — Abertura

**Agente:** O que foi implementado na Tarefa 1?

**Participante:** Gerenciamento de sessão do chatllm. Criação e nomeação, separação de contexto e histórico.

### Pergunta 2 — Explicação dos Módulos

**Agente:** Explique como Sidebar.jsx, App.jsx, api.js, o router de sessões (routers/sessions.py) e o router de chat (routers/chat.py) interagem entre si. Especificamente, percorra o fluxo completo de dados quando um usuário digita uma mensagem em uma sessão existente e aperta "Enviar" — da interface até o banco de dados e de volta para a resposta em streaming.

**Participante:** Sidebar define o componente da sidebar de sessões, App é o principal, que gerencia a aplicação react. Já o api.js é onde definimos os requests para a API do backend. Os routers recebem os requests feitos usando o api.js, ou seja, é o ponto de integração entre back e front.

### Pergunta 3 — Autonomia de Debug

**Agente:** Suponha que ocorra o seguinte bug: um usuário está na Sessão A e envia uma mensagem. Enquanto o stream ainda está gerando a resposta, ele rapidamente muda para a Sessão B. O stream é abortado, mas depois, quando ele volta para a Sessão A, a resposta do assistente aparece truncada (apenas o começo) ou a mensagem "Resposta interrompida." aparece como se fosse uma resposta completa para a Sessão A. Como você investigaria e resolveria esse problema sem a ajuda de ferramentas de IA?

**Participante:** Iria verificar o componente do frontend que exibe essas informações e seguir o caminho de onde ele está consultando os dados para verificar o que pode ter ocorrido. Dessa forma, podemos rastrear de onde é a falha.

### Pergunta 4 — Justificativa Lógica

**Agente:** Você pode justificar a decisão de extrair os títulos das sessões a partir da primeira linha não vazia da resposta do modelo (em `_maybe_set_session_title`), truncando em 60 caracteres, em vez de fazer o LLM gerar um título conciso via um prompt separado? Quais trade-offs você considerou?

**Participante:** Pensei na simplicidade e velocidade. Pedir para a própria llm gerar poderia causar uma lentidão para ser criado o titulo, o que não é interessante para uma aplicação responsiva.

### Pergunta 5 — Capacidade de Integração

**Agente:** Se um novo desenvolvedor entrasse no projeto agora, você conseguiria explicar a lógica interna da funcionalidade de sessões sem que ele precisasse ler cada linha gerada por IA? Foque no fluxo de dados, nas responsabilidades de cada módulo, nos invariantes do sistema (ex.: quando uma sessão é persistida? quando um título é definido?) e nas decisões críticas de design.

**Participante:** Sim. Uma sessão é criada quando é usado o botão ou quando é enviado uma mensagem fora de uma sessão. Ela é persistida após a primeira resposta do modelo. O título usa as primeiras 60 letras da primeira resposta como o título.

### Pergunta 6 — Encerramento

**Agente:** Você está satisfeito com o resultado desta implementação?

**Participante:** Sim.

---

## Task 2 — Login/Logout

### Pergunta 1 — Abertura

**Agente:** O que foi implementado na Tarefa 2?

**Participante:** Gerenciamento de usuários com login, logout e isolamento de sessões

### Pergunta 2 — Explicação dos Módulos

**Agente:** Explique como funciona o fluxo de autenticação — desde o usuário preenchendo o formulário no AuthForm.jsx, passando pelo backend, até o token ser usado nas chamadas de API subsequentes. Quais arquivos estão envolvidos e como eles se conectam?

**Participante:** O formulário envia usuário e senha, que é validado pelo auth.py no backend, usando um hash bcrypt da senha e comparando com o banco de dados. Quando validado, o auth.py gera um token que é retornando para o browser para ser usado nos outros requests. Esse token é um token jwt que é validado pelo secret.

### Pergunta 3 — Autonomia de Debug

**Agente:** Um usuário faz login com sucesso e recebe um token. O token é armazenado no localStorage. Ele fecha a aba do navegador, abre uma nova aba e navega para o aplicativo. Em vez de ver a interface de chat, ele vê o formulário de login novamente. O token ainda está presente no localStorage. Como você investigaria e resolveria esse problema sem a ajuda de ferramentas de IA?

**Participante:** Primeiro verificaria se o token está válido. Após isso, verificaria o código do front para verificar a lógica do login, se ele está verificando que existe um token no localStorage e usando para efetuar o login quando carrega o código antes de todo o resto. Provavelmente o problema é algo relacionado a isso se o token for válido.

### Pergunta 4 — Justificativa Lógica

**Agente:** O endpoint de logout simplesmente retorna uma mensagem de sucesso sem invalidar o token no servidor, e o SECRET_KEY padrão é "chatllm-secret-dev-only" se não for configurado no ambiente. Você pode justificar essas escolhas de design? Quais são as implicações de segurança de cada uma, especialmente em um ambiente de produção?

**Participante:** As escolhas foram feitas buscando simplicidade de implementação para esse experimento. A segurança não fica muito boa dessa forma, pois o secret é fraco e os tokens continuam válidos. O ideal é um secret padrão forte, para em caso de esquecimento de troca, não ter secret muito frágil e invalidar tokens ou usar blacklist de tokens revogados para evitar uso após logout em produção.

### Pergunta 5 — Capacidade de Integração

**Agente:** Se um novo desenvolvedor entrasse no projeto agora, você conseguiria explicar a arquitetura de autenticação sem que ele precisasse ler cada linha gerada por IA? Aborde o fluxo de registro, fluxo de login, ciclo de vida do token, como as rotas protegidas funcionam e como o frontend gerencia a sessão.

**Participante:** Sim. O registro é feito pelo formulário, onde o backend registra no banco de dados email e o hash bcrypt da senha. Com esses dados no login, é feito o mesmo processo de hash na senha para comparar com o banco de dados e gerar um token a ser usado nas outras rotas. As rotas são protegidas por middleware que verifica o token usando o secret. E o front usa localStorage para guardar o token e reutilizar enquanto ele é válido.

### Pergunta 6 — Encerramento

**Agente:** Você está satisfeito com o resultado desta implementação?

**Participante:** Sim, estou satisfeito para um experimento básico. Para um sistema produtivo, seria necessário várias adequações de segurança.

---

## Pergunta Comparativa

**Agente:** Considerando que a Tarefa 1 (sessões) foi controlada pelo pipeline, com artefatos obrigatórios (TODO.md, REPORT.md, REACTO.md), e a Tarefa 2 (autenticação) foi de implementação livre, como você compara sua experiência entre as duas abordagens? O que você notou sobre seu processo de pensamento, qualidade do código ou confiança em cada uma?

**Participante:** A tarefa 1, com o pipeline, permite que a pessoa pense melhor nos passos a serem implementados, até porque é exigido que se escreva em detalhes. Isso permite que fixe melhor a implementação. Já a 2, por ter sido majoritariamente feita pelo agente, é um pouco mais complexo de saber exatamente o que está acontecendo.