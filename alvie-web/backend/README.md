# Alvie Web Backend

A small FastAPI service backed by SQLite for storing parsed output files
(the JSON produced by the alvie-cli parser and consumed by alvie-web).

## Endpoints

| Method | Path                | Description                                   |
| ------ | ------------------- | ---------------------------------------------- |
| GET    | `/api/outputs`       | List stored parsed outputs (summary fields only) |
| GET    | `/api/outputs/{id}`  | Fetch one stored parsed output, including its full JSON payload |
| POST   | `/api/outputs`       | Store a parsed output. Body: `{"filename": "...", "data": <ParsedOutput JSON>}` |
| DELETE | `/api/outputs/{id}`  | Delete one stored parsed output |
| DELETE | `/api/outputs`       | Delete all stored parsed outputs |

## Local development

```bash
cd alvie-web/backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The database defaults to a local `alvie.db` file (path set via the
`DATABASE_URL` env var, e.g. `sqlite:///./alvie.db`). In docker-compose, it's
pointed at `sqlite:////data/alvie.db` on a named volume so data persists
across container restarts.

Interactive API docs are available at `http://localhost:8000/docs` once the
server is running.
