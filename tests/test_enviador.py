"""Testes do Enviador — logica de follow-up com mocks."""
from unittest.mock import MagicMock

from agents.enviador import Enviador
from ml_client import CapStatus


def _make_enviador(pack_id, order_id, first_name="Comprador"):
    env = Enviador.__new__(Enviador)
    env._ml = MagicMock()
    env._gerador = MagicMock()
    env._enviados = MagicMock()

    env._enviados.verificar_e_marcar.return_value = False
    env._ml.buscar_pedido.return_value = {
        "pack_id": pack_id,
        "id": order_id,
        "buyer": {"nickname": "COMPRADOR_TESTE", "first_name": first_name},
        "order_items": [{"item": {"title": "Camera de Seguranca"}}],
    }
    env._ml.buscar_cap_disponivel.return_value = CapStatus.DISPONIVEL
    env._ml.buscar_nome_comprador.return_value = first_name or "Comprador"
    env._gerador.gerar.return_value = "Mensagem teste"
    return env


# --- Fix 1: pack_id None pula follow-up ---

def test_processar_compra_sem_pack_id_pula_followup():
    """processar_compra com pack_id=None nao tenta enviar via Action Guide."""
    env = _make_enviador(pack_id=None, order_id="777")
    env.processar_compra("777")
    env._ml.enviar_followup.assert_not_called()


def test_processar_envio_sem_pack_id_pula_followup():
    """processar_envio com pack_id=None nao tenta enviar via Action Guide."""
    env = _make_enviador(pack_id=None, order_id="777")
    env.processar_envio("777", "shipment_abc")
    env._ml.enviar_followup.assert_not_called()


def test_processar_entrega_sem_pack_id_pula_followup():
    """processar_entrega com pack_id=None nao tenta enviar via Action Guide."""
    env = _make_enviador(pack_id=None, order_id="777")
    env.processar_entrega("777")
    env._ml.enviar_followup.assert_not_called()


def test_processar_compra_com_pack_id_usa_pack_id():
    env = _make_enviador(pack_id=888, order_id="777")
    env.processar_compra("777")
    env._ml.enviar_followup.assert_called_once()
    args, _ = env._ml.enviar_followup.call_args
    assert args[0] == "888"


def test_processar_compra_ja_enviado_nao_reenvia():
    env = _make_enviador(pack_id=888, order_id="777")
    env._enviados.verificar_e_marcar.return_value = True
    env.processar_compra("777")
    env._ml.enviar_followup.assert_not_called()


def test_processar_entrega_other_disponivel_usa_other():
    """processar_entrega usa OTHER quando OTHER esta disponivel."""
    env = _make_enviador(pack_id=888, order_id="777")
    env._ml.buscar_cap_disponivel.side_effect = lambda pack, option_id="OTHER": CapStatus.DISPONIVEL
    env.processar_entrega("777")
    env._ml.enviar_followup.assert_called_once()
    _, kwargs = env._ml.enviar_followup.call_args
    assert kwargs.get("option_id", "OTHER") == "OTHER"


def test_processar_entrega_other_bloqueado_usa_send_invoice_link():
    """processar_entrega usa SEND_INVOICE_LINK quando OTHER esta bloqueado."""
    env = _make_enviador(pack_id=888, order_id="777")
    def cap_side(pack, option_id="OTHER"):
        if option_id == "OTHER":
            return CapStatus.INDISPONIVEL
        return CapStatus.DISPONIVEL
    env._ml.buscar_cap_disponivel.side_effect = cap_side
    env.processar_entrega("777")
    env._ml.enviar_followup.assert_called_once()
    _, kwargs = env._ml.enviar_followup.call_args
    assert kwargs.get("option_id") == "SEND_INVOICE_LINK"


def test_processar_entrega_ambos_bloqueados_aborta():
    """processar_entrega nao envia mensagem quando OTHER e SEND_INVOICE_LINK estao bloqueados."""
    env = _make_enviador(pack_id=888, order_id="777")
    env._ml.buscar_cap_disponivel.return_value = CapStatus.INDISPONIVEL
    env.processar_entrega("777")
    env._ml.enviar_followup.assert_not_called()


# --- Testes de CONVERSA_BLOQUEADA e ACESSO_NEGADO ---

def test_processar_compra_conversa_bloqueada_usa_endpoint_convencional():
    """processar_compra com CONVERSA_BLOQUEADA usa responder_mensagem como fallback."""
    env = _make_enviador(pack_id=888, order_id="777")
    env._ml.buscar_cap_disponivel.return_value = CapStatus.CONVERSA_BLOQUEADA
    env.processar_compra("777")
    env._ml.enviar_followup.assert_not_called()
    env._ml.responder_mensagem.assert_called_once()
    args, _ = env._ml.responder_mensagem.call_args
    assert args[0] == "888"


def test_processar_compra_acesso_negado_pula_followup():
    """processar_compra com ACESSO_NEGADO nao envia nada."""
    env = _make_enviador(pack_id=888, order_id="777")
    env._ml.buscar_cap_disponivel.return_value = CapStatus.ACESSO_NEGADO
    env.processar_compra("777")
    env._ml.enviar_followup.assert_not_called()
    env._ml.responder_mensagem.assert_not_called()


def test_processar_envio_conversa_bloqueada_usa_endpoint_convencional():
    """processar_envio com CONVERSA_BLOQUEADA usa responder_mensagem como fallback."""
    env = _make_enviador(pack_id=888, order_id="777")
    env._ml.buscar_cap_disponivel.return_value = CapStatus.CONVERSA_BLOQUEADA
    env.processar_envio("777", "ship_abc")
    env._ml.enviar_followup.assert_not_called()
    env._ml.responder_mensagem.assert_called_once()
    args, _ = env._ml.responder_mensagem.call_args
    assert args[0] == "888"


def test_processar_envio_acesso_negado_pula_followup():
    """processar_envio com ACESSO_NEGADO nao envia nada."""
    env = _make_enviador(pack_id=888, order_id="777")
    env._ml.buscar_cap_disponivel.return_value = CapStatus.ACESSO_NEGADO
    env.processar_envio("777", "ship_abc")
    env._ml.enviar_followup.assert_not_called()
    env._ml.responder_mensagem.assert_not_called()


def test_processar_entrega_conversa_bloqueada_usa_endpoint_convencional():
    """processar_entrega com CONVERSA_BLOQUEADA usa responder_mensagem como fallback."""
    env = _make_enviador(pack_id=888, order_id="777")
    env._ml.buscar_cap_disponivel.return_value = CapStatus.CONVERSA_BLOQUEADA
    env.processar_entrega("777")
    env._ml.enviar_followup.assert_not_called()
    env._ml.responder_mensagem.assert_called_once()
    args, _ = env._ml.responder_mensagem.call_args
    assert args[0] == "888"


def test_processar_entrega_acesso_negado_pula_followup():
    """processar_entrega com ACESSO_NEGADO nao envia nada."""
    env = _make_enviador(pack_id=888, order_id="777")
    env._ml.buscar_cap_disponivel.return_value = CapStatus.ACESSO_NEGADO
    env.processar_entrega("777")
    env._ml.enviar_followup.assert_not_called()
    env._ml.responder_mensagem.assert_not_called()


def test_processar_entrega_other_indisponivel_invoice_indisponivel_pula():
    """processar_entrega pula quando OTHER=INDISPONIVEL e SEND_INVOICE_LINK tambem INDISPONIVEL."""
    env = _make_enviador(pack_id=888, order_id="777")
    env._ml.buscar_cap_disponivel.return_value = CapStatus.INDISPONIVEL
    env.processar_entrega("777")
    env._ml.enviar_followup.assert_not_called()
    env._ml.responder_mensagem.assert_not_called()
