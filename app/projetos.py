"""Projetos e membros. Quem não participa de um projeto recebe 404, como se ele não existisse."""

import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, StringConstraints

from app.auth import Atual, Login, Usuario
from app.db import Banco

rotas = APIRouter()

NomeDoProjeto = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
]


class ProjetoEntrada(BaseModel):
    nome: NomeDoProjeto


class Projeto(ProjetoEntrada):
    id: int
    dono_id: int


class NovoMembro(BaseModel):
    login: Login


def projeto_do_membro(projeto_id: int, usuario: Atual, banco: Banco) -> Projeto:
    linha = banco.execute(
        "SELECT p.id, p.nome, p.dono_id FROM projetos p "
        "JOIN membros m ON m.projeto_id = p.id WHERE p.id = ? AND m.usuario_id = ?",
        (projeto_id, usuario.id),
    ).fetchone()
    if linha is None:
        raise HTTPException(404, "Projeto não encontrado")
    return Projeto(**dict(linha))


DoMembro = Annotated[Projeto, Depends(projeto_do_membro)]


@rotas.post("/projetos", response_model=Projeto, status_code=201)
def criar_projeto(dados: ProjetoEntrada, usuario: Atual, banco: Banco) -> Projeto:
    # Projeto e primeiro membro são gravados juntos, ou nenhum dos dois.
    banco.execute("BEGIN")
    with banco:
        cursor = banco.execute(
            "INSERT INTO projetos (nome, dono_id) VALUES (?, ?)",
            (dados.nome, usuario.id),
        )
        assert cursor.lastrowid is not None  # nosec B101
        banco.execute(
            "INSERT INTO membros VALUES (?, ?)", (cursor.lastrowid, usuario.id)
        )
    return Projeto(id=cursor.lastrowid, nome=dados.nome, dono_id=usuario.id)


@rotas.get("/projetos", response_model=list[Projeto])
def listar_projetos(usuario: Atual, banco: Banco) -> list[Projeto]:
    linhas = banco.execute(
        "SELECT p.id, p.nome, p.dono_id FROM projetos p "
        "JOIN membros m ON m.projeto_id = p.id WHERE m.usuario_id = ? ORDER BY p.id",
        (usuario.id,),
    )
    return [Projeto(**dict(x)) for x in linhas]


@rotas.post("/projetos/{projeto_id}/membros", response_model=Usuario, status_code=201)
def adicionar_membro(
    dados: NovoMembro, projeto: DoMembro, usuario: Atual, banco: Banco
) -> Usuario:
    if usuario.id != projeto.dono_id:
        raise HTTPException(403, "Somente o dono do projeto adiciona membros")
    linha = banco.execute(
        "SELECT id, login, nome FROM usuarios WHERE login = ?", (dados.login,)
    ).fetchone()
    if linha is None:
        raise HTTPException(404, "Usuário não encontrado")
    try:
        banco.execute("INSERT INTO membros VALUES (?, ?)", (projeto.id, linha["id"]))
    except sqlite3.IntegrityError:
        raise HTTPException(409, "Usuário já participa do projeto") from None
    return Usuario(**dict(linha))
