# Strategic Blueprint

> Focus on the **what** and **why**. The code will follow.

**Hard rule**: AI agents must not edit this file and must not draft paste-ready content for it.

## The Problem
Preciso criar um sistema de sessão para o meu chat. Nesse contexto quando o usuário enviar uma mensagem para o chat o sistema de realizar duas ações básicas. A primeira consiste em quando ele enviar a primeira interação do chat ele deve iniciar uma seção, essa seção deve ser guardada no banco de dados contento informações como titulo data de registro e ultima atualização. Além disso, deve ser criado uma tabela no banco de dados onde os textos enviados tanto pela IA quanto pelo usuário ficam marcados. Essa tabela deve registra a qual sessão ela pertence, guardar os textos em um campo de texto e dizer se aquele texto foi enviado pela IA ou pelo usuáio. 

A segunda ação consiste em refatorar o front para que ele possa lidar com essas sessões. Você deve adicionar um aside lateral esquerdo contento todas as seções que foram criadas. O usuário pode clicar sobre a seção e alterar em qual seção ele está trabalhando. Assim, podemos ver que cada mensagem enviada tem que está vinculada a uma seção. O usuário pode ter um botão para iniciar uma nova seção no front, mas a seção só irá ser criada de fato quando o usuãrio enviar uma mensagem a api.

## Steps
- [ ] Cria duas tabelas no banco de dados, sessions e messages. A tabela de sessions guarda a seção enquanto messages contem as mensagem da seção sempre idetificando quem enviou, o usuário ou o chat.
- [ ] Crie um endpoint para listar as seções
- [ ] Crie um endpoint para listar as mensagens das seções
- [ ] Crie um endpoint para receber mensagens (lembre-se que deve ser criada uma nova sessão quando o usuário enviar a primeira mensagem, podemos receber um campo chamado session nulo se for o caso)
- [ ] Cria a listagem de sessão no front
- [ ] Crie um botão de nova sessão no front (que deve mostrar apenas um novo chat)

## Success Looks Like
- [ ] O sistema deve criar seções quando o usuário enviar uma mensagem
- [ ] O usuário deve ser capaz de criar outras seções
- [ ] O usuário deve acessar outras seções
- [ ] O usuário deve ser capaz de enviar mensagens para sessões antigas e novas

## Notes

---
**⚠️ HUMAN ONLY**: This file is your strategic space. AI agents must not edit it.
