"""Enviador: processa eventos do ML e envia mensagens de follow-up."""
import logging
from ml_client import MLClient
from agents.gerador import Gerador
from agents.enviados import Enviados

log = logging.getLogger(__name__)


class Enviador:
    def __init__(self):
        self._ml = MLClient()
        self._gerador = Gerador()
        self._enviados = Enviados()

    def processar_compra(self, order_id: str) -> None:
        if self._enviados.ja_enviou(order_id, "compra"):
            log.info(f"Compra {order_id} ja processada, ignorando")
            return
        try:
            pedido = self._ml.buscar_pedido(order_id)
            pack_id = pedido.get("pack_id")
            if not pack_id:
                log.info(f"Compra {order_id} sem pack_id ainda — follow-up sera enviado no evento de envio")
                return
            dados = self._extrair_dados_pedido(pedido)
            mensagem = self._gerador.gerar("compra", dados)
            self._ml.enviar_followup(str(pack_id), mensagem)
            self._enviados.marcar(order_id, "compra")
            log.info(f"Mensagem de compra enviada para order={order_id}")
        except Exception as e:
            log.error(f"Erro ao processar compra {order_id}: {e}")

    def processar_envio(self, order_id: str, shipment_id: str) -> None:
        if self._enviados.ja_enviou(order_id, "envio"):
            log.info(f"Envio {order_id} ja processado, ignorando")
            return
        try:
            pedido = self._ml.buscar_pedido(order_id)
            dados = self._extrair_dados_pedido(pedido)
            pack_id = str(pedido.get("pack_id") or order_id)
            mensagem = self._gerador.gerar("envio", dados)
            self._ml.enviar_followup(pack_id, mensagem)
            self._enviados.marcar(order_id, "envio")
            log.info(f"Mensagem de envio enviada para order={order_id}")
        except Exception as e:
            log.error(f"Erro ao processar envio {order_id}: {e}")

    def processar_entrega(self, order_id: str) -> None:
        if self._enviados.ja_enviou(order_id, "entrega"):
            log.info(f"Entrega {order_id} ja processada, ignorando")
            return
        try:
            pedido = self._ml.buscar_pedido(order_id)
            dados = self._extrair_dados_pedido(pedido)
            pack_id = str(pedido.get("pack_id") or order_id)
            mensagem = self._gerador.gerar("entrega", dados)
            self._ml.enviar_followup(pack_id, mensagem)
            self._enviados.marcar(order_id, "entrega")
            log.info(f"Mensagem de entrega enviada para order={order_id}")
        except Exception as e:
            log.error(f"Erro ao processar entrega {order_id}: {e}")

    def _extrair_dados_pedido(self, pedido: dict) -> dict:
        comprador = pedido.get("buyer", {})
        itens = pedido.get("order_items", [])
        produto = itens[0].get("item", {}).get("title", "") if itens else ""
        return {
            "nome_comprador": comprador.get("nickname", ""),
            "produto": produto,
            "order_id": str(pedido.get("id", "")),
        }
