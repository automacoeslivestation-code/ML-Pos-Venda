"""Cliente HTTP para a API do Mercado Livre com renovacao automatica de token."""
import httpx
from config import config


class MLClient:
    def __init__(self):
        self._access_token: str | None = None
        self._http = httpx.Client(base_url=config.ML_BASE_URL, timeout=30)

    def _renovar_token(self) -> None:
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

    def _headers(self) -> dict:
        if not self._access_token:
            self._renovar_token()
        return {"Authorization": f"Bearer {self._access_token}"}

    def _get(self, path: str, **params) -> dict:
        resp = self._http.get(path, headers=self._headers(), params=params)
        if resp.status_code == 401:
            self._renovar_token()
            resp = self._http.get(path, headers=self._headers(), params=params)
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, body: dict) -> dict:
        resp = self._http.post(path, headers=self._headers(), json=body)
        if resp.status_code == 401:
            self._renovar_token()
            resp = self._http.post(path, headers=self._headers(), json=body)
        resp.raise_for_status()
        return resp.json()

    # --- Perguntas ---

    def listar_perguntas_novas(self) -> list[dict]:
        """Retorna perguntas sem resposta do vendedor."""
        data = self._get(
            "/questions/search",
            seller_id=config.ML_SELLER_ID,
            status="UNANSWERED",
        )
        return data.get("questions", [])

    def responder_pergunta(self, question_id: str, texto: str) -> dict:
        return self._post(f"/answers", {"question_id": question_id, "text": texto})

    # --- Mensagens pos-venda ---

    def listar_conversas_abertas(self) -> list[dict]:
        """Retorna conversas recentes de pos-venda."""
        data = self._get(
            f"/messages/packs",
            tag="post_sale",
            role="seller",
            status="active",
            seller_id=config.ML_SELLER_ID,
        )
        return data.get("conversations", [])

    def buscar_mensagens_conversa(self, pack_id: str) -> list[dict]:
        data = self._get(f"/messages/packs/{pack_id}/sellers/{config.ML_SELLER_ID}")
        return data.get("messages", [])

    def responder_mensagem(self, pack_id: str, texto: str) -> dict:
        return self._post(
            f"/messages/packs/{pack_id}/sellers/{config.ML_SELLER_ID}",
            {"text": texto},
        )
