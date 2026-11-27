import pytest
from conftest import autenticar
from fastapi.testclient import TestClient

from app.main import app


def entrar_como(client, login):
    autenticar(client, login)


def id_de(client, login):
    resposta = client.post(f"/projetos/{client.projeto}/membros", json={"login": login})
    return resposta.json()["id"]


@pytest.fixture
def equipe(client):
    """Ana é dona de um projeto; Bia e Caio são membros; Davi está fora."""
    tokens = {}
    for login in ("bia", "caio", "davi", "ana"):
        entrar_como(client, login)
        tokens[login] = client.headers["Authorization"]
    client.projeto = client.post("/projetos", json={"nome": "Site"}).json()["id"]
    ids = {login: id_de(client, login) for login in ("bia", "caio")}
    url = f"/projetos/{client.projeto}/tarefas"
    tarefa = client.post(url, json={"titulo": "Publicar"}).json()

    def como(login):
        client.headers["Authorization"] = tokens[login]
        return client

    return como, ids, url, f"{url}/{tarefa['id']}"


@pytest.mark.parametrize("tamanho, status", [(200, 201), (201, 422), (0, 422)])
def test_limite_do_titulo(equipe, tamanho, status):
    como, _, url, _ = equipe
    assert como("ana").post(url, json={"titulo": "a" * tamanho}).status_code == status


def test_titulo_com_sql_e_apenas_texto(equipe):
    como, _, url, _ = equipe
    titulo = "x'); DROP TABLE tarefas; --"
    como("ana").post(url, json={"titulo": titulo})
    assert como("ana").get(url).json()[-1]["titulo"] == titulo


def test_ciclo_de_vida_pelo_responsavel(equipe):
    como, ids, _, tarefa = equipe
    como("bia").put(f"{tarefa}/responsavel", json={"usuario_id": ids["bia"]})
    for acao, status in [
        ("iniciar", "em_andamento"),
        ("devolver", "pendente"),
        ("iniciar", "em_andamento"),
        ("concluir", "concluida"),
        ("reabrir", "em_andamento"),
    ]:
        assert como("bia").post(f"{tarefa}/{acao}").json()["status"] == status


def test_tarefa_pendente_nao_pode_ser_concluida(equipe):
    como, _, _, tarefa = equipe
    assert como("ana").post(f"{tarefa}/concluir").status_code == 409


def test_membro_que_nao_e_responsavel_recebe_403(equipe):
    como, ids, _, tarefa = equipe
    como("ana").put(f"{tarefa}/responsavel", json={"usuario_id": ids["bia"]})
    assert como("caio").post(f"{tarefa}/iniciar").status_code == 403
    roubo = como("caio").put(f"{tarefa}/responsavel", json={"usuario_id": ids["caio"]})
    assert roubo.status_code == 403
    assert como("ana").get(tarefa).json()["status"] == "pendente"


def test_membro_nao_atribui_a_outra_pessoa(equipe):
    como, ids, _, tarefa = equipe
    resposta = como("caio").put(
        f"{tarefa}/responsavel", json={"usuario_id": ids["bia"]}
    )
    assert resposta.status_code == 403


def test_responsavel_precisa_ser_membro(equipe):
    como, _, _, tarefa = equipe
    resposta = como("ana").put(f"{tarefa}/responsavel", json={"usuario_id": 999})
    assert resposta.status_code == 422


def test_quem_esta_fora_nao_ve_nem_altera(equipe):
    como, _, url, tarefa = equipe
    assert como("davi").get(url).status_code == 404
    assert como("davi").get(tarefa).status_code == 404
    assert como("davi").post(url, json={"titulo": "invadir"}).status_code == 404
    assert como("davi").post(f"{tarefa}/iniciar").status_code == 404
    assert como("davi").get("/projetos").json() == []


def test_nao_alcanca_tarefa_por_outro_projeto(equipe):
    como, _, _, tarefa = equipe
    outro = como("davi").post("/projetos", json={"nome": "Meu"}).json()["id"]
    id_alheio = tarefa.rsplit("/", 1)[1]
    assert como("davi").get(f"/projetos/{outro}/tarefas/{id_alheio}").status_code == 404


def test_somente_o_dono_adiciona_membros(equipe):
    como, _, url, _ = equipe
    membros = url.replace("/tarefas", "/membros")
    assert como("bia").post(membros, json={"login": "davi"}).status_code == 403
    assert como("ana").post(membros, json={"login": "bia"}).status_code == 409
    assert como("ana").post(membros, json={"login": "ninguem"}).status_code == 404


def test_filtro_por_responsavel(equipe):
    como, ids, url, tarefa = equipe
    como("ana").put(f"{tarefa}/responsavel", json={"usuario_id": ids["bia"]})
    como("ana").post(url, json={"titulo": "Outra"})
    filtradas = como("ana").get(url, params={"responsavel_id": ids["bia"]}).json()
    assert [x["titulo"] for x in filtradas] == ["Publicar"]


def test_dados_sobrevivem_ao_reinicio(tmp_path, monkeypatch):
    monkeypatch.setenv("TAREFAS_DB", str(tmp_path / "teste.db"))
    with TestClient(app) as primeiro:
        autenticar(primeiro)
        primeiro.post("/projetos", json={"nome": "Persistir"})
    with TestClient(app) as segundo:
        autenticar(segundo)
        assert [x["nome"] for x in segundo.get("/projetos").json()] == ["Persistir"]
