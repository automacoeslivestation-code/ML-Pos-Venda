"""Script de autenticacao OAuth ML — roda uma vez pra gerar o refresh token."""
import os
import webbrowser
import httpx
from dotenv import load_dotenv, set_key

load_dotenv()

CLIENT_ID = os.getenv("ML_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("ML_CLIENT_SECRET", "")
REDIRECT_URI = "https://webhook.site/88a9cc8f-8539-4cb5-b575-fb785b3cc0fe"
ENV_FILE = ".env"


def main():
    if not CLIENT_ID or not CLIENT_SECRET:
        print("Erro: ML_CLIENT_ID e ML_CLIENT_SECRET precisam estar no .env")
        return

    auth_url = (
        f"https://auth.mercadolivre.com.br/authorization"
        f"?response_type=code"
        f"&client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
    )

    print("Abrindo navegador para autorizacao...")
    print(f"\nURL: {auth_url}\n")
    webbrowser.open(auth_url)

    print("Apos autorizar, o ML vai redirecionar para o webhook.site.")
    print("Copie o valor do parametro 'code' que aparecer na tela do webhook.site.")
    print("Exemplo: https://webhook.site/...?code=TG-XXXXXX\n")

    code = input("Cole o code aqui: ").strip()

    print("\nTrocando code pelo refresh token...")
    resp = httpx.post(
        "https://api.mercadolibre.com/oauth/token",
        data={
            "grant_type": "authorization_code",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "code": code,
            "redirect_uri": REDIRECT_URI,
        },
    )

    if resp.status_code != 200:
        print(f"Erro: {resp.status_code} — {resp.text}")
        return

    data = resp.json()
    refresh_token = data["refresh_token"]
    seller_id = str(data["user_id"])

    set_key(ENV_FILE, "ML_REFRESH_TOKEN", refresh_token)
    set_key(ENV_FILE, "ML_SELLER_ID", seller_id)

    print(f"\nSucesso!")
    print(f"ML_SELLER_ID={seller_id}")
    print(f"ML_REFRESH_TOKEN={refresh_token}")
    print("\n.env atualizado automaticamente.")


if __name__ == "__main__":
    main()
