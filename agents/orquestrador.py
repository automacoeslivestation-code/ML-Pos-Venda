"""Orquestrador: coordena o fluxo entre todos os agentes."""
import time
import logging

from config import config
from ml_client import MLClient
from agents.monitor import Monitor
from agents.analisador import Analisador
from agents.especialista import Especialista
from agents.respondedor import Respondedor
from agents.escalador import Escalador
from agents.telegram_listener import TelegramListener

log = logging.getLogger(__name__)


class Orquestrador:
    def __init__(self):
        ml = MLClient()
        self.ml = ml
        self.monitor = Monitor(ml)
        self.analisador = Analisador()
        self.especialista = Especialista()
        self.respondedor = Respondedor(ml)
        self.escalador = Escalador()
        self.telegram_listener = TelegramListener(ml)

    def ciclo(self) -> None:
        # Processa respostas do humano no Telegram primeiro
        respondidas = self.telegram_listener.processar_respostas()
        if respondidas:
            log.info(f"Respostas humanas processadas: {respondidas}")

        # Busca novas interacoes no ML
        log.info("Buscando novas interacoes...")
        interacoes = self.monitor.buscar_novas()
        log.info(f"Encontradas: {len(interacoes)}")

        for interacao in interacoes:
            try:
                self._processar(interacao)
                self.monitor.marcar_processada(interacao.id)
            except Exception as e:
                log.error(f"Erro ao processar {interacao.id}: {e}")

    def _processar(self, interacao) -> None:
        log.info(f"Processando {interacao.tipo.value} {interacao.id}")

        analise = self.analisador.analisar(interacao)
        log.info(f"  Intencao: {analise.intencao.value} | Urgente: {analise.urgente}")

        contexto = self.especialista.contexto_para(analise.intencao.value)

        resposta = self.respondedor.gerar_e_postar(interacao, analise, contexto)
        log.info(f"  Confianca: {resposta.confianca:.0%} | Postada: {resposta.postada}")

        if not resposta.postada:
            self.escalador.escalar(interacao, analise, resposta)
            log.info(f"  Escalado para humano via Telegram")

    def processar_mensagem_pack(self, resource_id: str) -> bool:
        """Busca mensagens do pack e notifica o humano via Telegram com o texto real.
        Retorna True se encontrou e escalou mensagem do comprador, False caso contrário.
        """
        pack_id = resource_id
        try:
            # Webhook de mensagens manda UUID hex sem tracos — resolve para pack_id
            try:
                msg = self.ml.buscar_mensagem_por_uuid(resource_id)
                pack_id = str(msg.get("pack_id") or resource_id)
                log.info(f"UUID {resource_id} resolvido para pack_id={pack_id}")
            except Exception as e:
                log.info(f"resource_id {resource_id} nao e UUID ({e}), usando como pack_id direto")

            mensagens = self.ml.buscar_mensagens_pack(pack_id)
            log.info(f"pack={pack_id} total de mensagens={len(mensagens)}")

            texto = ""
            nome_comprador = ""
            for msg in reversed(mensagens):
                from_info = msg.get("from", {})
                remetente = str(from_info.get("user_id", ""))
                if remetente != str(config.ML_SELLER_ID):
                    raw_text = msg.get("text", "")
                    if isinstance(raw_text, dict):
                        texto = raw_text.get("plain", "") or str(raw_text)
                    else:
                        texto = str(raw_text)
                    nome_comprador = remetente
                    log.info(f"pack={pack_id} mensagem do comprador={remetente}: '{texto[:60]}'")
                    break

            if not mensagens:
                log.warning(f"pack={pack_id} sem mensagens na API ainda")
                return False

            if not texto:
                log.warning(f"pack={pack_id} sem mensagem do comprador (apenas mensagens do seller)")
                return False

            order_status = self._buscar_status_pedido(pack_id)
            self.escalador.escalar_mensagem(pack_id, nome_comprador, texto, order_status)
            log.info(f"pack={pack_id} escalada com sucesso")
            return True

        except Exception as e:
            log.error(f"Erro ao processar mensagem pack={pack_id}: {e}")
            return False

    def _buscar_status_pedido(self, pack_id: str) -> str:
        """Retorna status legivel do pedido: Não enviado / Em trânsito / Entregue / Cancelado."""
        try:
            pedido = self.ml.buscar_pedido_por_pack(pack_id)
            shipping = pedido.get("shipping", {}) or {}
            ship_status = shipping.get("status", "")
            order_status = pedido.get("status", "")
            if order_status == "cancelled":
                return "Cancelado"
            if ship_status == "delivered":
                return "Entregue"
            if ship_status == "shipped":
                return "Em trânsito"
            return "Não enviado"
        except Exception:
            return ""

    def rodar(self) -> None:
        log.info(f"Iniciando loop com intervalo de {config.POLLING_INTERVAL}s")
        while True:
            self.ciclo()
            time.sleep(config.POLLING_INTERVAL)
