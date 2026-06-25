from __future__ import annotations

from datetime import datetime, timezone

from datetime import datetime, timezone

from backend.models import ChatMessage, Message, Session, User


class TestChatMessage:
    def test_create_message_defaults(self, db_session):
        """Deve criar uma mensagem com valores padrao para session_key, model e created_at."""
        msg = ChatMessage(
            role="user",
            content="Ola, mundo!",
        )
        db_session.add(msg)
        db_session.commit()
        db_session.refresh(msg)

        assert msg.id is not None
        assert msg.session_key == "default"
        assert msg.role == "user"
        assert msg.content == "Ola, mundo!"
        assert msg.model == "google/gemma-4-31b-it"
        assert isinstance(msg.created_at, datetime)

    def test_create_message_custom_session(self, db_session):
        """Deve criar uma mensagem com session_key customizada."""
        msg = ChatMessage(
            session_key="session-abc",
            role="assistant",
            content="Resposta do assistente.",
        )
        db_session.add(msg)
        db_session.commit()
        db_session.refresh(msg)

        assert msg.session_key == "session-abc"
        assert msg.role == "assistant"

    def test_create_message_custom_model(self, db_session):
        """Deve criar uma mensagem com modelo customizado."""
        msg = ChatMessage(
            role="user",
            content="Teste",
            model="openai/gpt-4o",
        )
        db_session.add(msg)
        db_session.commit()
        db_session.refresh(msg)

        assert msg.model == "openai/gpt-4o"

    def test_query_by_session_key(self, db_session):
        """Deve filtrar mensagens por session_key."""
        msg1 = ChatMessage(session_key="s1", role="user", content="a")
        msg2 = ChatMessage(session_key="s2", role="user", content="b")
        db_session.add_all([msg1, msg2])
        db_session.commit()

        results = (
            db_session.query(ChatMessage)
            .filter(ChatMessage.session_key == "s1")
            .all()
        )
        assert len(results) == 1
        assert results[0].content == "a"

    def test_query_by_role(self, db_session):
        """Deve filtrar mensagens pelo campo role."""
        msg1 = ChatMessage(role="user", content="pergunta")
        msg2 = ChatMessage(role="assistant", content="resposta")
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
        before = datetime.now(timezone.utc).replace(tzinfo=None)
        msg = ChatMessage(role="user", content="timestamp test")
        db_session.add(msg)
        db_session.commit()
        db_session.refresh(msg)
        after = datetime.now(timezone.utc).replace(tzinfo=None)

        assert before <= msg.created_at <= after


def _make_user(db_session) -> User:
    """Cria um usuario de testes e retorna."""
    u = User(name="Teste", email="teste@email.com", hashed_password="hash_falso")
    db_session.add(u)
    db_session.flush()
    return u


class TestSession:
    def test_create_session_defaults(self, db_session):
        """Deve criar uma sessao com valores padrao."""
        u = _make_user(db_session)
        s = Session(user_id=u.id)
        db_session.add(s)
        db_session.commit()
        db_session.refresh(s)

        assert s.id is not None
        assert s.title == "Nova conversa"
        assert s.user_id == u.id
        assert isinstance(s.created_at, datetime)
        assert isinstance(s.updated_at, datetime)

    def test_session_custom_title(self, db_session):
        """Deve criar uma sessao com titulo customizado."""
        u = _make_user(db_session)
        s = Session(user_id=u.id, title="Minha sessao de teste")
        db_session.add(s)
        db_session.commit()
        db_session.refresh(s)

        assert s.title == "Minha sessao de teste"

    def test_session_ordered_by_updated_at(self, db_session):
        """Sessoes mais recentes primeiro."""
        from datetime import timedelta

        u = _make_user(db_session)
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        s1 = Session(user_id=u.id, title="Antiga", updated_at=now - timedelta(hours=2))
        s2 = Session(user_id=u.id, title="Recente", updated_at=now)
        db_session.add_all([s1, s2])
        db_session.commit()

        results = db_session.query(Session).order_by(Session.updated_at.desc()).all()
        assert results[0].title == "Recente"
        assert results[1].title == "Antiga"

    def test_session_belongs_to_user(self, db_session):
        """Sessao deve pertencer ao usuario correto."""
        u = _make_user(db_session)
        s = Session(user_id=u.id, title="Minha sessao")
        db_session.add(s)
        db_session.commit()

        assert s.user.id == u.id
        assert u.sessions[0].title == "Minha sessao"


class TestMessage:
    def test_create_message_with_session(self, db_session):
        """Deve criar uma mensagem vinculada a uma sessao."""
        u = _make_user(db_session)
        s = Session(user_id=u.id, title="Sessao teste")
        db_session.add(s)
        db_session.flush()

        msg = Message(session_id=s.id, role="user", content="Ola")
        db_session.add(msg)
        db_session.commit()
        db_session.refresh(msg)

        assert msg.id is not None
        assert msg.session_id == s.id
        assert msg.role == "user"
        assert msg.content == "Ola"
        assert msg.model == "google/gemma-4-31b-it"
        assert isinstance(msg.created_at, datetime)

    def test_message_belongs_to_session(self, db_session):
        """A mensagem deve pertencer a sessao correta (relationship)."""
        u = _make_user(db_session)
        s = Session(user_id=u.id, title="Sessao 1")
        db_session.add(s)
        db_session.flush()

        msg = Message(session_id=s.id, role="assistant", content="Resposta")
        db_session.add(msg)
        db_session.commit()

        assert msg.session.title == "Sessao 1"
        assert s.messages[0].content == "Resposta"

    def test_cascade_delete(self, db_session):
        """Deletar sessao deve deletar as mensagens associadas."""
        u = _make_user(db_session)
        s = Session(user_id=u.id, title="Sessao delete")
        db_session.add(s)
        db_session.flush()

        msg1 = Message(session_id=s.id, role="user", content="msg1")
        msg2 = Message(session_id=s.id, role="assistant", content="msg2")
        db_session.add_all([msg1, msg2])
        db_session.commit()

        db_session.delete(s)
        db_session.commit()

        remaining = db_session.query(Message).filter(
            Message.session_id == s.id
        ).all()
        assert len(remaining) == 0

    def test_content_persists_long_text(self, db_session):
        """Deve persistir conteudos longos corretamente."""
        long_text = "Lorem ipsum " * 200
        msg = ChatMessage(role="user", content=long_text)
        db_session.add(msg)
        db_session.commit()
        db_session.refresh(msg)

        assert msg.content == long_text
