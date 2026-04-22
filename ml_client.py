"""Cliente HTTP para a API do Mercado Livre.

Suporta dois modos:
- Com ML_REFRESH_TOKEN: renova automaticamente
- Com ML_ACCESS_TOKEN: usa direto (expira em 6h — rodar auth_ml.py para renovar)
"""
import json
import logging
import os
from enum import Enum
import httpx
from config import config
from railway import atualizar_variavel

log = logging.getLogger(__name__)


class CapStatus(Enum):
    """Status retornado por buscar_cap_disponivel."""
    DISPONIVEL = "disponivel"
    INDISPONIVEL = "indisponivel"       # array vazio ou cap=0
    CONVERSA_BLOQUEADA = "bloqueada"   # 403 com "blocked" no body
    ACESSO_NEGADO = "negado"           # 403 sem "blocked"


_TOKEN_BACKUP_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "data", "refresh_token_backup.json"
)

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
                railway_ok = atualizar_variavel("ML_REFRESH_TOKEN", data["refresh_token"])
                atualizar_variavel("ML_ACCESS_TOKEN", data["access_token"])
                # [FIX #3] Fallback local: salva tokens se Railway falhar
                if not railway_ok:
                    log.warning("Railway falhou — salvando tokens em backup local")
                    try:
                        os.makedirs(os.path.dirname(_TOKEN_BACKUP_PATH), exist_ok=True)
                        with open(_TOKEN_BACKUP_PATH, 'w') as f_bkp:
                            json.dump(
                                {
                                    "ML_REFRESH_TOKEN": data["refresh_token"],
                                    "ML_ACCESS_TOKEN": data["access_token"],
                                },
                                f_bkp,
                            )
                        log.info(f"Tokens salvos em backup local: {_TOKEN_BACKUP_PATH}")
                    except Exception as backup_err:
                        log.error(f"Falha ao salvar backup local dos tokens: {backup_err}")
        else:
            raise TokenExpiradoError(
                "Access token expirado e ML_REFRESH_TOKEN nao configurado. "
                "Rode: uv run python auth_ml.py"
            )

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._access_token}"}

    def _get(self, path: str, extra_headers: dict | None = None, **params) -> dict:
        headers = {**self._headers(), **(extra_headers or {})}
        resp = self._http.get(path, headers=headers, params=params or None)
        if resp.status_code == 401:
            self._renovar_token()
            headers = {**self._headers(), **(extra_headers or {})}
            resp = self._http.get(path, headers=headers, params=params or None)
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
            data = self._get(
                "/orders/search",
                **{
                    "seller": config.ML_SELLER_ID,
                    "shipping.status": shipping_status,
                    "limit": limit,
                    "offset": offset,
                }
            )
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
            data = self._get(f"/shipments/{ship_id}")
            return data.get("logistic_type") or "outros"
        except Exception:
            return "outros"

    def contar_pedidos_por_envio(self, shipping_status: str) -> int:
        """Conta pedidos pelo status de envio (ex: ready_to_ship, shipped)."""
        data = self._get(
            "/orders/search",
            **{
                "seller": config.ML_SELLER_ID,
                "order.status": "paid",
                "shipping.status": shipping_status,
            }
        )
        return data.get("paging", {}).get("total", 0)

    def contar_entregues_no_mes(self) -> int:
        """Conta pedidos finalizados (entregues) no mês atual."""
        from datetime import datetime
        hoje = datetime.now()
        desde = f"{hoje.year}-{hoje.month:02d}-01T00:00:00.000-03:00"
        data = self._get(
            "/orders/search",
            **{
                "seller": config.ML_SELLER_ID,
                "shipping.status": "delivered",
                "order.date_closed.from": desde,
            }
        )
        return data.get("paging", {}).get("total", 0)

    def buscar_envio(self, shipment_id: str) -> dict:
        return self._get(f"/shipments/{shipment_id}", extra_headers={"x-format-new": "true"})

    def buscar_order_id_por_shipment(self, shipment_id: str) -> str:
        """Busca order_id via GET /shipments/{id}/items.

        Fallback para quando buscar_envio nao retorna order_id diretamente.
        Retorna o order_id do primeiro item, ou string vazia se nao encontrado.
        """
        try:
            data = self._get(f"/shipments/{shipment_id}/items")
            items = data if isinstance(data, list) else data.get("results", [])
            if items:
                order_id = items[0].get("order_id")
                if order_id:
                    return str(order_id)
            log.warning(f"buscar_order_id_por_shipment: shipment={shipment_id} sem items ou order_id")
            return ""
        except Exception as e:
            log.error(f"Erro ao buscar order_id do shipment {shipment_id}: {e}")
            return ""

    # ID do agente de mensageria ML para Brasil (obrigatorio desde fev/2026)
    _ML_AGENT_ID = "3037675074"

    def buscar_cap_disponivel(self, pack_id: str, option_id: str = "OTHER") -> CapStatus:
        """Verifica disponibilidade do CAP para o pack e option_id informado.

        Endpoint: GET /messages/action_guide/packs/{pack_id}/caps_available?tag=post_sale

        Retornos:
        - DISPONIVEL: 200 + option_id encontrado com cap_available > 0
        - INDISPONIVEL: 200 + option_id nao encontrado ou cap_available = 0
        - CONVERSA_BLOQUEADA: 403 com "blocked" no body (fallback convencional possivel)
        - ACESSO_NEGADO: 403 sem "blocked" (pack inacessivel, POST falharia igual)
        - DISPONIVEL: outros erros (fail-open para nao bloquear o fluxo)
        """
        try:
            resp = self._http.get(
                f"/messages/action_guide/packs/{pack_id}/caps_available",
                headers=self._headers(),
                params={"tag": "post_sale"},
            )
            if resp.status_code == 401:
                self._renovar_token()
                resp = self._http.get(
                    f"/messages/action_guide/packs/{pack_id}/caps_available",
                    headers=self._headers(),
                    params={"tag": "post_sale"},
                )
            if resp.status_code == 403:
                body_text = resp.text.lower()
                if "blocked" in body_text:
                    log.info(f"buscar_cap_disponivel pack={pack_id} — conversa bloqueada (403 blocked)")
                    return CapStatus.CONVERSA_BLOQUEADA
                log.warning(f"buscar_cap_disponivel pack={pack_id} — acesso negado (403 sem blocked)")
                return CapStatus.ACESSO_NEGADO
            if resp.status_code != 200:
                log.warning(f"buscar_cap_disponivel pack={pack_id} status={resp.status_code} — assumindo disponivel (fail-open)")
                return CapStatus.DISPONIVEL
            caps = resp.json()
            for item in caps:
                if item.get("option_id") == option_id:
                    cap_val = item.get("cap_available", 0)
                    if cap_val > 0:
                        log.info(f"buscar_cap_disponivel pack={pack_id} option_id={option_id} cap_available={cap_val} — disponivel")
                        return CapStatus.DISPONIVEL
                    log.info(f"buscar_cap_disponivel pack={pack_id} option_id={option_id} cap_available={cap_val} — indisponivel")
                    return CapStatus.INDISPONIVEL
            log.warning(f"buscar_cap_disponivel pack={pack_id} option_id={option_id} nao encontrado na resposta — indisponivel")
            return CapStatus.INDISPONIVEL
        except Exception as e:
            log.warning(f"buscar_cap_disponivel pack={pack_id} erro={e} — assumindo disponivel (fail-open)")
            return CapStatus.DISPONIVEL

    def enviar_followup(self, pack_id: str, texto: str, option_id: str = "OTHER") -> dict:
        """Envia mensagem proativa de follow-up (compra/envio/entrega) via Action Guide."""
        if len(texto) > 350:
            texto = texto[:347] + "..."
        return self._post(
            f"/messages/action_guide/packs/{pack_id}/option",
            {"option_id": option_id, "text": texto},
            tag="post_sale",
        )

    # --- Perguntas ---

    def listar_perguntas_novas(self) -> list[dict]:
        data = self._get(
            "/questions/search",
            seller_id=config.ML_SELLER_ID,
            status="UNANSWERED",
            api_version=4,
        )
        return data.get("questions", [])

    def responder_pergunta(self, question_id: str, texto: str) -> dict:
        if len(texto) > 2000:
            texto = texto[:1997] + "..."
        return self._post("/answers", {"question_id": int(question_id), "text": texto})

    # --- Mensagens pos-venda ---

    def buscar_mensagem_por_uuid(self, uuid: str) -> dict:
        return self._get(f"/messages/{uuid}", tag="post_sale")

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
                "from": {"user_id": str(config.ML_SELLER_ID)},
                "to": {"user_id": self._ML_AGENT_ID},
                "text": texto,
            },
            tag="post_sale",
        )

    def buscar_nome_comprador(self, order_id: str, pedido: dict) -> str:
        """Resolve o nome real do comprador em 3 niveis:
        1. buyer.first_name do pedido (disponivel quando nao e ME2)
        2. GET /orders/{order_id}/billing_info -> buyer.billing_info.name ou name
        3. nickname sem sufixo numerico de data (ex: GRASIELLYCLARA20221125 -> Grasiellyclara)
        Retorna sempre uma string nao vazia.
        """
        import re
        buyer = pedido.get("buyer", {})

        # Nivel 1: first_name direto no pedido
        first_name = (buyer.get("first_name") or "").strip()
        if first_name:
            return first_name

        # Nivel 2: billing_info
        try:
            data = self._get(f"/orders/{order_id}/billing_info")
            billing = data.get("buyer", {}).get("billing_info", {})
            name = (billing.get("name") or data.get("name") or "").strip()
            if name:
                return name
        except Exception as e:
            log.warning(f"buscar_nome_comprador billing_info order={order_id} erro={e}")

        # Nivel 3: nickname sem sufixo numerico
        nickname = buyer.get("nickname", "") or ""
        clean = re.sub(r'\d+$', '', nickname).title()
        return clean or nickname
