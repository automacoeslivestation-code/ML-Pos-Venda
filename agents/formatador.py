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


_PROMPT_SISTEMA = """Voce e um revisor ortografico de atendimento ao cliente.

Voce recebe uma mensagem digitada rapidamente por um atendente. Sua unica funcao e:
- Corrigir ortografia e pontuacao
- Ajustar maiusculas/minusculas

NAO faca mais nada alem disso. Mantenha cada palavra, cada frase, cada ideia exatamente como o atendente escreveu.
Se uma palavra parece errada, corrija para a mais provavel pelo contexto e pronto.

NUNCA: reescreva, reformule, expanda, resuma, adicione exemplos, faca perguntas ou altere o sentido.

Retorne SOMENTE o texto corrigido. A saudacao ja sera adicionada — nao a repita.
"""


class Formatador:
    def __init__(self):
        self._client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

    def formatar(self, texto_bruto: str, nome_comprador: str = "") -> str:
        saudacao = _saudacao_horario()
        abertura = f"{saudacao}! "

        msg = self._client.messages.create(
            model=config.MODEL_RESPONDEDOR,
            max_tokens=400,
            system=_PROMPT_SISTEMA,
            messages=[{"role": "user", "content": texto_bruto}],
        )

        texto_formatado = msg.content[0].text.strip()
        return abertura + texto_formatado
