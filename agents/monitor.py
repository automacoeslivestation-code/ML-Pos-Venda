"""Monitor: busca perguntas e mensagens novas no Mercado Livre."""
from dataclasses import dataclass, field
from enum import Enum

from ml_client import MLClient


class TipoInteracao(Enum):
    PERGUNTA = "pergunta"
    MENSAGEM = "mensagem"


@dataclass
class Interacao:
    tipo: TipoInteracao
    id: str               # question_id ou pack_id
    texto: str            # ultima mensagem ou pergunta
    item_id: str = ""     # MLB... do anuncio relacionado
    ordem_id: str = ""    # numero do pedido (mensagens pos-venda)
    nome_comprador: str = ""
    historico: list[str] = field(default_factory=list)


class Monitor:
    def __init__(self, client: MLClient):
        self._client = client
        self._respondidas: set[str] = set()  # IDs ja processados nessa sessao

    def buscar_novas(self) -> list[Interacao]:
        interacoes: list[Interacao] = []
        interacoes.extend(self._buscar_perguntas())
        interacoes.extend(self._buscar_mensagens())
        return interacoes

    def _buscar_perguntas(self) -> list[Interacao]:
        perguntas = self._client.listar_perguntas_novas()
        resultado = []
        for p in perguntas:
            qid = str(p["id"])
            if qid in self._respondidas:
                continue
            from_data = p.get("from", {})
            nome = from_data.get("nickname", "")
            resultado.append(
                Interacao(
                    tipo=TipoInteracao.PERGUNTA,
                    id=qid,
                    texto=p["text"],
                    item_id=p.get("item_id", ""),
                    nome_comprador=nome,
                )
            )
        return resultado

    def _buscar_mensagens(self) -> list[Interacao]:
        conversas = self._client.listar_conversas_abertas()
        resultado = []
        for conv in conversas:
            pack_id = str(conv["id"])
            if pack_id in self._respondidas:
                continue
            msgs = self._client.buscar_mensagens_conversa(pack_id)
            if not msgs:
                continue
            ultima = msgs[-1]
            # So processar se a ultima mensagem e do comprador
            if ultima.get("from", {}).get("user_id") == ultima.get("seller_id"):
                continue
            historico = [m["text"] for m in msgs if "text" in m]
            resultado.append(
                Interacao(
                    tipo=TipoInteracao.MENSAGEM,
                    id=pack_id,
                    texto=ultima.get("text", ""),
                    ordem_id=str(conv.get("order_id", "")),
                    historico=historico,
                )
            )
        return resultado

    def marcar_processada(self, interacao_id: str) -> None:
        self._respondidas.add(interacao_id)
