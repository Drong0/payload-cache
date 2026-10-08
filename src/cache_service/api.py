from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from cache_service.schemas import PayloadCreate, PayloadCreated, PayloadRead
from cache_service.service import PayloadService

router = APIRouter()


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.session_factory() as session:
        yield session


def get_payload_service(
    request: Request, session: Annotated[AsyncSession, Depends(get_session)]
) -> PayloadService:
    return PayloadService(session, request.app.state.transformer)


PayloadServiceDep = Annotated[PayloadService, Depends(get_payload_service)]


@router.post(
    "/payload",
    status_code=status.HTTP_201_CREATED,
    responses={status.HTTP_200_OK: {"model": PayloadCreated, "description": "Already generated"}},
)
async def create_payload(
    body: PayloadCreate, response: Response, service: PayloadServiceDep
) -> PayloadCreated:
    result = await service.create(body.list_1, body.list_2)
    if result.created:
        return PayloadCreated(id=result.payload_id, message="Payload created")
    response.status_code = status.HTTP_200_OK
    return PayloadCreated(id=result.payload_id, message="Payload already exists")


@router.get("/payload/{payload_id}", responses={status.HTTP_404_NOT_FOUND: {}})
async def read_payload(payload_id: UUID, service: PayloadServiceDep) -> PayloadRead:
    output = await service.get_output(payload_id)
    if output is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Payload not found")
    return PayloadRead(output=output)


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
