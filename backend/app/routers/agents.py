from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.schemas import AgentCreate, AgentRead, AgentWithKeyRead, AgentUpdate
from app.services import agent_service

router = APIRouter(prefix="/agents", tags=["agents"])


@router.post("", response_model=AgentWithKeyRead, status_code=status.HTTP_201_CREATED)
async def create_agent(data: AgentCreate, db: AsyncSession = Depends(get_db)):
    """Register a new agent. The raw API key is returned only once."""
    try:
        agent, raw_key = await agent_service.create_agent(db, data)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Agent name already exists",
        )
    response_data = AgentRead.model_validate(agent).model_dump()
    response_data["api_key"] = raw_key
    return response_data


@router.get("/{agent_id}", response_model=AgentRead)
async def get_agent(agent_id: UUID, db: AsyncSession = Depends(get_db)):
    """Retrieve an agent by ID."""
    agent = await agent_service.get_agent(db, agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return agent


@router.patch("/{agent_id}", response_model=AgentRead)
async def update_agent(agent_id: UUID, data: AgentUpdate, db: AsyncSession = Depends(get_db)):
    """Update an existing agent."""
    agent = await agent_service.get_agent(db, agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    try:
        return await agent_service.update_agent(db, agent, data)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Agent name already exists",
        )
