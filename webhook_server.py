"""Servidor webhook para receber notificacoes do Mercado Livre em tempo real."""
import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request, BackgroundTasks

from agents.orquestrador import Orquestrador

log = logging.getLogger(__name__)

orq: Orquestrador | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global orq
    orq = Orquestrador()
    log.info("Orquestrador iniciado")
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/")
def health():
    return {"status": "ok"}


@app.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    """Recebe notificacoes do ML e processa em background."""
    payload = await request.json()
    log.info(f"Webhook recebido: {payload}")
    background_tasks.add_task(processar_notificacao, payload)
    return {"received": True}


async def processar_notificacao(payload: dict):
    """Processa a notificacao do ML em background."""
    try:
        topic = payload.get("topic", "")
        resource_id = str(payload.get("resource", "")).split("/")[-1]

        if topic in ("questions", "messages"):
            log.info(f"Processando {topic} id={resource_id}")
            orq.ciclo()
    except Exception as e:
        log.error(f"Erro ao processar notificacao: {e}")


def run():
    uvicorn.run("webhook_server:app", host="0.0.0.0", port=8000, log_level="info")


if __name__ == "__main__":
    run()
