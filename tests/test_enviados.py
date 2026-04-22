"""Testes do Enviados — deduplicacao e persistencia com filesystem temporario."""
import json
import pytest
from pathlib import Path

from agents.enviados import Enviados


@pytest.fixture
def enviados_tmp(tmp_path, monkeypatch):
    """Instancia Enviados apontando para um arquivo temporario."""
    arquivo_tmp = tmp_path / "enviados.json"
    monkeypatch.setattr("agents.enviados.ARQUIVO", arquivo_tmp)
    return Enviados(), arquivo_tmp


def test_nao_enviado_retorna_false_quando_vazio(enviados_tmp):
    enviados, _ = enviados_tmp
    assert enviados.verificar_e_marcar("123", "compra") is False


def test_verificar_e_marcar_persiste_no_arquivo(enviados_tmp):
    enviados, arquivo = enviados_tmp
    enviados.verificar_e_marcar("123", "compra")
    assert arquivo.exists()
    dados = json.loads(arquivo.read_text(encoding="utf-8"))
    assert "123_compra" in dados


def test_verificar_e_marcar_retorna_true_na_segunda_chamada(enviados_tmp):
    enviados, _ = enviados_tmp
    enviados.verificar_e_marcar("456", "envio")
    assert enviados.verificar_e_marcar("456", "envio") is True


def test_eventos_distintos_nao_se_confundem(enviados_tmp):
    enviados, _ = enviados_tmp
    enviados.verificar_e_marcar("789", "compra")
    assert enviados.verificar_e_marcar("789", "compra") is True
    assert enviados.verificar_e_marcar("789", "entrega") is False
    assert enviados.verificar_e_marcar("000", "compra") is False


def test_marcar_multiplos_eventos(enviados_tmp):
    enviados, arquivo = enviados_tmp
    enviados.verificar_e_marcar("1", "compra")
    enviados.verificar_e_marcar("1", "envio")
    enviados.verificar_e_marcar("1", "entrega")
    dados = json.loads(arquivo.read_text(encoding="utf-8"))
    assert len(dados) == 3
    assert "1_compra" in dados
    assert "1_envio" in dados
    assert "1_entrega" in dados


def test_carregar_arquivo_json_corrompido_retorna_vazio(tmp_path, monkeypatch):
    arquivo_tmp = tmp_path / "enviados.json"
    arquivo_tmp.write_text("INVALIDO_JSON", encoding="utf-8")
    monkeypatch.setattr("agents.enviados.ARQUIVO", arquivo_tmp)
    enviados = Enviados()
    # Nao deve lancar excecao, deve retornar False
    assert enviados.verificar_e_marcar("x", "y") is False


def test_verificar_e_marcar_retorna_false_e_marca_na_primeira_chamada(enviados_tmp):
    enviados, arquivo = enviados_tmp
    resultado = enviados.verificar_e_marcar("abc", "compra")
    assert resultado is False
    dados = json.loads(arquivo.read_text(encoding="utf-8"))
    assert "abc_compra" in dados


def test_verificar_e_marcar_retorna_true_na_segunda_chamada_2(enviados_tmp):
    enviados, _ = enviados_tmp
    enviados.verificar_e_marcar("abc", "compra")
    resultado = enviados.verificar_e_marcar("abc", "compra")
    assert resultado is True


def test_verificar_e_marcar_eventos_distintos_independentes(enviados_tmp):
    enviados, _ = enviados_tmp
    r1 = enviados.verificar_e_marcar("abc", "compra")
    r2 = enviados.verificar_e_marcar("abc", "envio")
    r3 = enviados.verificar_e_marcar("xyz", "compra")
    assert r1 is False
    assert r2 is False
    assert r3 is False
    assert enviados.verificar_e_marcar("abc", "compra") is True
    assert enviados.verificar_e_marcar("abc", "envio") is True
    assert enviados.verificar_e_marcar("xyz", "compra") is True
