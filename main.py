"""Entry point do sistema de pos-venda ML.

Modos:
  --ciclo    executa um unico ciclo de polling (teste/cron)
  --polling  loop continuo de polling (fallback sem webhook)
  (padrao)   inicia servidor webhook (recomendado para Railway)
"""
import sys
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

from config import config
from agents.orquestrador import Orquestrador


def main():
    config.validar()

    if "--ciclo" in sys.argv:
        orq = Orquestrador()
        orq.ciclo()
    elif "--polling" in sys.argv:
        orq = Orquestrador()
        orq.rodar()
    else:
        import webhook_server
        webhook_server.run()


if __name__ == "__main__":
    main()
