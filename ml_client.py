"""Cliente HTTP para a API do Mercado Livre.

Suporta dois modos:
- Com ML_REFRESH_TOKEN: renova automaticamente
- Com ML_ACCESS_TOKEN: usa direto (expira em 6h — rodar auth_ml.py para renovar)
"""
import logging
import httpx
from config import config
from railway import atualizar_variavel

log = logging.getLogger(__name__)


class TokenExpiradoError(Exception):
    """Levantado quando o access_token expirou e nao ha refresh_token disponivel."""
    pass


class MLClient:
    def __init__(self):
        self._access_token: str = config.ML_ACCESS_TOKEN or ""
        self._http = httpx.Client(base_url=config.ML_BASE_URL, timeout=30)

    def _renovar_token(self) -> None:
        if config.ML_REFRESH_TOKEN:
            resp = self._http.post(
                "/oauth/token",
                data={
                    "grant_type": "refresh_token",
                    "client_id": config.ML_CLIENT_ID,
                    "client_secret": config.ML_CLIENT_SECRET,
                    "refresh_token": config.ML_REFRESH_TOKEN,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            self._access_token = data["access_token"]
            if data.get("refresh_token"):
                config.ML_REFRESH_TOKEN = data["refresh_token"]
                log.info("Refresh token renovado — atualizando no Railway...")
                atualizar_variavel("ML_REFRESH_TOKEN", data["refresh_token"])
                atualizar_variavel("ML_ACCESS_TOKEN", data["access_token"])
        else:
            raise TokenExpiradoError(
                "Access token expirado e ML_REFRESH_TOKEN nao configurado. "
                "Rode: uv run python auth_ml.py"
            )

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._access_token}"}

    def _get(self, path: str, **params) -> dict:
        resp = self._http.get(path, headers=self._headers(), params=params)
        if resp.status_code == 401:
            self._renovar_token()
            resp = self._http.get(path, headers=self._headers(), params=params)
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, body: dict, **params) -> dict:
        resp = self._http.post(path, headers=self._headers(), json=body, params=params or None)
        if resp.status_code == 401:
            self._renovar_token()
            resp = self._http.post(path, headers=self._headers(), json=body, params=params or None)
        resp.raise_for_status()
        return resp.json()

    # --- Follow-up (pedidos e envios) ---

    def buscar_pedido(self, order_id: str) -> dict:
        return self._get(f"/orders/{order_id}")

    def buscar_pedido_por_pack(self, pack_id: str) -> dict:
        """Busca pedido pelo pack_id (usado em mensagens pos-venda)."""
        data = self._get("/orders/search", pack=pack_id, seller=config.ML_SELLER_ID)
        results = data.get("results", [])
        return results[0] if results else {}

    def contar_reclamacoes_abertas(self) -> int:
        """Conta reclamações abertas do seller."""
        data = self._get(
            "/post-purchase/v1/claims/search",
            seller_id=config.ML_SELLER_ID,
            status="opened",
        )
        return data.get("paging", {}).get("total", 0)

    def listar_ship_ids_por_status(self, shipping_status: str) -> list[tuple[str, str]]:
        """Retorna lista de (order_id, ship_id) para o status de envio dado (paginado)."""
        resultados = []
        offset = 0
        limit = 50
        while True:
            params = {
                "seller": config.ML_SELLER_ID,
                "shipping.status": shipping_status,
                "limit": limit,
                "offset": offset,
            }
            resp = self._http.get("/orders/search", headers=self._headers(), params=params)
            if resp.status_code == 401:
                self._renovar_token()
                resp = self._http.get("/orders/search", headers=self._headers(), params=params)
            resp.raise_for_status()
            data = resp.json()
            pagina = [
                (str(o["id"]), str(o["shipping"]["id"]))
                for o in data.get("results", [])
                if o.get("shipping", {}).get("id")
            ]
            resultados.extend(pagina)
            total = data.get("paging", {}).get("total", 0)
            offset += limit
            if offset >= total:
                break
        return resultados

    def buscar_logistic_type(self, ship_id: str) -> str:
        """Retorna o logistic_type do envio (sem x-format-new)."""
        try:
            resp = self._http.get(f"/shipments/{ship_id}", headers=self._headers())
            if resp.status_code == 401:
                self._renovar_token()
                resp = self._http.get(f"/shipments/{ship_id}", headers=self._headers())
            return resp.json().get("logistic_type") or "outros"
        except Exception:
            return "outros"

    def contar_pedidos_por_envio(self, shipping_status: str) -> int:
        """Conta pedidos pelo status de envio (ex: ready_to_ship, shipped)."""
        params = {
            "seller": config.ML_SELLER_ID,
            "order.status": "paid",
            "shipping.status": shipping_status,
        }
        resp = self._http.get("/orders/search", headers=self._headers(), params=params)
        if resp.status_code == 401:
            self._renovar_token()
            resp = self._http.get("/orders/search", headers=self._headers(), params=params)
        resp.raise_for_status()
        return resp.json().get("paging", {}).get("total", 0)

    def buscar_envio(self, shipment_id: str) -> dict:
        resp = self._http.get(
            f"/shipments/{shipment_id}",
            headers={**self._headers(), "x-format-new": "true"},
        )
        if resp.status_code == 401:
            self._renovar_token()
            resp = self._http.get(
                f"/shipments/{shipment_id}",
                headers={**self._headers(), "x-format-new": "true"},
            )
        resp.raise_for_status()
        return resp.json()

    # ID do agente de mensageria ML para Brasil (obrigatorio desde fev/2026)
    _ML_AGENT_ID = 3037675074

    def enviar_followup(self, pack_id: str, texto: str) -> dict:
        """Envia mensagem proativa de follow-up (compra/envio/entrega) via Action Guide."""
        if len(texto) > 350:
            texto = texto[:347] + "..."
        return self._post(
            f"/messages/action_guide/packs/{pack_id}/option",
            {"option_id": "OTHER", "text": texto},
            tag="post_sale",
        )

    # --- Perguntas ---

    def listar_perguntas_novas(self) -> list[dict]:
        data = self._get(
            "/questions/search",
            seller_id=config.ML_SELLER_ID,
            status="UNANSWERED",
        )
        return data.get("questions", [])

    def responder_pergunta(self, question_id: str, texto: str) -> dict:
        if len(texto) > 2000:
            texto = texto[:1997] + "..."
        return self._post("/answers", {"question_id": question_id, "text": texto})

    # --- Mensagens pos-venda ---

    def buscar_mensagem_por_uuid(self, uuid: str) -> dict:
        return self._get(f"/messages/{uuid}", tag="post_sale")

    def listar_nao_lidas(self) -> list[dict]:
        data = self._get("/messages/unread", tag="post_sale", role="seller")
        return data.get("results", [])

    def buscar_mensagens_pack(self, pack_id: str) -> list[dict]:
        data = self._get(
            f"/messages/packs/{pack_id}/sellers/{config.ML_SELLER_ID}",
            tag="post_sale",
        )
        return data.get("messages", [])

    def responder_mensagem(self, pack_id: str, texto: str) -> dict:
        if len(texto) > 350:
            texto = texto[:347] + "..."
        return self._post(
            f"/messages/packs/{pack_id}/sellers/{config.ML_SELLER_ID}",
            {
                "from": {"user_id": int(config.ML_SELLER_ID)},
                "to": {"user_id": self._ML_AGENT_ID},
                "text": texto,
            },
            tag="post_sale",
        )
