"""Script de autenticacao OAuth ML — captura o code via servidor local."""
import os
import webbrowser
import threading
import httpx
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv, set_key

load_dotenv()

CLIENT_ID = os.getenv("ML_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("ML_CLIENT_SECRET", "")
REDIRECT_URI = "http://localhost:8888/callback"
ENV_FILE = ".env"

code_recebido = None


class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global code_recebido
        params = parse_qs(urlparse(self.path).query)
        code_recebido = params.get("code", [None])[0]
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Autorizado! Pode fechar esta aba.")
        threading.Thread(target=self.server.shutdown).start()

    def log_message(self, *args):
        pass


def main():
    if not CLIENT_ID or not CLIENT_SECRET:
        print("Erro: ML_CLIENT_ID e ML_CLIENT_SECRET precisam estar no .env")
        return

    auth_url = (
        f"https://auth.mercadolivre.com.br/authorization"
        f"?response_type=code"
        f"&client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&scope=offline_access+read+write"
    )

    print("Abrindo navegador para autorizacao...")
    webbrowser.open(auth_url)
    print("Aguardando autorizacao em http://localhost:8888/callback ...")

    server = HTTPServer(("localhost", 8888), CallbackHandler)
    server.serve_forever()

    if not code_recebido:
        print("Erro: code nao recebido.")
        return

    print(f"\nCode recebido! Trocando pelo token...")
    resp = httpx.post(
        "https://api.mercadolibre.com/oauth/token",
        data={
            "grant_type": "authorization_code",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "code": code_recebido,
            "redirect_uri": REDIRECT_URI,
        },
    )

    if resp.status_code != 200:
        print(f"Erro: {resp.status_code} — {resp.text}")
        return

    data = resp.json()
    seller_id = str(data["user_id"])
    access_token = data["access_token"]
    refresh_token = data.get("refresh_token", "")

    set_key(ENV_FILE, "ML_SELLER_ID", seller_id)
    set_key(ENV_FILE, "ML_ACCESS_TOKEN", access_token)

    if refresh_token:
        set_key(ENV_FILE, "ML_REFRESH_TOKEN", refresh_token)
        print("Sucesso! refresh_token obtido — renovacao automatica ativada.")
    else:
        print("Sucesso! access_token salvo (valido por 6h). Sem refresh_token.")

    print(f"ML_SELLER_ID={seller_id}")
    print(".env atualizado.")


if __name__ == "__main__":
    main()
