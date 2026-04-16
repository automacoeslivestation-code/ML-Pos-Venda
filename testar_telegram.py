"""Testa o envio de mensagem pro Telegram sem precisar de deploy."""
import httpx
from dotenv import dotenv_values

env = dotenv_values(".env")
TOKEN = env.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = env.get("TELEGRAM_CHAT_ID", "")

msg = (
    "❓ Pergunta aguardando sua resposta\n\n"
    "Intencao: duvida_tecnica\n"
    "Resumo: Comprador pergunta sobre compatibilidade\n\n"
    "Mensagem do comprador:\n"
    "Essa câmera é compatível com DVR de outra marca? Tem suporte a ONVIF?\n\n"
    "Sugestao do Claude (50% confianca):\n"
    "Depende do modelo, verifique a compatibilidade no manual.\n\n"
    "Para responder:\n/r 99999 sua resposta aqui"
)

resp = httpx.post(
    f"https://api.telegram.org/bot{TOKEN}/sendMessage",
    json={"chat_id": CHAT_ID, "text": msg},
    timeout=10,
)

print(f"Status: {resp.status_code}")
print(resp.json())
