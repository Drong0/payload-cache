import asyncio
from collections.abc import Awaitable, Callable

type Transformer = Callable[[str], Awaitable[str]]


class SimulatedTransformer:
    """Stand-in for the external transformer service.

    The delay makes it obvious from the outside whether a request hit the cache.
    """

    def __init__(self, delay_seconds: float) -> None:
        self._delay_seconds = delay_seconds

    async def __call__(self, text: str) -> str:
        await asyncio.sleep(self._delay_seconds)
        return text.upper()
