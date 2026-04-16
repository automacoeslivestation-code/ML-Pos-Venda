"""Formatador: polida a resposta do humano antes de postar no ML."""
from datetime import datetime
import anthropic

from config import config


def _saudacao_horario() -> str:
    hora = datetime.now().hour
    if 5 <= hora < 12:
        return "Bom dia"
    elif 12 <= hora < 18:
        return "Boa tarde"
    else:
        return "Boa noite"


_PROMPT_SISTEMA = """Voce e um assistente que formata respostas de atendimento ao cliente.

Sua tarefa:
1. Reformular o texto para ficar mais profissional e cordial
2. Corrigir erros de digitacao e gramatica
3. Retorne SOMENTE o texto final formatado, sem explicacoes

REGRAS ABSOLUTAS:
- NUNCA adicione informacoes que nao estejam no texto original
- NUNCA invente detalhes, prazos, precos ou especificacoes
- NUNCA remova informacoes do texto original
- Mantenha EXATAMENTE o mesmo significado — apenas melhore a forma

A saudacao ja sera adicionada antes do seu texto — nao a repita.
"""


class Formatador:
    def __init__(self):
        self._client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

    def formatar(self, texto_bruto: str, nome_comprador: str = "") -> str:
        saudacao = _saudacao_horario()

        if nome_comprador:
            abertura = f"{saudacao}, {nome_comprador}! "
        else:
            abertura = f"{saudacao}! "

        msg = self._client.messages.create(
            model=config.MODEL_RESPONDEDOR,
            max_tokens=400,
            system=_PROMPT_SISTEMA,
            messages=[{"role": "user", "content": texto_bruto}],
        )

        texto_formatado = msg.content[0].text.strip()
        return abertura + texto_formatado
