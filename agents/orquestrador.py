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

    def processar_mensagem_pack(self, pack_id: str) -> None:
        """Busca todas as mensagens de um pack e notifica o humano via Telegram."""
        try:
            msgs = self.monitor._client.buscar_mensagens_pack(pack_id)
            if not msgs:
                return

            # Filtra apenas mensagens do comprador
            msgs_comprador = [
                m for m in msgs
                if m.get("from", {}).get("user_id") != int(config.ML_SELLER_ID)
                and m.get("text", "").strip()
            ]
            if not msgs_comprador:
                return

            nome = msgs_comprador[-1].get("from", {}).get("nickname", "")
            textos = [m["text"].strip() for m in msgs_comprador]
            texto_consolidado = "\n".join(f"• {t}" for t in textos) if len(textos) > 1 else textos[0]

            self.escalador.escalar_mensagem(pack_id, nome, texto_consolidado)
            log.info(f"Pack {pack_id} escalado com {len(msgs_comprador)} mensagem(ns)")
        except Exception as e:
            log.error(f"Erro ao processar pack {pack_id}: {e}")

    def rodar(self) -> None:
        log.info(f"Iniciando loop com intervalo de {config.POLLING_INTERVAL}s")
        while True:
            self.ciclo()
            time.sleep(config.POLLING_INTERVAL)
