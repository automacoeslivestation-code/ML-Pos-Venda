"""Enviados: rastreia eventos de follow-up ja processados para evitar duplicatas."""
import json
import logging
import threading
from pathlib import Path

log = logging.getLogger(__name__)

ARQUIVO = Path(__file__).parent.parent / "data" / "enviados.json"


class Enviados:
    def __init__(self):
        self._lock = threading.Lock()

    def verificar_e_marcar(self, order_id: str, evento: str) -> bool:
        """Retorna True se ja foi enviado (nao marca). Retorna False e marca se nao havia."""
        with self._lock:
            dados = self._carregar()
            chave = f"{order_id}_{evento}"
            if chave in dados:
                return True
            dados[chave] = True
            ARQUIVO.parent.mkdir(exist_ok=True)
            ARQUIVO.write_text(json.dumps(dados, indent=2), encoding="utf-8")
            return False


    def _carregar(self) -> dict:
        if ARQUIVO.exists():
            try:
                return json.loads(ARQUIVO.read_text(encoding="utf-8"))
            except Exception as e:
                log.error(f"Erro ao carregar {ARQUIVO}: {e} — iniciando com dict vazio")
                return {}
        return {}
