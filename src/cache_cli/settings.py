import sys
from pathlib import Path
from typing import Final, Self

from pydantic import Field, HttpUrl, field_validator, model_validator
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict

from cache_service.schemas import PayloadCreate

STDIO: Final = "-"


class CliSettings(BaseSettings):
    """Send a payload to the cache service and print the generated output."""

    model_config = SettingsConfigDict(
        cli_prog_name="cache-cli",
        cli_hide_none_type=True,
        case_sensitive=True,
        # -h stays reserved for --help, so the host gets -H.
        cli_shortcuts={"host": "H", "repeat": "r", "input": "i", "json": "j", "output": "o"},
    )

    host: HttpUrl = Field(default=HttpUrl("http://localhost:8000"), description="Service URL")
    repeat: int = Field(default=1, ge=1, description="Number of iterations")
    input: str | None = Field(
        default=None, description="JSON file with list_1 and list_2, '-' for stdin"
    )
    json_payload: str | None = Field(
        default=None, alias="json", description="Payload as a JSON string"
    )
    output: str = Field(default=STDIO, description="Output file, '-' for stdout")

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        # Only command line arguments count: a stray HOST or INPUT variable must not leak in.
        return (init_settings,)

    @field_validator("input")
    @classmethod
    def check_input_file(cls, value: str | None) -> str | None:
        if value is not None and value != STDIO and not Path(value).is_file():
            raise ValueError(f"file not found: {value}")
        return value

    @field_validator("json_payload")
    @classmethod
    def check_json_payload(cls, value: str | None) -> str | None:
        if value is not None:
            PayloadCreate.model_validate_json(value)
        return value

    @model_validator(mode="after")
    def check_single_source(self) -> Self:
        if (self.input is None) == (self.json_payload is None):
            raise ValueError("pass exactly one of --input or --json")
        return self

    def load_payload(self) -> PayloadCreate:
        if self.json_payload is not None:
            raw = self.json_payload
        elif self.input == STDIO:
            raw = sys.stdin.read()
        else:
            raw = Path(str(self.input)).read_text()
        return PayloadCreate.model_validate_json(raw)
