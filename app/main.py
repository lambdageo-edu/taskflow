import sqlite3
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, StringConstraints

from app import auth
from app.db import Banco, criar_esquema

Titulo = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=200),
]


class TarefaEntrada(BaseModel):
    titulo: Titulo
    concluida: bool = False


class Tarefa(TarefaEntrada):
    id: int


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI) -> AsyncIterator[None]:
    criar_esquema()
    yield


app = FastAPI(title="API de Tarefas", lifespan=ciclo_de_vida)
app.include_router(auth.rotas)
# Nesta etapa, basta estar autenticado: as tarefas ainda são de todos.
autenticado = [Depends(auth.usuario_atual)]


def buscar(banco: sqlite3.Connection, tarefa_id: int) -> Tarefa:
    linha = banco.execute("SELECT * FROM tarefas WHERE id = ?", (tarefa_id,)).fetchone()
    if linha is None:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    return Tarefa(**dict(linha))


@app.post("/tarefas", response_model=Tarefa, status_code=201, dependencies=autenticado)
def criar_tarefa(dados: TarefaEntrada, banco: Banco) -> Tarefa:
    cursor = banco.execute(
        "INSERT INTO tarefas (titulo, concluida) VALUES (?, ?)",
        (dados.titulo, dados.concluida),
    )
    assert cursor.lastrowid is not None  # nosec B101
    return buscar(banco, cursor.lastrowid)


@app.get("/tarefas", response_model=list[Tarefa], dependencies=autenticado)
def listar_tarefas(banco: Banco) -> list[Tarefa]:
    return [
        Tarefa(**dict(x)) for x in banco.execute("SELECT * FROM tarefas ORDER BY id")
    ]


@app.get("/tarefas/{tarefa_id}", response_model=Tarefa, dependencies=autenticado)
def obter_tarefa(tarefa_id: int, banco: Banco) -> Tarefa:
    return buscar(banco, tarefa_id)


@app.patch(
    "/tarefas/{tarefa_id}/concluir", response_model=Tarefa, dependencies=autenticado
)
def concluir_tarefa(tarefa_id: int, banco: Banco) -> Tarefa:
    banco.execute("UPDATE tarefas SET concluida = 1 WHERE id = ?", (tarefa_id,))
    return buscar(banco, tarefa_id)
