# TaskFlow

Gerenciador de tarefas de equipe em FastAPI e SQLite. É o projeto condutor do livro
[Desenvolvimento de Software](https://lambdageo-edu.github.io/book-engenharia-de-software/).

## Como rodar

Requer Python 3.14.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

A documentação interativa fica em <http://localhost:8000/docs>. O banco é o arquivo
`tarefas.db`, ou o caminho indicado em `TAREFAS_DB`.

Com Docker:

```bash
docker build -t taskflow .
docker run -p 127.0.0.1:8000:8000 -v taskflow-dados:/dados taskflow
```

## Como testar

```bash
ruff check . && ruff format --check . && mypy app
pytest --cov=app --cov-fail-under=80
```

## Primeiro uso

1. `POST /usuarios` com `login`, `nome` e `senha` (pelo menos 15 caracteres).
2. `POST /sessoes` com `login` e `senha`; guarde o `token`.
3. Envie `Authorization: Bearer <token>` (no `/docs`, botão *Authorize*).
4. `POST /projetos`, depois `POST /projetos/{id}/tarefas`.

## Regras

| Quem | Pode |
|---|---|
| Membro do projeto | ver e criar tarefas; assumir uma tarefa sem responsável |
| Responsável pela tarefa | iniciar, devolver, concluir e reabrir |
| Dono do projeto | tudo isso, adicionar membros e definir responsáveis |
| Quem não é membro | nada: recebe 404 |

## Evolução

| Tag | Etapa |
|---|---|
| `v1-memoria` | API em memória (cap. 6) |
| `v2-pipeline` | pipeline, imagem e verificações de segurança (cap. 7) |
| `v3-sqlite` | persistência |
| `v4-login` | usuários e sessões |
| `v5-equipe` | projetos, membros, responsável e status |

Para ver uma etapa: `git checkout v3-sqlite`.

## O que falta para uso real

* HTTPS (o token e a senha trafegam em texto puro sem ele);
* limite de tentativas de login e de requisições;
* recuperação e troca de senha, confirmação de identidade;
* migrações do esquema do banco e cópias de segurança.

## Licença

[MIT](LICENSE). Você pode usar, modificar e distribuir o código, mantendo o aviso de autoria.
