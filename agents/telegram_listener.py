"""TelegramListener: recebe respostas do humano via Telegram e processa."""
import logging
import httpx
from concurrent.futures import ThreadPoolExecutor, as_completed

from config import config
from agents.memoria import Memoria
from agents.pendentes import Pendentes
from agents.formatador import Formatador

log = logging.getLogger(__name__)

TELEGRAM_API = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}"


class TelegramListener:
    def __init__(self, ml_client):
        self._ml = ml_client
        self._memoria = Memoria()
        self._pendentes = Pendentes()
        self._formatador = Formatador()
        self._ultimo_update_id: int = 0

    def processar_respostas(self) -> int:
        """Verifica novas mensagens no Telegram e processa respostas do humano.
        Retorna o numero de respostas processadas.
        """
        updates = self._buscar_updates()
        processadas = 0

        for update in updates:
            self._ultimo_update_id = update["update_id"]
            msg = update.get("message", {})
            chat_id = msg.get("chat", {}).get("id")
            if str(chat_id) != str(config.TELEGRAM_CHAT_ID):
                log.warning(f"Mensagem ignorada de chat_id nao autorizado: {chat_id}")
                continue
            texto = msg.get("text", "").strip()

            if texto.startswith("/r "):
                processadas += self._processar_resposta(texto)
            elif texto == "/listar":
                self._listar_pendentes()
            elif texto == "/status":
                self._status()
            elif texto.startswith("/cancelar "):
                self._cancelar(texto)
            elif texto == "/envios":
                self._envios()
            elif texto == "/comandos":
                self._comandos()

        return processadas

    def _buscar_updates(self) -> list[dict]:
        try:
            resp = httpx.get(
                f"{TELEGRAM_API}/getUpdates",
                params={"offset": self._ultimo_update_id + 1, "timeout": 5},
                timeout=10,
            )
            resp.raise_for_status()
            return resp.json().get("result", [])
        except Exception as e:
            log.error(f"Erro ao buscar updates do Telegram: {e}")
            return []

    def _processar_resposta(self, texto: str) -> int:
        """Formato esperado: /r <codigo> <resposta>"""
        partes = texto.split(" ", 2)
        if len(partes) < 3:
            log.warning(f"Formato invalido: {texto}")
            self._enviar_telegram("Formato invalido. Use: /r <numero> <sua resposta>")
            return 0

        try:
            codigo = int(partes[1])
        except ValueError:
            self._enviar_telegram(f"Código inválido: `{partes[1]}`. Use o número que aparece na notificação.")
            return 0

        resposta_bruta = partes[2].strip()

        resultado = self._pendentes.buscar_por_codigo(codigo)
        if not resultado:
            self._enviar_telegram(f"Código `{codigo}` não encontrado ou já respondido.")
            return 0

        interacao_id, pendente = resultado

        try:
            nome = pendente.get("nome_comprador", "")
            resposta_final = self._formatador.formatar(resposta_bruta, nome)

            self._postar_no_ml(interacao_id, pendente["tipo"], resposta_final)
            self._memoria.adicionar(pendente["texto"], resposta_final, pendente["intencao"])
            self._pendentes.remover(interacao_id)

            self._enviar_telegram(
                f"Postado no ML:\n\n_{resposta_final}_\n\n"
                f"Base atual: {self._memoria.total()} exemplos."
            )
            log.info(f"Resposta humana processada para {interacao_id}")
            return 1
        except Exception as e:
            log.error(f"Erro ao postar resposta para {interacao_id}: {e}")
            self._enviar_telegram(f"Erro ao postar resposta: {e}")
            return 0

    def _postar_no_ml(self, interacao_id: str, tipo: str, texto: str) -> None:
        if tipo == "pergunta":
            self._ml.responder_pergunta(interacao_id, texto)
        else:
            self._ml.responder_mensagem(interacao_id, texto)

    def _listar_pendentes(self) -> None:
        todos = self._pendentes.todos()
        if not todos:
            self._enviar_telegram("Nenhuma pergunta pendente.")
            return

        linhas = [f"📋 Pendentes: {len(todos)}\n"]
        for iid, p in todos.items():
            tipo = p.get("tipo", "pergunta")
            texto = p.get("texto", "")
            codigo = p.get("codigo", iid)
            if tipo == "mensagem":
                order_status = p.get("order_status", "")
                cabecalho = f"💬 Pós-venda" + (f" | {order_status}" if order_status else "")
            else:
                item_id = p.get("item_id", "")
                if item_id:
                    item_id_fmt = item_id.replace("MLB", "MLB-", 1)
                    link = f"https://produto.mercadolivre.com.br/{item_id_fmt}"
                    cabecalho = f"❓ Pergunta | {link}"
                else:
                    cabecalho = "❓ Pergunta"
            linhas.append("——————————————")
            linhas.append(f"{codigo} {cabecalho}")
            linhas.append(texto)
            linhas.append(f"/r {codigo}")

        self._enviar_telegram("\n".join(linhas))

    def _status(self) -> None:
        todos = self._pendentes.todos()
        total = len(todos)
        memoria = self._memoria.total()

        try:
            para_enviar = self._ml.contar_pedidos_por_envio("ready_to_ship")
            em_transito = self._ml.contar_pedidos_por_envio("shipped")
            reclamacoes = self._ml.contar_reclamacoes_abertas()
            alerta = " ⚠️" if reclamacoes > 0 else ""
            pedidos_linha = (
                f"\n——————————————\n"
                f"📦 Para enviar: {para_enviar}\n"
                f"🚚 Em trânsito: {em_transito}\n"
                f"🔴 Reclamações: {reclamacoes}{alerta}"
            )
        except Exception:
            pedidos_linha = ""

        if total == 0:
            self._enviar_telegram(
                f"✅ Tudo em dia!\n\n"
                f"📚 Base: {memoria} respostas aprovadas."
                f"{pedidos_linha}"
            )
        else:
            tipos = {"pergunta": 0, "mensagem": 0}
            for p in todos.values():
                tipos[p.get("tipo", "pergunta")] += 1
            self._enviar_telegram(
                f"📊 {total} pendentes · {memoria} respostas na base\n"
                f"——————————————\n"
                f"❓ Perguntas: {tipos['pergunta']}\n"
                f"💬 Mensagens: {tipos['mensagem']}"
                f"{pedidos_linha}\n\n"
                f"Use /listar para ver detalhes."
            )

    def _cancelar(self, texto: str) -> None:
        """Remove uma pendente sem responder. Formato: /cancelar <numero>"""
        partes = texto.split(" ", 1)
        if len(partes) < 2 or not partes[1].strip():
            self._enviar_telegram("Formato invalido. Use: /cancelar <numero>")
            return
        try:
            codigo = int(partes[1].strip())
        except ValueError:
            self._enviar_telegram(f"Código inválido: `{partes[1].strip()}`.")
            return
        resultado = self._pendentes.buscar_por_codigo(codigo)
        if not resultado:
            self._enviar_telegram(f"Código `{codigo}` não encontrado ou já respondido.")
            return
        interacao_id, _ = resultado
        self._pendentes.remover(interacao_id)
        self._enviar_telegram(f"Pendente `{codigo}` removido sem responder.")
        log.info(f"Pendente {interacao_id} (codigo={codigo}) cancelado pelo humano")

    _LOGISTIC_LABELS = {
        "fulfillment":      "Full",
        "self_service":     "Flex",
        "xd_drop_off":      "Agência",
        "xd_cross_docking": "Cross docking",
        "me2":              "Mercado Envios",
        "me1":              "Correios",
        "outros":           "Outros",
    }

    def _envios(self) -> None:
        self._enviar_telegram("🔍 Buscando detalhes dos envios, aguarde...")
        try:
            para_enviar = self._ml.listar_ship_ids_por_status("ready_to_ship")
            em_transito = self._ml.listar_ship_ids_por_status("shipped")

            def contar_por_tipo(ship_ids: list[tuple[str, str]]) -> dict[str, int]:
                contagem: dict[str, int] = {}
                with ThreadPoolExecutor(max_workers=20) as executor:
                    futures = {executor.submit(self._ml.buscar_logistic_type, sid): sid for _, sid in ship_ids}
                    for future in as_completed(futures):
                        tipo = future.result()
                        contagem[tipo] = contagem.get(tipo, 0) + 1
                return contagem

            tipos_enviar  = contar_por_tipo(para_enviar)
            tipos_transito = contar_por_tipo(em_transito)

            def formatar(contagem: dict[str, int]) -> str:
                if not contagem:
                    return "  Nenhum"
                linhas = []
                for tipo, qtd in sorted(contagem.items(), key=lambda x: -x[1]):
                    label = self._LOGISTIC_LABELS.get(tipo, tipo)
                    linhas.append(f"  {label}: {qtd}")
                return "\n".join(linhas)

            msg = (
                f"📦 Para enviar: {len(para_enviar)}\n"
                f"{formatar(tipos_enviar)}\n\n"
                f"🚚 Em trânsito: {len(em_transito)}\n"
                f"{formatar(tipos_transito)}"
            )
            self._enviar_telegram(msg)
        except Exception as e:
            log.error(f"Erro ao buscar envios: {e}")
            self._enviar_telegram(f"Erro ao buscar envios: {e}")

    def _comandos(self) -> None:
        msg = (
            "Comandos disponíveis:\n\n"
            "/r <id> <resposta>\n"
            "  Responde uma pergunta ou mensagem pendente no ML\n\n"
            "/listar\n"
            "  Mostra todas as perguntas/mensagens aguardando resposta\n\n"
            "/status\n"
            "  Resumo de pendentes e tamanho da base de conhecimento\n\n"
            "/cancelar <id>\n"
            "  Remove um pendente sem responder (ex: comprador ja resolveu)\n\n"
            "/envios\n"
            "  Detalha pedidos para enviar e em trânsito por tipo (Flex, Full, Agência...)\n\n"
            "/comandos\n"
            "  Mostra esta lista"
        )
        self._enviar_telegram(msg)

    def _enviar_telegram(self, texto: str) -> None:
        try:
            httpx.post(
                f"{TELEGRAM_API}/sendMessage",
                json={"chat_id": config.TELEGRAM_CHAT_ID, "text": texto},
                timeout=10,
            )
        except Exception as e:
            log.error(f"Erro ao enviar mensagem Telegram: {e}")
