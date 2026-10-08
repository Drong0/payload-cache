import httpx

from tests.fakes import CountingTransformer

SAMPLE = {
    "list_1": ["first string", "second string", "third string"],
    "list_2": ["other string", "another string", "last string"],
}
SAMPLE_OUTPUT = (
    "FIRST STRING, OTHER STRING, SECOND STRING, ANOTHER STRING, THIRD STRING, LAST STRING"
)


async def test_creates_and_reads_payload(client: httpx.AsyncClient) -> None:
    created = await client.post("/payload", json=SAMPLE)
    read = await client.get(f"/payload/{created.json()['id']}")

    assert created.status_code == 201
    assert read.json() == {"output": SAMPLE_OUTPUT}


async def test_same_input_reuses_id_without_transforming_again(
    client: httpx.AsyncClient, transformer: CountingTransformer
) -> None:
    first = await client.post("/payload", json=SAMPLE)
    second = await client.post("/payload", json=SAMPLE)

    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]
    assert len(transformer.calls) == 6


async def test_transforms_only_strings_not_seen_before(
    client: httpx.AsyncClient, transformer: CountingTransformer
) -> None:
    await client.post("/payload", json=SAMPLE)
    transformer.calls.clear()

    body = {"list_1": ["first string", "new", "new"], "list_2": ["new", "last string", "new"]}
    response = await client.post("/payload", json=body)

    assert response.status_code == 201
    assert transformer.calls == ["new"]


async def test_unknown_payload_returns_404(client: httpx.AsyncClient) -> None:
    response = await client.get("/payload/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404


async def test_lists_of_different_length_are_rejected(
    client: httpx.AsyncClient, transformer: CountingTransformer
) -> None:
    response = await client.post("/payload", json={"list_1": ["a", "b"], "list_2": ["c"]})

    assert response.status_code == 422
    assert transformer.calls == []
