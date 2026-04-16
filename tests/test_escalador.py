"""Testes do Escalador — verifica que manda mensagem correta pro Telegram."""
import pytest
from unittest.mock import MagicMock, patch

from agents.escalador import Escalador
from agents.monitor import Interacao, TipoInteracao
from agents.analisador import Analise, Intencao
from agents.respondedor import Resposta


def _make_cenario(urgente=False):
    interacao = Interacao(tipo=TipoInteracao.PERGUNTA, id="q99", texto="Produto com defeito")
    analise = Analise(intencao=Intencao.TROCA_DEVOLUCAO, resumo="Defeito relatado", urgente=urgente)
    resposta = Resposta(texto="Vamos resolver isso.", confianca=0.5, postada=False)
    return interacao, analise, resposta


def test_envia_mensagem_telegram():
    with patch("agents.escalador.httpx.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200)
        escalador = Escalador()
        escalador.escalar(*_make_cenario())
        mock_post.assert_called_once()


def test_mensagem_contem_id_e_texto():
    with patch("agents.escalador.httpx.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200)
        escalador = Escalador()
        escalador.escalar(*_make_cenario())
        body = mock_post.call_args.kwargs["json"]
        assert "q99" in body["text"]
        assert "Produto com defeito" in body["text"]


def test_emoji_urgente_para_urgente():
    with patch("agents.escalador.httpx.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200)
        escalador = Escalador()
        escalador.escalar(*_make_cenario(urgente=True))
        body = mock_post.call_args.kwargs["json"]
        assert "🚨" in body["text"]
