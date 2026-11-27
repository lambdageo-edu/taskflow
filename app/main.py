from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import auth, projetos, tarefas
from app.db import criar_esquema


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI) -> AsyncIterator[None]:
    criar_esquema()
    yield


app = FastAPI(title="TaskFlow", lifespan=ciclo_de_vida)
app.include_router(auth.rotas)
app.include_router(projetos.rotas)
app.include_router(tarefas.rotas)
