import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    # Cada teste usa um banco novo, em uma pasta temporária.
    monkeypatch.setenv("TAREFAS_DB", str(tmp_path / "teste.db"))
    with TestClient(app) as cliente:
        yield cliente


def test_criar_tarefa_retorna_201_e_id(client):
    resposta = client.post("/tarefas", json={"titulo": "Estudar pytest"})
    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["titulo"] == "Estudar pytest"
    assert corpo["concluida"] is False
    assert "id" in corpo


def test_criar_tarefa_com_titulo_vazio_retorna_422(client):
    resposta = client.post("/tarefas", json={"titulo": "   "})
    assert resposta.status_code == 422


def test_listar_tarefas_inclui_tarefa_criada(client):
    client.post("/tarefas", json={"titulo": "Ler capítulo 6"})
    resposta = client.get("/tarefas")
    assert resposta.status_code == 200
    titulos = [t["titulo"] for t in resposta.json()]
    assert "Ler capítulo 6" in titulos


def test_obter_tarefa_inexistente_retorna_404(client):
    resposta = client.get("/tarefas/9999")
    assert resposta.status_code == 404


def test_concluir_tarefa_muda_status(client):
    # Dado que existe a tarefa
    criada = client.post("/tarefas", json={"titulo": "Testar conclusão"}).json()
    # Quando eu concluo essa tarefa
    resposta = client.patch(f"/tarefas/{criada['id']}/concluir")
    # Então ela aparece como concluída
    assert resposta.status_code == 200
    assert resposta.json()["concluida"] is True


@pytest.mark.parametrize("tamanho, status", [(200, 201), (201, 422)])
def test_limite_do_titulo(client, tamanho, status):
    resposta = client.post("/tarefas", json={"titulo": "a" * tamanho})
    assert resposta.status_code == status
    assert len(client.get("/tarefas").json()) == (1 if status == 201 else 0)


def test_dados_sobrevivem_ao_reinicio(tmp_path, monkeypatch):
    monkeypatch.setenv("TAREFAS_DB", str(tmp_path / "teste.db"))
    with TestClient(app) as primeiro:
        primeiro.post("/tarefas", json={"titulo": "Persistir"})
    with TestClient(app) as segundo:
        assert [x["titulo"] for x in segundo.get("/tarefas").json()] == ["Persistir"]


def test_titulo_com_sql_e_apenas_texto(client):
    titulo = "x'); DROP TABLE tarefas; --"
    assert client.post("/tarefas", json={"titulo": titulo}).status_code == 201
    assert client.get("/tarefas").json()[0]["titulo"] == titulo
