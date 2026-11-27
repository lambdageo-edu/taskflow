from typing import Annotated

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, StringConstraints

app = FastAPI(title="API de Tarefas")

Titulo = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=200),
]


class TarefaEntrada(BaseModel):
    titulo: Titulo
    concluida: bool = False


class Tarefa(TarefaEntrada):
    id: int


_tarefas: dict[int, Tarefa] = {}
_proximo_id = 1


@app.post("/tarefas", response_model=Tarefa, status_code=201)
def criar_tarefa(dados: TarefaEntrada) -> Tarefa:
    global _proximo_id
    tarefa = Tarefa(id=_proximo_id, **dados.model_dump())
    _tarefas[tarefa.id] = tarefa
    _proximo_id += 1
    return tarefa


@app.get("/tarefas", response_model=list[Tarefa])
def listar_tarefas() -> list[Tarefa]:
    return list(_tarefas.values())


@app.get("/tarefas/{tarefa_id}", response_model=Tarefa)
def obter_tarefa(tarefa_id: int) -> Tarefa:
    tarefa = _tarefas.get(tarefa_id)
    if tarefa is None:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    return tarefa


@app.patch("/tarefas/{tarefa_id}/concluir", response_model=Tarefa)
def concluir_tarefa(tarefa_id: int) -> Tarefa:
    tarefa = _tarefas.get(tarefa_id)
    if tarefa is None:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    tarefa.concluida = True
    return tarefa
