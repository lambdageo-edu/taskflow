import sqlite3

import pytest
from conftest import SENHA


def test_sem_token_retorna_401(client):
    del client.headers["Authorization"]
    assert client.get("/tarefas").status_code == 401


def test_token_inventado_retorna_401(client):
    client.headers["Authorization"] = "Bearer inventado"
    assert client.get("/tarefas").status_code == 401


def test_logout_invalida_o_token(client):
    assert client.delete("/sessoes").status_code == 204
    assert client.get("/tarefas").status_code == 401


def test_sessao_expirada_retorna_401(client, tmp_path):
    con = sqlite3.connect(tmp_path / "teste.db")
    con.execute("UPDATE sessoes SET expira_em = 0")
    con.commit()
    con.close()
    assert client.get("/tarefas").status_code == 401


def test_banco_nao_guarda_senha_nem_token(client, tmp_path):
    token = client.headers["Authorization"].removeprefix("Bearer ")
    con = sqlite3.connect(tmp_path / "teste.db")
    despejo = "\n".join(con.iterdump())
    con.close()
    assert SENHA not in despejo
    assert token not in despejo
    assert "$argon2id$" in despejo


@pytest.mark.parametrize("login", ["ana", "ninguem"])
def test_erro_de_login_nao_revela_se_usuario_existe(client, login):
    resposta = client.post("/sessoes", json={"login": login, "senha": "errada"})
    assert resposta.status_code == 401
    assert resposta.json() == {"detail": "Login ou senha incorretos"}


def test_senha_curta_e_login_repetido(client):
    curta = {"login": "bia", "nome": "Bia", "senha": "curta"}
    assert client.post("/usuarios", json=curta).status_code == 422
    repetido = {"login": "ANA", "nome": "Outra", "senha": SENHA}
    assert client.post("/usuarios", json=repetido).status_code == 409
