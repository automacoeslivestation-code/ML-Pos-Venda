"""Testes do Analisador sem chamadas de API (mock)."""
import json
import pytest
from unittest.mock import MagicMock, patch

from agents.monitor import Interacao, TipoInteracao
from agents.analisador import Analisador, Intencao


def _make_interacao(texto: str) -> Interacao:
    return Interacao(tipo=TipoInteracao.PERGUNTA, id="123", texto=texto)


def _mock_resposta(intencao: str, resumo: str, urgente: bool):
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text=json.dumps({
        "intencao": intencao,
        "resumo": resumo,
        "urgente": urgente,
    }))]
    return mock_msg


@pytest.fixture
def analisador():
    with patch("agents.analisador.anthropic.Anthropic"):
        a = Analisador()
        a._client = MagicMock()
        return a


def test_classifica_duvida_tecnica(analisador):
    analisador._client.messages.create.return_value = _mock_resposta(
        "duvida_tecnica", "Comprador pergunta sobre compatibilidade", False
    )
    resultado = analisador.analisar(_make_interacao("Essa camera e compativel com DVR de outra marca?"))
    assert resultado.intencao == Intencao.DUVIDA_TECNICA
    assert resultado.urgente is False


def test_classifica_troca_devolucao_urgente(analisador):
    analisador._client.messages.create.return_value = _mock_resposta(
        "troca_devolucao", "Produto chegou com defeito", True
    )
    resultado = analisador.analisar(_make_interacao("A camera chegou quebrada, quero devolver"))
    assert resultado.intencao == Intencao.TROCA_DEVOLUCAO
    assert resultado.urgente is True


def test_classifica_prazo_entrega(analisador):
    analisador._client.messages.create.return_value = _mock_resposta(
        "prazo_entrega", "Comprador quer saber quando chega", False
    )
    resultado = analisador.analisar(_make_interacao("Quando meu pedido vai chegar?"))
    assert resultado.intencao == Intencao.PRAZO_ENTREGA


def test_usa_historico_na_analise(analisador):
    analisador._client.messages.create.return_value = _mock_resposta(
        "duvida_tecnica", "Duvida sobre instalacao", False
    )
    interacao = Interacao(
        tipo=TipoInteracao.MENSAGEM,
        id="456",
        texto="Como conecto o cabo?",
        historico=["Oi, comprei a camera", "Como instalo?"],
    )
    analisador.analisar(interacao)
    call_args = analisador._client.messages.create.call_args
    prompt = call_args.kwargs["messages"][0]["content"]
    assert "Historico" in prompt
