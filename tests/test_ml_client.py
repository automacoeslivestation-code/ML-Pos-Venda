"""Testes para MLClient — metodos de fallback e consultas."""
import pytest
from unittest.mock import patch, MagicMock

from ml_client import MLClient, CapStatus


def _make_client():
    """Cria MLClient sem depender de variaveis de ambiente."""
    cliente = MLClient()
    cliente._access_token = "fake_token"
    return cliente


def test_buscar_order_id_por_shipment_sucesso():
    """Testa fallback de order_id via /shipments/{id}/items — retorna order_id do primeiro item."""
    cliente = _make_client()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = [
        {"order_id": 456789, "item_id": "MLB123"},
        {"order_id": 456789, "item_id": "MLB124"},
    ]
    mock_resp.raise_for_status = lambda: None

    with patch.object(cliente._http, "get", return_value=mock_resp):
        result = cliente.buscar_order_id_por_shipment("123")

    assert result == "456789"


def test_buscar_order_id_por_shipment_lista_vazia():
    """Testa fallback quando shipment nao tem items — retorna string vazia."""
    cliente = _make_client()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = []
    mock_resp.raise_for_status = lambda: None

    with patch.object(cliente._http, "get", return_value=mock_resp):
        result = cliente.buscar_order_id_por_shipment("999")

    assert result == ""


def test_buscar_order_id_por_shipment_excecao():
    """Testa fallback quando API lanca excecao — retorna string vazia sem propagar."""
    cliente = _make_client()

    with patch.object(cliente._http, "get", side_effect=Exception("timeout")):
        result = cliente.buscar_order_id_por_shipment("ERR")

    assert result == ""


def test_buscar_order_id_por_shipment_formato_dict():
    """Testa fallback quando API retorna dict com chave results em vez de lista direta."""
    cliente = _make_client()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"results": [{"order_id": 111222, "item_id": "MLB999"}]}
    mock_resp.raise_for_status = lambda: None

    with patch.object(cliente._http, "get", return_value=mock_resp):
        result = cliente.buscar_order_id_por_shipment("555")

    assert result == "111222"


# --- Testes de retry em 401 ---

def _make_resp(status_code: int, json_data: dict = None):
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = json_data or {}
    mock.raise_for_status = MagicMock()
    if status_code >= 400:
        mock.raise_for_status.side_effect = Exception(f"HTTP {status_code}")
    return mock


def test_get_renova_token_em_401():
    """_get deve chamar _renovar_token e repetir requisicao quando recebe 401."""
    cliente = _make_client()
    resp_401 = _make_resp(401)
    resp_ok  = _make_resp(200, {"ok": True})

    with patch.object(cliente._http, "get", side_effect=[resp_401, resp_ok]):
        with patch.object(cliente, "_renovar_token") as mock_renovar:
            result = cliente._get("/some/path")

    mock_renovar.assert_called_once()
    assert result == {"ok": True}


def test_post_renova_token_em_401():
    """_post deve chamar _renovar_token e repetir requisicao quando recebe 401."""
    cliente = _make_client()
    resp_401 = _make_resp(401)
    resp_ok  = _make_resp(200, {"created": True})

    with patch.object(cliente._http, "post", side_effect=[resp_401, resp_ok]):
        with patch.object(cliente, "_renovar_token") as mock_renovar:
            result = cliente._post("/some/path", {"key": "val"})

    mock_renovar.assert_called_once()
    assert result == {"created": True}


def test_buscar_cap_disponivel_renova_token_em_401():
    """buscar_cap_disponivel deve renovar token em 401 e tentar novamente."""
    cliente = _make_client()
    resp_401 = _make_resp(401)
    resp_ok  = MagicMock()
    resp_ok.status_code = 200
    resp_ok.json.return_value = [{"option_id": "OTHER", "cap_available": 1}]

    with patch.object(cliente._http, "get", side_effect=[resp_401, resp_ok]):
        with patch.object(cliente, "_renovar_token") as mock_renovar:
            result = cliente.buscar_cap_disponivel("pack123", "OTHER")

    mock_renovar.assert_called_once()
    assert result == CapStatus.DISPONIVEL


# --- Testes de truncamento de texto ---

def test_responder_mensagem_trunca_acima_de_350_chars():
    cliente = _make_client()
    texto_longo = "x" * 400

    resp_ok = _make_resp(200, {"id": "msg1"})
    resp_ok.raise_for_status = MagicMock()

    with patch.object(cliente._http, "post", return_value=resp_ok) as mock_post:
        cliente.responder_mensagem("pack1", texto_longo)

    corpo = mock_post.call_args.kwargs["json"]
    assert len(corpo["text"]) <= 350
    assert corpo["text"].endswith("...")


def test_responder_mensagem_nao_trunca_texto_curto():
    cliente = _make_client()
    texto_curto = "Texto normal de resposta."

    resp_ok = _make_resp(200, {"id": "msg2"})
    resp_ok.raise_for_status = MagicMock()

    with patch.object(cliente._http, "post", return_value=resp_ok) as mock_post:
        cliente.responder_mensagem("pack1", texto_curto)

    corpo = mock_post.call_args.kwargs["json"]
    assert corpo["text"] == texto_curto


def test_enviar_followup_trunca_acima_de_350_chars():
    cliente = _make_client()
    texto_longo = "a" * 400

    resp_ok = _make_resp(200, {"id": "fu1"})
    resp_ok.raise_for_status = MagicMock()

    with patch.object(cliente._http, "post", return_value=resp_ok) as mock_post:
        cliente.enviar_followup("pack1", texto_longo)

    corpo = mock_post.call_args.kwargs["json"]
    assert len(corpo["text"]) <= 350
    assert corpo["text"].endswith("...")


def test_responder_pergunta_trunca_acima_de_2000_chars():
    cliente = _make_client()
    texto_longo = "p" * 2100

    resp_ok = _make_resp(200, {"id": "ans1"})
    resp_ok.raise_for_status = MagicMock()

    with patch.object(cliente._http, "post", return_value=resp_ok) as mock_post:
        cliente.responder_pergunta("12345", texto_longo)

    corpo = mock_post.call_args.kwargs["json"]
    assert len(corpo["text"]) <= 2000
    assert corpo["text"].endswith("...")


def test_buscar_cap_disponivel_envia_tag_post_sale():
    """buscar_cap_disponivel deve passar tag=post_sale como query param na chamada GET."""
    cliente = _make_client()
    resp_ok = MagicMock()
    resp_ok.status_code = 200
    resp_ok.json.return_value = [{"option_id": "OTHER", "cap_available": 2}]

    with patch.object(cliente._http, "get", return_value=resp_ok) as mock_get:
        result = cliente.buscar_cap_disponivel("pack999", "OTHER")

    assert result == CapStatus.DISPONIVEL
    call_kwargs = mock_get.call_args.kwargs
    assert call_kwargs.get("params", {}).get("tag") == "post_sale"


# --- Testes de buscar_nome_comprador ---

def test_buscar_nome_comprador_usa_first_name():
    """Retorna first_name do pedido quando disponivel."""
    cliente = _make_client()
    pedido = {"buyer": {"first_name": "Grasielly", "nickname": "GRASIELLYCLARA20221125204534"}}
    result = cliente.buscar_nome_comprador("123", pedido)
    assert result == "Grasielly"


def test_buscar_nome_comprador_usa_billing_info_quando_sem_first_name():
    """Quando first_name vazio, usa billing_info.name via API."""
    cliente = _make_client()
    pedido = {"buyer": {"first_name": "", "nickname": "GRASIELLYCLARA20221125204534"}}

    resp_ok = MagicMock()
    resp_ok.status_code = 200
    resp_ok.json.return_value = {
        "buyer": {"billing_info": {"name": "Grasielly Clara"}}
    }
    resp_ok.raise_for_status = MagicMock()

    with patch.object(cliente._http, "get", return_value=resp_ok):
        result = cliente.buscar_nome_comprador("123", pedido)

    assert result == "Grasielly Clara"


def test_buscar_nome_comprador_limpa_sufixo_numerico_do_nickname():
    """Quando first_name e billing_info falham, limpa sufixo numerico do nickname."""
    cliente = _make_client()
    pedido = {"buyer": {"first_name": "", "nickname": "GRASIELLYCLARA20221125204534"}}

    with patch.object(cliente, "_get", side_effect=Exception("API indisponivel")):
        result = cliente.buscar_nome_comprador("123", pedido)

    assert result == "Grasiellyclara"


# --- Testes de 403 em buscar_cap_disponivel ---

def test_buscar_cap_disponivel_403_blocked_retorna_conversa_bloqueada():
    """buscar_cap_disponivel deve retornar CONVERSA_BLOQUEADA quando 403 com 'blocked' no body."""
    cliente = _make_client()
    resp_403 = MagicMock()
    resp_403.status_code = 403
    resp_403.text = '{"message": "conversation blocked", "status": 403}'

    with patch.object(cliente._http, "get", return_value=resp_403):
        result = cliente.buscar_cap_disponivel("pack_bloqueado", "OTHER")

    assert result == CapStatus.CONVERSA_BLOQUEADA


def test_buscar_cap_disponivel_403_sem_blocked_retorna_acesso_negado():
    """buscar_cap_disponivel deve retornar ACESSO_NEGADO quando 403 sem 'blocked' no body."""
    cliente = _make_client()
    resp_403 = MagicMock()
    resp_403.status_code = 403
    resp_403.text = '{"message": "Forbidden", "status": 403}'

    with patch.object(cliente._http, "get", return_value=resp_403):
        result = cliente.buscar_cap_disponivel("pack_negado", "OTHER")

    assert result == CapStatus.ACESSO_NEGADO


def test_buscar_cap_disponivel_200_cap_zero_retorna_indisponivel():
    """buscar_cap_disponivel deve retornar INDISPONIVEL quando cap_available=0."""
    cliente = _make_client()
    resp_ok = MagicMock()
    resp_ok.status_code = 200
    resp_ok.json.return_value = [{"option_id": "OTHER", "cap_available": 0}]

    with patch.object(cliente._http, "get", return_value=resp_ok):
        result = cliente.buscar_cap_disponivel("pack_zero", "OTHER")

    assert result == CapStatus.INDISPONIVEL


def test_buscar_cap_disponivel_200_option_id_ausente_retorna_indisponivel():
    """buscar_cap_disponivel deve retornar INDISPONIVEL quando option_id nao esta na resposta."""
    cliente = _make_client()
    resp_ok = MagicMock()
    resp_ok.status_code = 200
    resp_ok.json.return_value = [{"option_id": "SEND_INVOICE_LINK", "cap_available": 2}]

    with patch.object(cliente._http, "get", return_value=resp_ok):
        result = cliente.buscar_cap_disponivel("pack_sem_other", "OTHER")

    assert result == CapStatus.INDISPONIVEL


def test_buscar_cap_disponivel_500_retorna_disponivel_fail_open():
    """buscar_cap_disponivel deve retornar DISPONIVEL (fail-open) em erros 500."""
    cliente = _make_client()
    resp_500 = MagicMock()
    resp_500.status_code = 500

    with patch.object(cliente._http, "get", return_value=resp_500):
        result = cliente.buscar_cap_disponivel("pack_erro", "OTHER")

    assert result == CapStatus.DISPONIVEL
