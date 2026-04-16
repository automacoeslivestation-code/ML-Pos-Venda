"""Script de autenticacao OAuth ML — roda para gerar/renovar o token."""
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
        f"&scope=offline_access+read+write"
    )

    print("Acesse essa URL no navegador onde voce esta logado no Mercado Livre:")
    print(f"\n{auth_url}\n")
    webbrowser.open(auth_url)

    print("Apos autorizar, copie o 'code' que aparecer no webhook.site.")
    print("Exemplo: code=TG-XXXXXX\n")

    code = input("Cole o code aqui: ").strip()

    print("\nTrocando code pelo token...")
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
    seller_id = str(data["user_id"])
    access_token = data["access_token"]
    refresh_token = data.get("refresh_token", "")

    set_key(ENV_FILE, "ML_SELLER_ID", seller_id)
    set_key(ENV_FILE, "ML_ACCESS_TOKEN", access_token)

    if refresh_token:
        set_key(ENV_FILE, "ML_REFRESH_TOKEN", refresh_token)
        print(f"\nSucesso! refresh_token obtido — renovacao automatica ativada.")
    else:
        print(f"\nSucesso! access_token salvo (valido por 6h).")
        print("Para renovar, rode este script novamente.")

    print(f"ML_SELLER_ID={seller_id}")
    print(".env atualizado automaticamente.")


if __name__ == "__main__":
    main()
