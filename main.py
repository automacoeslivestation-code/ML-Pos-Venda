"""Entry point do sistema de pos-venda ML."""
import sys
from config import config
from agents.orquestrador import Orquestrador


def main():
    config.validar()
    orq = Orquestrador()

    if "--ciclo" in sys.argv:
        # Executa um unico ciclo (util para testes e cron externo)
        orq.ciclo()
    else:
        # Loop continuo
        orq.rodar()


if __name__ == "__main__":
    main()
