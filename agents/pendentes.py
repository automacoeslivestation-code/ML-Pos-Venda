"""Pendentes: rastreia perguntas aguardando resposta do humano."""
import json
from pathlib import Path

PENDENTES_PATH = Path(__file__).parent.parent / "base_conhecimento" / "pendentes.json"


class Pendentes:
    def __init__(self):
        self._path = PENDENTES_PATH
        self._dados: dict[str, dict] = self._carregar()

    def _carregar(self) -> dict:
        if self._path.exists():
            return json.loads(self._path.read_text(encoding="utf-8"))
        return {}

    def _salvar(self) -> None:
        self._path.write_text(
            json.dumps(self._dados, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def adicionar(self, interacao_id: str, texto: str, intencao: str, tipo: str, nome_comprador: str = "") -> None:
        self._dados[interacao_id] = {
            "texto": texto,
            "intencao": intencao,
            "tipo": tipo,
            "nome_comprador": nome_comprador,
        }
        self._salvar()

    def buscar(self, interacao_id: str) -> dict | None:
        return self._dados.get(interacao_id)

    def remover(self, interacao_id: str) -> None:
        self._dados.pop(interacao_id, None)
        self._salvar()

    def todos(self) -> dict:
        return dict(self._dados)
