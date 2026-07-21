# Aegis

Capa de gobernanza y permisos para agentes de IA.

Aegis se sienta delante de las acciones de otros agentes (CrewAI, LangGraph, Hermès) y decide, antes de ejecutar, si permitir la acción, exigir aprobación humana, o denegarla — dejando un registro auditable.

## Stack

- **Backend**: FastAPI + Python
- **Cola**: Redis Streams
- **Persistencia**: PostgreSQL (SQLite en desarrollo simple)
- **Dashboard**: React + TypeScript
- **Empaquetado**: Docker + docker-compose
- **SDK**: Decorador/wrapper Python para CrewAI

## Fases del MVP

1. **Fase 0 — Scaffolding e identidad**: estructura del repo, docker-compose, modelos de datos, registro de agentes con credenciales y scopes.
2. **Fase 1 — Gateway + auditoría**: endpoint `POST /actions`, audit log inmutable.
3. **Fase 2 — Motor de políticas**: reglas de riesgo `allow/review/deny`.
4. **Fase 3 — Cola de aprobación + dashboard**: Redis Streams, UI de aprobación.
5. **Fase 4 — SDK CrewAI**: decorador probado sobre `multi-agentes`.
6. **Fase 5 — Risk score + docs**: scoring OWASP-like, vista de auditoría, diagramas.

## Ejecutar localmente

```bash
docker compose up --build
```

O para desarrollo ligero del backend:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Variables de entorno

Ver `.env.example`.
