from __future__ import annotations

from datetime import datetime, timezone

from backend.models import ChatMessage, ChatSession


class TestChatSession:
    def test_create_session(self, db_session):
        """Deve criar uma sessao com valores padrao."""
        session = ChatSession(title=None)
        db_session.add(session)
        db_session.commit()
        db_session.refresh(session)

        assert session.id is not None
        assert session.title is None
        assert isinstance(session.created_at, datetime)
        assert isinstance(session.updated_at, datetime)

    def test_session_with_title(self, db_session):
        """Deve criar uma sessao com titulo."""
        session = ChatSession(title="Minha sessao")
        db_session.add(session)
        db_session.commit()
        db_session.refresh(session)

        assert session.title == "Minha sessao"

    def test_session_cascade_delete_messages(self, db_session):
        """Deletar sessao deve remover mensagens associadas."""
        session = ChatSession(title=None)
        db_session.add(session)
        db_session.commit()
        db_session.refresh(session)

        msg = ChatMessage(session_id=session.id, role="user", content="teste")
        db_session.add(msg)
        db_session.commit()

        assert db_session.query(ChatMessage).count() == 1

        db_session.delete(session)
        db_session.commit()

        assert db_session.query(ChatMessage).count() == 0


class TestChatMessage:
    def test_create_message_defaults(self, db_session):
        """Deve criar uma mensagem com valores padrao para session_id, model e created_at."""
        session = ChatSession(title=None)
        db_session.add(session)
        db_session.commit()
        db_session.refresh(session)

        msg = ChatMessage(
            session_id=session.id,
            role="user",
            content="Ola, mundo!",
        )
        db_session.add(msg)
        db_session.commit()
        db_session.refresh(msg)

        assert msg.id is not None
        assert msg.session_id == session.id
        assert msg.role == "user"
        assert msg.content == "Ola, mundo!"
        assert msg.model == "google/gemma-4-31b-it"
        assert isinstance(msg.created_at, datetime)

    def test_create_message_custom_model(self, db_session):
        """Deve criar uma mensagem com modelo customizado."""
        session = ChatSession(title=None)
        db_session.add(session)
        db_session.commit()

        msg = ChatMessage(
            session_id=session.id,
            role="user",
            content="Teste",
            model="openai/gpt-4o",
        )
        db_session.add(msg)
        db_session.commit()
        db_session.refresh(msg)

        assert msg.model == "openai/gpt-4o"

    def test_query_by_session_id(self, db_session):
        """Deve filtrar mensagens por session_id."""
        session1 = ChatSession(title=None)
        session2 = ChatSession(title=None)
        db_session.add_all([session1, session2])
        db_session.commit()

        msg1 = ChatMessage(session_id=session1.id, role="user", content="a")
        msg2 = ChatMessage(session_id=session2.id, role="user", content="b")
        db_session.add_all([msg1, msg2])
        db_session.commit()

        results = (
            db_session.query(ChatMessage)
            .filter(ChatMessage.session_id == session1.id)
            .all()
        )
        assert len(results) == 1
        assert results[0].content == "a"

    def test_query_by_role(self, db_session):
        """Deve filtrar mensagens pelo campo role."""
        session = ChatSession(title=None)
        db_session.add(session)
        db_session.commit()

        msg1 = ChatMessage(session_id=session.id, role="user", content="pergunta")
        msg2 = ChatMessage(session_id=session.id, role="assistant", content="resposta")
        db_session.add_all([msg1, msg2])
        db_session.commit()

        users = (
            db_session.query(ChatMessage)
            .filter(ChatMessage.role == "user")
            .all()
        )
        assistants = (
            db_session.query(ChatMessage)
            .filter(ChatMessage.role == "assistant")
            .all()
        )

        assert len(users) == 1
        assert len(assistants) == 1
        assert users[0].content == "pergunta"
        assert assistants[0].content == "resposta"

    def test_created_at_auto_set(self, db_session):
        """O campo created_at deve ser preenchido automaticamente com UTC now."""
        session = ChatSession(title=None)
        db_session.add(session)
        db_session.commit()

        before = datetime.now(timezone.utc).replace(tzinfo=None)
        msg = ChatMessage(session_id=session.id, role="user", content="timestamp test")
        db_session.add(msg)
        db_session.commit()
        db_session.refresh(msg)
        after = datetime.now(timezone.utc).replace(tzinfo=None)

        assert before <= msg.created_at <= after

    def test_message_belongs_to_session(self, db_session):
        """A mensagem deve pertencer a sessao correta via relationship."""
        session = ChatSession(title="test session")
        db_session.add(session)
        db_session.commit()

        msg = ChatMessage(session_id=session.id, role="user", content="msg")
        db_session.add(msg)
        db_session.commit()
        db_session.refresh(session)

        assert len(session.messages) == 1
        assert session.messages[0].content == "msg"

    def test_content_persists_long_text(self, db_session):
        """Deve persistir conteudos longos corretamente."""
        long_text = "Lorem ipsum " * 200
        session = ChatSession(title=None)
        db_session.add(session)
        db_session.commit()
        msg = ChatMessage(session_id=session.id, role="user", content=long_text)
        db_session.add(msg)
        db_session.commit()
        db_session.refresh(msg)

        assert msg.content == long_text
