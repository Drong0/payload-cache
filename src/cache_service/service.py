import asyncio
import logging
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from cache_service.models import Payload, Transformation
from cache_service.payload import fingerprint, interleave, payload_fingerprint
from cache_service.transformer import Transformer

logger = logging.getLogger(__name__)


def _payload_id_by_hash(input_hash: str) -> Select[UUID]:
    return select(Payload.id).where(Payload.input_hash == input_hash)


@dataclass(frozen=True)
class CreateResult:
    payload_id: UUID
    created: bool


class PayloadService:
    def __init__(self, session: AsyncSession, transformer: Transformer) -> None:
        self._session = session
        self._transformer = transformer

    async def create(self, list_1: list[str], list_2: list[str]) -> CreateResult:
        input_hash = payload_fingerprint(list_1, list_2)
        existing_id = await self._session.scalar(_payload_id_by_hash(input_hash))
        if existing_id is not None:
            return CreateResult(existing_id, created=False)

        transformed = await self._transform({*list_1, *list_2})
        output = interleave([transformed[t] for t in list_1], [transformed[t] for t in list_2])

        payload_id = await self._session.scalar(
            insert(Payload)
            .values(input_hash=input_hash, output=output)
            .on_conflict_do_nothing(index_elements=[Payload.input_hash])
            .returning(Payload.id)
        )
        await self._session.commit()
        if payload_id is not None:
            return CreateResult(payload_id, created=True)

        # A concurrent request with the same input inserted it first: reuse its id.
        concurrent = await self._session.scalars(_payload_id_by_hash(input_hash))
        return CreateResult(concurrent.one(), created=False)

    async def get_output(self, payload_id: UUID) -> str | None:
        return await self._session.scalar(select(Payload.output).where(Payload.id == payload_id))

    async def _transform(self, texts: set[str]) -> dict[str, str]:
        """Transform each unique text, calling the transformer only for texts not cached yet."""
        text_by_hash = {fingerprint(text): text for text in texts}
        rows = await self._session.execute(
            select(Transformation.input_hash, Transformation.output_text).where(
                Transformation.input_hash.in_(text_by_hash)
            )
        )
        cached = {text_by_hash[input_hash]: output for input_hash, output in rows}

        missing = [text for text in texts if text not in cached]
        outputs = await asyncio.gather(*(self._transformer(text) for text in missing))
        fresh = dict(zip(missing, outputs, strict=True))
        logger.info("Transformer cache: %d hits, %d misses", len(cached), len(fresh))

        if fresh:
            await self._session.execute(
                insert(Transformation)
                .values(
                    [
                        {"input_hash": fingerprint(text), "input_text": text, "output_text": output}
                        for text, output in fresh.items()
                    ]
                )
                .on_conflict_do_nothing(index_elements=[Transformation.input_hash])
            )
        return cached | fresh
