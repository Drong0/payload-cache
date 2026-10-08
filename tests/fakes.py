class CountingTransformer:
    """Records every call, so tests can assert how often the external service was hit."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    async def __call__(self, value: str) -> str:
        self.calls.append(value)
        return value.upper()
