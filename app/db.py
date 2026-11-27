"""Acesso ao SQLite. Toda consulta usa parâmetros (?), nunca texto concatenado."""

import os
import sqlite3
from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends

ESQUEMA = """
CREATE TABLE IF NOT EXISTS tarefas (
    id        INTEGER PRIMARY KEY,
    titulo    TEXT NOT NULL CHECK (length(titulo) BETWEEN 1 AND 200),
    concluida INTEGER NOT NULL DEFAULT 0 CHECK (concluida IN (0, 1))
);
"""


def caminho_do_banco() -> str:
    return os.environ.get("TAREFAS_DB", "tarefas.db")


def conectar() -> sqlite3.Connection:
    # isolation_level=None: cada comando é gravado na hora (autocommit).
    # check_same_thread=False: o FastAPI pode abrir e usar em threads diferentes;
    # cada requisição tem a sua conexão, que não é compartilhada.
    con = sqlite3.connect(
        caminho_do_banco(), isolation_level=None, check_same_thread=False
    )
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def criar_esquema() -> None:
    con = conectar()
    try:
        con.executescript(ESQUEMA)
    finally:
        con.close()


def obter_conexao() -> Iterator[sqlite3.Connection]:
    con = conectar()
    try:
        yield con
    finally:
        con.close()


Banco = Annotated[sqlite3.Connection, Depends(obter_conexao)]
