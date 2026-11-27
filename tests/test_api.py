import pytest
from fastapi.testclient import TestClient

from app import main

client = TestClient(main.app)


@pytest.fixture(autouse=True)
def estado_limpo():
    main._tarefas.clear()
    main._proximo_id = 1


def test_criar_tarefa_retorna_201_e_id():
    resposta = client.post("/tarefas", json={"titulo": "Estudar pytest"})
    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["titulo"] == "Estudar pytest"
    assert corpo["concluida"] is False
    assert "id" in corpo


def test_criar_tarefa_com_titulo_vazio_retorna_422():
    resposta = client.post("/tarefas", json={"titulo": "   "})
    assert resposta.status_code == 422


def test_listar_tarefas_inclui_tarefa_criada():
    client.post("/tarefas", json={"titulo": "Ler capítulo 6"})
    resposta = client.get("/tarefas")
    assert resposta.status_code == 200
    titulos = [t["titulo"] for t in resposta.json()]
    assert "Ler capítulo 6" in titulos


def test_obter_tarefa_inexistente_retorna_404():
    resposta = client.get("/tarefas/9999")
    assert resposta.status_code == 404


def test_concluir_tarefa_muda_status():
    # Dado que existe a tarefa
    criada = client.post("/tarefas", json={"titulo": "Testar conclusão"}).json()
    # Quando eu concluo essa tarefa
    resposta = client.patch(f"/tarefas/{criada['id']}/concluir")
    # Então ela aparece como concluída
    assert resposta.status_code == 200
    assert resposta.json()["concluida"] is True


@pytest.mark.parametrize("tamanho, status", [(200, 201), (201, 422)])
def test_limite_do_titulo(tamanho, status):
    resposta = client.post("/tarefas", json={"titulo": "a" * tamanho})
    assert resposta.status_code == status
    assert len(client.get("/tarefas").json()) == (1 if status == 201 else 0)
