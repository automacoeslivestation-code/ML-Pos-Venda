"""Servidor webhook para receber notificacoes do Mercado Livre em tempo real."""
import asyncio
import logging
from contextlib import asynccontextmanager

import httpx
import uvicorn
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import HTMLResponse

from config import config
from agents.orquestrador import Orquestrador

RAILWAY_API_TOKEN = "9165c94a-5cce-42f9-8ae3-160b38b290b1"
RAILWAY_SERVICE_ID = "96a04753-9183-444c-8ec6-4742ddaf0323"
RAILWAY_ENVIRONMENT_ID = "c2cff01d-acc3-4fd4-a6de-9fc0c2d2bcf9"
ML_REDIRECT_URI = "https://ml-pos-venda-production-3f78.up.railway.app/callback"

log = logging.getLogger(__name__)

orq: Orquestrador | None = None


async def _ciclo_startup():
    """Roda um ciclo imediatamente no startup para pegar perguntas em aberto."""
    await asyncio.sleep(2)
    try:
        log.info("Startup: buscando perguntas em aberto...")
        orq.ciclo()
    except Exception as e:
        log.error(f"Erro no ciclo de startup: {e}")


async def _loop_telegram():
    """Verifica respostas do Telegram a cada 10s, independente do webhook do ML."""
    await asyncio.sleep(5)
    while True:
        try:
            respondidas = orq.telegram_listener.processar_respostas()
            if respondidas:
                log.info(f"Telegram loop: {respondidas} resposta(s) processada(s)")
        except Exception as e:
            log.error(f"Erro no loop Telegram: {e}")
        await asyncio.sleep(10)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global orq
    orq = Orquestrador()
    log.info("Orquestrador iniciado")
    asyncio.create_task(_ciclo_startup())
    asyncio.create_task(_loop_telegram())
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/")
def health():
    return {"status": "ok"}


@app.get("/callback")
async def ml_callback(request: Request):
    """Captura o code do ML OAuth, troca pelo token e atualiza variaveis no Railway."""
    code = request.query_params.get("code", "")
    if not code:
        return HTMLResponse("<h2>Erro: code nao recebido.</h2>", status_code=400)

    # Troca o code pelo token
    resp = httpx.post(
        "https://api.mercadolibre.com/oauth/token",
        data={
            "grant_type": "authorization_code",
            "client_id": config.ML_CLIENT_ID,
            "client_secret": config.ML_CLIENT_SECRET,
            "code": code,
            "redirect_uri": ML_REDIRECT_URI,
        },
        timeout=15,
    )

    if not resp.is_success:
        return HTMLResponse(f"<h2>Erro ao trocar token: {resp.text}</h2>", status_code=500)

    data = resp.json()
    access_token = data.get("access_token", "")
    refresh_token = data.get("refresh_token", "")

    # Atualiza variaveis no Railway via GraphQL
    erros = []
    for nome, valor in [("ML_ACCESS_TOKEN", access_token), ("ML_REFRESH_TOKEN", refresh_token)]:
        if not valor:
            continue
        ok = _atualizar_variavel_railway(nome, valor)
        if not ok:
            erros.append(nome)

    if erros:
        log.error(f"Falha ao atualizar no Railway: {erros}")
        return HTMLResponse(
            f"<h2>Token obtido mas falha ao salvar no Railway: {erros}</h2>"
            f"<p>Salve manualmente:</p>"
            f"<p>ML_ACCESS_TOKEN={access_token}</p>"
            f"<p>ML_REFRESH_TOKEN={refresh_token}</p>",
            status_code=500,
        )

    log.info("Tokens ML atualizados no Railway com sucesso")
    tem_refresh = "SIM" if refresh_token else "NAO (ML nao retornou)"
    return HTMLResponse(
        f"<h2>Tokens atualizados no Railway!</h2>"
        f"<p>refresh_token obtido: <b>{tem_refresh}</b></p>"
        f"<p>O Railway vai reiniciar com os novos tokens em instantes.</p>"
    )


def _atualizar_variavel_railway(nome: str, valor: str) -> bool:
    """Atualiza uma variavel de ambiente no Railway via API GraphQL."""
    query = """
    mutation upsertVariables($input: VariableCollectionUpsertInput!) {
        variableCollectionUpsert(input: $input)
    }
    """
    variables = {
        "input": {
            "projectId": "b12551c3-7c69-4bb6-be0b-884141f51198",
            "serviceId": RAILWAY_SERVICE_ID,
            "environmentId": RAILWAY_ENVIRONMENT_ID,
            "variables": {nome: valor},
        }
    }
    try:
        resp = httpx.post(
            "https://backboard.railway.com/graphql/v2",
            json={"query": query, "variables": variables},
            headers={
                "Authorization": f"Bearer {RAILWAY_API_TOKEN}",
                "Content-Type": "application/json",
            },
            timeout=15,
        )
        return resp.is_success and "errors" not in resp.json()
    except Exception as e:
        log.error(f"Erro ao chamar Railway API: {e}")
        return False


@app.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    """Recebe notificacoes do ML e processa em background."""
    payload = await request.json()
    log.info(f"Webhook recebido: {payload}")
    background_tasks.add_task(processar_notificacao, payload)
    return {"received": True}


_debounce_tasks: dict[str, asyncio.Task] = {}


async def processar_notificacao(payload: dict):
    """Processa a notificacao do ML em background."""
    try:
        topic = payload.get("topic", "")
        resource_id = str(payload.get("resource", "")).split("/")[-1]

        if topic == "questions":
            log.info(f"Processando pergunta id={resource_id}")
            orq.ciclo()
        elif topic == "messages":
            log.info(f"Mensagem recebida pack={resource_id} — aguardando 8s")
            _agendar_processamento_mensagem(resource_id)
    except Exception as e:
        log.error(f"Erro ao processar notificacao: {e}")


def _agendar_processamento_mensagem(pack_id: str) -> None:
    """Debounce: cancela tarefa anterior e agenda nova para daqui 8s."""
    tarefa_anterior = _debounce_tasks.get(pack_id)
    if tarefa_anterior and not tarefa_anterior.done():
        tarefa_anterior.cancel()
    _debounce_tasks[pack_id] = asyncio.create_task(_processar_mensagem_apos_delay(pack_id))


async def _processar_mensagem_apos_delay(pack_id: str) -> None:
    await asyncio.sleep(8)
    try:
        log.info(f"Processando mensagens do pack={pack_id}")
        orq.processar_mensagem_pack(pack_id)
    except Exception as e:
        log.error(f"Erro ao processar pack {pack_id}: {e}")
    finally:
        _debounce_tasks.pop(pack_id, None)


def run():
    uvicorn.run("webhook_server:app", host="0.0.0.0", port=8000, log_level="info")


if __name__ == "__main__":
    run()
