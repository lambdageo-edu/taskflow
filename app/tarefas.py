"""Tarefas de um projeto: ciclo de vida e permissões."""

import sqlite3
from enum import StrEnum
from typing import Annotated

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, StringConstraints

from app.auth import Atual
from app.db import Banco
from app.projetos import DoMembro, Projeto

rotas = APIRouter(prefix="/projetos/{projeto_id}/tarefas")

Titulo = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
]


class Status(StrEnum):
    PENDENTE = "pendente"
    EM_ANDAMENTO = "em_andamento"
    CONCLUIDA = "concluida"


class Acao(StrEnum):
    INICIAR = "iniciar"
    DEVOLVER = "devolver"
    CONCLUIR = "concluir"
    REABRIR = "reabrir"


# O diagrama de estados do Capítulo 4: ação -> (de onde, para onde).
TRANSICOES = {
    Acao.INICIAR: (Status.PENDENTE, Status.EM_ANDAMENTO),
    Acao.DEVOLVER: (Status.EM_ANDAMENTO, Status.PENDENTE),
    Acao.CONCLUIR: (Status.EM_ANDAMENTO, Status.CONCLUIDA),
    Acao.REABRIR: (Status.CONCLUIDA, Status.EM_ANDAMENTO),
}


class TarefaEntrada(BaseModel):
    titulo: Titulo


class Responsavel(BaseModel):
    usuario_id: int | None


class Tarefa(TarefaEntrada):
    id: int
    projeto_id: int
    status: Status
    responsavel_id: int | None


def buscar(banco: sqlite3.Connection, projeto: Projeto, tarefa_id: int) -> Tarefa:
    # Filtra também pelo projeto: impede alcançar a tarefa de outro projeto trocando o id.
    linha = banco.execute(
        "SELECT * FROM tarefas WHERE id = ? AND projeto_id = ?", (tarefa_id, projeto.id)
    ).fetchone()
    if linha is None:
        raise HTTPException(404, "Tarefa não encontrada")
    return Tarefa(**dict(linha))


@rotas.post("", response_model=Tarefa, status_code=201)
def criar_tarefa(dados: TarefaEntrada, projeto: DoMembro, banco: Banco) -> Tarefa:
    cursor = banco.execute(
        "INSERT INTO tarefas (projeto_id, titulo) VALUES (?, ?)",
        (projeto.id, dados.titulo),
    )
    assert cursor.lastrowid is not None  # nosec B101
    return buscar(banco, projeto, cursor.lastrowid)


@rotas.get("", response_model=list[Tarefa])
def listar_tarefas(
    projeto: DoMembro, banco: Banco, responsavel_id: int | None = None
) -> list[Tarefa]:
    linhas = banco.execute(
        "SELECT * FROM tarefas WHERE projeto_id = ? "
        "AND (? IS NULL OR responsavel_id = ?) ORDER BY id",
        (projeto.id, responsavel_id, responsavel_id),
    )
    return [Tarefa(**dict(x)) for x in linhas]


@rotas.get("/{tarefa_id}", response_model=Tarefa)
def obter_tarefa(tarefa_id: int, projeto: DoMembro, banco: Banco) -> Tarefa:
    return buscar(banco, projeto, tarefa_id)


@rotas.put("/{tarefa_id}/responsavel", response_model=Tarefa)
def definir_responsavel(
    tarefa_id: int, dados: Responsavel, projeto: DoMembro, usuario: Atual, banco: Banco
) -> Tarefa:
    buscar(banco, projeto, tarefa_id)
    sql = "UPDATE tarefas SET responsavel_id = ? WHERE id = ?"
    parametros = [dados.usuario_id, tarefa_id]
    if usuario.id != projeto.dono_id:
        if dados.usuario_id != usuario.id:
            raise HTTPException(403, "Membros só podem assumir tarefas para si")
        # A condição vai no próprio UPDATE: duas pessoas não assumem a mesma tarefa.
        sql += " AND (responsavel_id IS NULL OR responsavel_id = ?)"
        parametros.append(usuario.id)
    try:
        cursor = banco.execute(sql, parametros)
    except sqlite3.IntegrityError:
        raise HTTPException(
            422, "O responsável precisa ser membro do projeto"
        ) from None
    if cursor.rowcount == 0:
        raise HTTPException(403, "A tarefa já tem outro responsável")
    return buscar(banco, projeto, tarefa_id)


@rotas.post("/{tarefa_id}/{acao}", response_model=Tarefa)
def mudar_status(
    tarefa_id: int, acao: Acao, projeto: DoMembro, usuario: Atual, banco: Banco
) -> Tarefa:
    tarefa = buscar(banco, projeto, tarefa_id)
    if usuario.id not in (projeto.dono_id, tarefa.responsavel_id):
        raise HTTPException(403, "Somente o responsável ou o dono do projeto")
    origem, destino = TRANSICOES[acao]
    cursor = banco.execute(
        # O estado e o responsável são conferidos de novo no momento da gravação.
        "UPDATE tarefas SET status = ? WHERE id = ? AND status = ? AND responsavel_id IS ?",
        (destino, tarefa_id, origem, tarefa.responsavel_id),
    )
    if cursor.rowcount == 0:
        raise HTTPException(409, f"Não é possível {acao} uma tarefa neste estado")
    return buscar(banco, projeto, tarefa_id)
