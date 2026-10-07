import uuid

from sqlalchemy import String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Transformation(Base):
    """Cached result of one transformer call."""

    __tablename__ = "transformations"

    # Keyed by hash because indexing long strings is limited and slow.
    input_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    input_text: Mapped[str] = mapped_column(Text)
    output_text: Mapped[str] = mapped_column(Text)


class Payload(Base):
    __tablename__ = "payloads"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    input_hash: Mapped[str] = mapped_column(String(64), unique=True)
    output: Mapped[str] = mapped_column(Text)
