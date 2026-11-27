import pytest
from fastapi.testclient import TestClient

from app.main import app

SENHA = "uma frase bem comprida"


def autenticar(cliente, login="ana"):
    cliente.post("/usuarios", json={"login": login, "nome": login, "senha": SENHA})
    sessao = cliente.post("/sessoes", json={"login": login, "senha": SENHA}).json()
    cliente.headers["Authorization"] = f"Bearer {sessao['token']}"


@pytest.fixture
def client(tmp_path, monkeypatch):
    # Cada teste usa um banco novo, em uma pasta temporária.
    monkeypatch.setenv("TAREFAS_DB", str(tmp_path / "teste.db"))
    with TestClient(app) as cliente:
        autenticar(cliente)
        yield cliente
