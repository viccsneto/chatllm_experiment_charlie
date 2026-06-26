from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.services.openrouter import stream_reply


class TestStreamEdgeCases:
    """Testes para edge cases no streaming do OpenRouter."""

    @staticmethod
    def _make_stream_mock(mock_aiter_lines_fn, status_code=200):
        mock_response = MagicMock()
        mock_response.status_code = status_code
        mock_response.aiter_lines = mock_aiter_lines_fn

        class FakeStreamCtx:
            async def __aenter__(self):
                return mock_response

            async def __aexit__(self, *args):
                pass

        class FakeClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            def stream(self, *args, **kwargs):
                return FakeStreamCtx()

        return FakeClient()

    @pytest.mark.asyncio
    async def test_empty_choices_array_skipped(self):
        """Deve ignorar eventos com choices array vazio (IndexError guard)."""
        async def mock_aiter_lines():
            yield 'data: {"choices":[]}'  # choices vazio — deve ser ignorado
            yield 'data: {"choices":[{"delta":{"content":"valido"}}]}'
            yield "data: [DONE]"

        mock_client = self._make_stream_mock(mock_aiter_lines)

        with patch("backend.services.openrouter.OPENROUTER_API_KEY", "sk-test"):
            with patch("httpx.AsyncClient", return_value=mock_client):
                deltas = []
                async for delta in stream_reply(user_message="Teste", history=[]):
                    deltas.append(delta)

                assert deltas == ["valido"], f"Esperado ['valido'], obtido {deltas}"

    @pytest.mark.asyncio
    async def test_missing_choices_key_skipped(self):
        """Deve ignorar eventos sem a chave choices."""
        async def mock_aiter_lines():
            yield 'data: {"foo":"bar"}'  # sem choices
            yield 'data: {"choices":[{"delta":{"content":"ok"}}]}'
            yield "data: [DONE]"

        mock_client = self._make_stream_mock(mock_aiter_lines)

        with patch("backend.services.openrouter.OPENROUTER_API_KEY", "sk-test"):
            with patch("httpx.AsyncClient", return_value=mock_client):
                deltas = []
                async for delta in stream_reply(user_message="Teste", history=[]):
                    deltas.append(delta)

                assert deltas == ["ok"]