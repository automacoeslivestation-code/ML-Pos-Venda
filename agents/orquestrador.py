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

    def rodar(self) -> None:
        log.info(f"Iniciando loop com intervalo de {config.POLLING_INTERVAL}s")
        while True:
            self.ciclo()
            time.sleep(config.POLLING_INTERVAL)
