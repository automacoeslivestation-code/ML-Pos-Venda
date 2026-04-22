"""Enviador: processa eventos do ML e envia mensagens de follow-up."""
import logging
from ml_client import MLClient, CapStatus
from agents.gerador import Gerador
from agents.enviados import Enviados

log = logging.getLogger(__name__)


class Enviador:
    def __init__(self):
        self._ml = MLClient()
        self._gerador = Gerador()
        self._enviados = Enviados()

    def processar_compra(self, order_id: str) -> None:
        if self._enviados.verificar_e_marcar(order_id, "compra"):
            log.info(f"Compra {order_id} ja processada, ignorando")
            return
        try:
            pedido = self._ml.buscar_pedido(order_id)
            pack_id = pedido.get("pack_id")
            if not pack_id:
                log.info(f"Compra {order_id} sem pack_id — Action Guide nao suporta order_id, pulando follow-up")
                return
            pack_id_str = str(pack_id)
            cap = self._ml.buscar_cap_disponivel(pack_id_str, "OTHER")
            dados = self._extrair_dados_pedido(pedido, order_id)
            mensagem = self._gerador.gerar("compra", dados)
            if cap == CapStatus.DISPONIVEL:
                self._ml.enviar_followup(pack_id_str, mensagem)
                log.info(f"Mensagem de compra enviada para order={order_id}")
            elif cap == CapStatus.CONVERSA_BLOQUEADA:
                log.info(f"Conversa bloqueada para pack={pack_id_str} (compra {order_id}), usando endpoint convencional")
                self._ml.responder_mensagem(pack_id_str, mensagem)
                log.info(f"Mensagem de compra (convencional) enviada para order={order_id}")
            elif cap == CapStatus.INDISPONIVEL:
                log.info(f"CAP indisponivel para pack={pack_id_str} (compra {order_id}) — pulando follow-up")
            elif cap == CapStatus.ACESSO_NEGADO:
                log.warning(f"Acesso negado ao pack={pack_id_str} (compra {order_id}) — pulando follow-up")
        except Exception as e:
            log.error(f"Erro ao processar compra {order_id}: {e}")

    def processar_envio(self, order_id: str, shipment_id: str) -> None:
        if self._enviados.verificar_e_marcar(order_id, "envio"):
            log.info(f"Envio {order_id} ja processado, ignorando")
            return
        try:
            pedido = self._ml.buscar_pedido(order_id)
            pack_id = pedido.get("pack_id")
            if not pack_id:
                log.info(f"Envio {order_id} sem pack_id — Action Guide nao suporta order_id, pulando follow-up")
                return
            pack_id_str = str(pack_id)
            cap = self._ml.buscar_cap_disponivel(pack_id_str, "OTHER")
            dados = self._extrair_dados_pedido(pedido, order_id)
            mensagem = self._gerador.gerar("envio", dados)
            if cap == CapStatus.DISPONIVEL:
                self._ml.enviar_followup(pack_id_str, mensagem)
                log.info(f"Mensagem de envio enviada para order={order_id}")
            elif cap == CapStatus.CONVERSA_BLOQUEADA:
                log.info(f"Conversa bloqueada para pack={pack_id_str} (envio {order_id}), usando endpoint convencional")
                self._ml.responder_mensagem(pack_id_str, mensagem)
                log.info(f"Mensagem de envio (convencional) enviada para order={order_id}")
            elif cap == CapStatus.INDISPONIVEL:
                log.info(f"CAP indisponivel para pack={pack_id_str} (envio {order_id}) — pulando follow-up")
            elif cap == CapStatus.ACESSO_NEGADO:
                log.warning(f"Acesso negado ao pack={pack_id_str} (envio {order_id}) — pulando follow-up")
        except Exception as e:
            log.error(f"Erro ao processar envio {order_id}: {e}")

    def processar_entrega(self, order_id: str) -> None:
        if self._enviados.verificar_e_marcar(order_id, "entrega"):
            log.info(f"Entrega {order_id} ja processada, ignorando")
            return
        try:
            pedido = self._ml.buscar_pedido(order_id)
            pack_id = pedido.get("pack_id")
            if not pack_id:
                log.info(f"Entrega {order_id} sem pack_id — Action Guide nao suporta order_id, pulando follow-up")
                return
            pack_id_str = str(pack_id)
            cap_other = self._ml.buscar_cap_disponivel(pack_id_str, "OTHER")
            dados = self._extrair_dados_pedido(pedido, order_id)
            mensagem = self._gerador.gerar("entrega", dados)
            if cap_other == CapStatus.DISPONIVEL:
                self._ml.enviar_followup(pack_id_str, mensagem, option_id="OTHER")
                log.info(f"Mensagem de entrega enviada para order={order_id} option_id=OTHER")
            elif cap_other == CapStatus.CONVERSA_BLOQUEADA:
                log.info(f"Conversa bloqueada para pack={pack_id_str} (entrega {order_id}), usando endpoint convencional")
                self._ml.responder_mensagem(pack_id_str, mensagem)
                log.info(f"Mensagem de entrega (convencional) enviada para order={order_id}")
            elif cap_other == CapStatus.ACESSO_NEGADO:
                log.warning(f"Acesso negado ao pack={pack_id_str} (entrega {order_id}) — pulando follow-up")
            elif cap_other == CapStatus.INDISPONIVEL:
                cap_invoice = self._ml.buscar_cap_disponivel(pack_id_str, "SEND_INVOICE_LINK")
                if cap_invoice == CapStatus.DISPONIVEL:
                    self._ml.enviar_followup(pack_id_str, mensagem, option_id="SEND_INVOICE_LINK")
                    log.info(f"Mensagem de entrega enviada para order={order_id} option_id=SEND_INVOICE_LINK")
                else:
                    log.info(f"CAP indisponivel para pack={pack_id_str} (entrega {order_id}, OTHER e SEND_INVOICE_LINK) — pulando follow-up")
        except Exception as e:
            log.error(f"Erro ao processar entrega {order_id}: {e}")

    def _extrair_dados_pedido(self, pedido: dict, order_id: str) -> dict:
        itens = pedido.get("order_items", [])
        produto = itens[0].get("item", {}).get("title", "") if itens else ""
        nome_comprador = self._ml.buscar_nome_comprador(order_id, pedido)
        return {
            "nome_comprador": nome_comprador,
            "produto": produto,
            "order_id": str(pedido.get("id", "")),
        }
