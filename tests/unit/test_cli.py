import io
import json

import httpx
import pytest
from pydantic import ValidationError

from cache_cli.main import run
from cache_cli.settings import CliSettings

PAYLOAD = '{"list_1": ["a"], "list_2": ["b"]}'
PAYLOAD_ID = "6b1c0f8e-5d1e-4a3b-9c2d-1e2f3a4b5c6d"


def parse(*args: str) -> CliSettings:
    return CliSettings(_cli_parse_args=list(args))


def test_parses_short_flags() -> None:
    settings = parse("-H", "http://cache:9000", "-r", "3", "-j", PAYLOAD)

    assert str(settings.host) == "http://cache:9000/"
    assert settings.repeat == 3
    assert settings.load_payload().list_1 == ["a"]


@pytest.mark.parametrize(
    "args",
    [
        (),
        ("-i", "-", "-j", PAYLOAD),
        ("-r", "0", "-j", PAYLOAD),
        ("-j", '{"list_1": ["a"], "list_2": []}'),
        ("-i", "missing.json"),
    ],
)
def test_rejects_invalid_arguments(args: tuple[str, ...]) -> None:
    with pytest.raises(ValidationError):
        parse(*args)


def test_run_writes_one_line_per_iteration(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(201, json={"id": PAYLOAD_ID, "message": "Payload created"})
        return httpx.Response(200, json={"output": "A, B"})

    monkeypatch.setattr("sys.stdin", io.StringIO(PAYLOAD))
    client = httpx.Client(transport=httpx.MockTransport(handler), base_url="http://test")

    run(parse("-i", "-", "-r", "2"), client)

    lines = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert len(lines) == 2
    assert lines[0]["id"] == PAYLOAD_ID
    assert lines[0]["output"] == "A, B"
