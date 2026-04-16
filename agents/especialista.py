"""Especialista: carrega base de conhecimento dos produtos para embasar respostas."""
from pathlib import Path

from agents.memoria import Memoria


BASE_DIR = Path(__file__).parent.parent / "base_conhecimento"


class Especialista:
    def __init__(self):
        self._cache: dict[str, str] = {}
        self._memoria = Memoria()

    def _carregar(self, nome: str) -> str:
        if nome not in self._cache:
            path = BASE_DIR / f"{nome}.md"
            self._cache[nome] = path.read_text(encoding="utf-8") if path.exists() else ""
        return self._cache[nome]

    def contexto_para(self, intencao: str) -> str:
        """Retorna o contexto relevante da base de conhecimento para a intencao."""
        partes = []

        # Arquivos .md manuais
        partes.append(self._carregar("produtos"))
        partes.append(self._carregar("faq"))

        if intencao in ("troca_devolucao", "reclamacao"):
            partes.append(self._carregar("garantia"))
            partes.append(self._carregar("politicas"))
        elif intencao == "duvida_tecnica":
            partes.append(self._carregar("instalacao"))

        # Exemplos aprovados pelo humano (aprendizado continuo)
        exemplos = self._memoria.formatar_contexto(intencao)
        if exemplos:
            partes.append(exemplos)

        return "\n\n---\n\n".join(p for p in partes if p)
