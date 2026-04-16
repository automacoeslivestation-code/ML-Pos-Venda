"""Testes do Respondedor — parsing de resposta e logica de confianca."""
import pytest
from unittest.mock import MagicMock, patch

from agents.respondedor import Respondedor, Resposta
from agents.monitor import Interacao, TipoInteracao
from agents.analisador import Analise, Intencao


def _make_analise(intencao=Intencao.DUVIDA_TECNICA, urgente=False):
    return Analise(intencao=intencao, resumo="teste", urgente=urgente)


def _make_interacao():
    return Interacao(tipo=TipoInteracao.PERGUNTA, id="q1", texto="Como instalar?")


@pytest.fixture
def respondedor():
    ml_mock = MagicMock()
    with patch("agents.respondedor.anthropic.Anthropic"):
        r = Respondedor(ml_mock)
        r._claude = MagicMock()
        return r


def test_parsear_resposta_com_confianca_alta(respondedor):
    texto_bruto = "A instalacao e simples, siga o manual.\nCONFIANCA: 0.9"
    resposta = respondedor._parsear(texto_bruto)
    assert resposta.confianca == 0.9
    assert "CONFIANCA" not in resposta.texto
    assert "A instalacao" in resposta.texto


def test_parsear_resposta_sem_confianca_usa_default(respondedor):
    texto_bruto = "Vou verificar e retorno em breve."
    resposta = respondedor._parsear(texto_bruto)
    # Sem CONFIANCA no texto, usa config.CONFIANCA_MINIMA - 0.1
    assert resposta.confianca < 0.75


def test_nao_posta_se_confianca_baixa(respondedor):
    respondedor._claude.messages.create.return_value = MagicMock(
        content=[MagicMock(text="Nao tenho certeza.\nCONFIANCA: 0.4")]
    )
    resposta = respondedor.gerar_e_postar(_make_interacao(), _make_analise(), "")
    assert resposta.postada is False
    respondedor._ml.responder_pergunta.assert_not_called()


def test_posta_se_confianca_alta(respondedor):
    respondedor._claude.messages.create.return_value = MagicMock(
        content=[MagicMock(text="E compativel sim!\nCONFIANCA: 0.95")]
    )
    resposta = respondedor.gerar_e_postar(_make_interacao(), _make_analise(), "")
    assert resposta.postada is True
    respondedor._ml.responder_pergunta.assert_called_once()
