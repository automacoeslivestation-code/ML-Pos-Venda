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

    def _proximo_codigo(self) -> int:
        dados = self._carregar()
        codigos = [v.get("codigo", 0) for v in dados.values() if isinstance(v.get("codigo"), int)]
        return max(codigos, default=0) + 1

    def adicionar(self, interacao_id: str, texto: str, intencao: str, tipo: str,
                  nome_comprador: str = "", titulo_item: str = "", item_id: str = "",
                  order_status: str = "", sugestao: str = "", confianca: float = 0.0) -> int:
        self._dados = self._carregar()
        codigo = self._proximo_codigo()
        self._dados[interacao_id] = {
            "codigo": codigo,
            "texto": texto,
            "intencao": intencao,
            "tipo": tipo,
            "nome_comprador": nome_comprador,
            "titulo_item": titulo_item,
            "item_id": item_id,
            "order_status": order_status,
            "sugestao": sugestao,
            "confianca": confianca,
        }
        self._salvar()
        return codigo

    def buscar(self, interacao_id: str) -> dict | None:
        return self._carregar().get(interacao_id)

    def buscar_por_codigo(self, codigo: int) -> tuple[str, dict] | None:
        for iid, p in self._carregar().items():
            if p.get("codigo") == codigo:
                return iid, p
        return None

    def remover(self, interacao_id: str) -> None:
        self._dados = self._carregar()
        self._dados.pop(interacao_id, None)
        self._salvar()

    def todos(self) -> dict:
        return self._carregar()
