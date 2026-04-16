"""Memoria: salva e consulta pares pergunta->resposta aprovados pelo humano."""
import json
from datetime import date
from pathlib import Path

MEMORIA_PATH = Path(__file__).parent.parent / "base_conhecimento" / "memoria.json"


class Memoria:
    def __init__(self):
        self._path = MEMORIA_PATH
        self._dados: list[dict] = self._carregar()

    def _carregar(self) -> list[dict]:
        if self._path.exists():
            return json.loads(self._path.read_text(encoding="utf-8"))
        return []

    def _salvar(self) -> None:
        self._path.write_text(
            json.dumps(self._dados, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def adicionar(self, pergunta: str, resposta: str, intencao: str) -> None:
        self._dados.append({
            "pergunta": pergunta,
            "resposta": resposta,
            "intencao": intencao,
            "data": str(date.today()),
        })
        self._salvar()

    def exemplos_para(self, intencao: str, limite: int = 5) -> list[dict]:
        """Retorna os ultimos N exemplos aprovados para a intencao."""
        filtrados = [d for d in self._dados if d["intencao"] == intencao]
        return filtrados[-limite:]

    def total(self) -> int:
        return len(self._dados)

    def formatar_contexto(self, intencao: str) -> str:
        exemplos = self.exemplos_para(intencao)
        if not exemplos:
            return ""
        linhas = ["Exemplos de respostas aprovadas anteriormente:\n"]
        for e in exemplos:
            linhas.append(f"P: {e['pergunta']}\nR: {e['resposta']}\n")
        return "\n".join(linhas)
