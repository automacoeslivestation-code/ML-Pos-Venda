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

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
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

    def processar_mensagem_pack(self, pack_id: str) -> None:
        """Busca mensagens do pack e notifica o humano via Telegram com o texto real."""
        try:
            mensagens = self.ml.buscar_mensagens_pack(pack_id)
            # Pega a ultima mensagem do comprador
            texto = ""
            nome_comprador = ""
            for msg in reversed(mensagens):
                from_info = msg.get("from", {})
                remetente = str(from_info.get("user_id", ""))
                if remetente != str(config.ML_SELLER_ID):
                    texto = str(msg.get("text", ""))
                    nome_comprador = remetente
                    break

            if texto:
                order_status = self._buscar_status_pedido(pack_id)
                self.escalador.escalar_mensagem(pack_id, nome_comprador, texto, order_status)
                log.info(f"Mensagem pack={pack_id} escalada: '{texto[:60]}'")
            else:
                self.escalador.escalar_mensagem_simples()
                log.info(f"Mensagem pack={pack_id} sem texto do comprador, notificacao simples")
        except Exception as e:
            log.error(f"Erro ao processar mensagem pack {pack_id}: {e}")
            self.escalador.escalar_mensagem_simples()

    def _buscar_status_pedido(self, order_id: str) -> str:
        """Retorna status legivel do pedido: Não enviado / Em trânsito / Entregue / Cancelado."""
        try:
            pedido = self.ml.buscar_pedido(order_id)
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
