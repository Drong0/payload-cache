import json
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from typing import TextIO

import httpx
from pydantic import ValidationError

from cache_cli.settings import STDIO, CliSettings
from cache_service.schemas import PayloadCreate, PayloadCreated, PayloadRead


@contextmanager
def open_output(target: str) -> Iterator[TextIO]:
    if target == STDIO:
        yield sys.stdout
        return
    with open(target, "w") as file:
        yield file


def run_once(client: httpx.Client, payload: PayloadCreate) -> dict[str, object]:
    started = time.perf_counter()
    created_response = client.post("/payload", json=payload.model_dump())
    created_response.raise_for_status()
    created = PayloadCreated.model_validate_json(created_response.content)

    read_response = client.get(f"/payload/{created.id}")
    read_response.raise_for_status()
    read = PayloadRead.model_validate_json(read_response.content)

    return {
        "id": str(created.id),
        "created": created_response.status_code == httpx.codes.CREATED,
        "elapsed_ms": round((time.perf_counter() - started) * 1000),
        "output": read.output,
    }


def run(settings: CliSettings, client: httpx.Client) -> None:
    payload = settings.load_payload()
    with open_output(settings.output) as output:
        for _ in range(settings.repeat):
            output.write(json.dumps(run_once(client, payload)) + "\n")


def describe_validation_error(error: ValidationError) -> str:
    messages = (
        f"{'.'.join(map(str, detail['loc'])) or 'arguments'}: "
        f"{detail['msg'].removeprefix('Value error, ')}"
        for detail in error.errors()
    )
    return "; ".join(messages)


def main() -> None:
    try:
        settings = CliSettings(_cli_parse_args=True)
        with httpx.Client(base_url=str(settings.host)) as client:
            run(settings, client)
    except ValidationError as error:
        sys.exit(f"cache-cli: {describe_validation_error(error)}")
    except (OSError, httpx.HTTPError) as error:
        sys.exit(f"cache-cli: {error}")
