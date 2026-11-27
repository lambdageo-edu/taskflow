"""Cadastro, login e sessões."""

import hashlib
import secrets
import sqlite3
import time
from typing import Annotated

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field, StringConstraints

from app.db import Banco

DURACAO_DA_SESSAO = 8 * 60 * 60  # segundos

hasher = PasswordHasher()  # Argon2id, com sal aleatório
# Verificado quando o login não existe, para o tempo de resposta não revelar isso.
HASH_FICTICIO = hasher.hash(secrets.token_urlsafe(32))

portador = HTTPBearer(auto_error=False)
rotas = APIRouter()

Login = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True, to_lower=True, pattern=r"^[A-Za-z0-9_.-]{3,30}$"
    ),
]
Nome = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
]


class Cadastro(BaseModel):
    login: Login
    nome: Nome
    senha: str = Field(min_length=15, max_length=128)


class Credenciais(BaseModel):
    login: Login
    senha: str = Field(max_length=128)


class Usuario(BaseModel):
    id: int
    login: str
    nome: str


class Sessao(BaseModel):
    token: str
    tipo: str = "bearer"
    expira_em_segundos: int = DURACAO_DA_SESSAO


def resumo(token: str) -> str:
    # O token é longo e aleatório: SHA-256 basta. Senhas exigem Argon2.
    return hashlib.sha256(token.encode()).hexdigest()


def nao_autenticado(detalhe: str) -> HTTPException:
    return HTTPException(401, detalhe, headers={"WWW-Authenticate": "Bearer"})


Credencial = Annotated[HTTPAuthorizationCredentials | None, Depends(portador)]


def usuario_atual(credencial: Credencial, banco: Banco) -> Usuario:
    if credencial is None:
        raise nao_autenticado("Autenticação necessária")
    linha = banco.execute(
        "SELECT u.id, u.login, u.nome FROM sessoes s JOIN usuarios u ON u.id = s.usuario_id "
        "WHERE s.token_hash = ? AND s.expira_em > ?",
        (resumo(credencial.credentials), int(time.time())),
    ).fetchone()
    if linha is None:
        raise nao_autenticado("Sessão inválida ou expirada")
    return Usuario(**dict(linha))


Atual = Annotated[Usuario, Depends(usuario_atual)]


@rotas.post("/usuarios", response_model=Usuario, status_code=201)
def cadastrar(dados: Cadastro, banco: Banco) -> Usuario:
    try:
        cursor = banco.execute(
            "INSERT INTO usuarios (login, nome, senha_hash) VALUES (?, ?, ?)",
            (dados.login, dados.nome, hasher.hash(dados.senha)),
        )
    except sqlite3.IntegrityError:
        raise HTTPException(409, "Login já utilizado") from None
    assert cursor.lastrowid is not None  # nosec B101
    return Usuario(id=cursor.lastrowid, login=dados.login, nome=dados.nome)


@rotas.post("/sessoes", response_model=Sessao, status_code=201)
def entrar(dados: Credenciais, banco: Banco) -> Sessao:
    linha = banco.execute(
        "SELECT id, senha_hash FROM usuarios WHERE login = ?", (dados.login,)
    ).fetchone()
    try:
        hasher.verify(linha["senha_hash"] if linha else HASH_FICTICIO, dados.senha)
    except VerifyMismatchError:
        linha = None
    if linha is None:
        # A mesma mensagem para login inexistente e senha errada.
        raise nao_autenticado("Login ou senha incorretos")
    banco.execute("DELETE FROM sessoes WHERE expira_em <= ?", (int(time.time()),))
    token = secrets.token_urlsafe(32)
    banco.execute(
        "INSERT INTO sessoes (token_hash, usuario_id, expira_em) VALUES (?, ?, ?)",
        (resumo(token), linha["id"], int(time.time()) + DURACAO_DA_SESSAO),
    )
    return Sessao(token=token)


@rotas.delete("/sessoes", status_code=204)
def sair(credencial: Credencial, usuario: Atual, banco: Banco) -> Response:
    assert credencial is not None  # nosec B101
    banco.execute(
        "DELETE FROM sessoes WHERE token_hash = ?", (resumo(credencial.credentials),)
    )
    return Response(status_code=204)
