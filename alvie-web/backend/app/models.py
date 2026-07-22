from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class ParsedOutputRecord(Base):
    """A stored parsed output file, as produced by the alvie-cli parser."""

    __tablename__ = "parsed_outputs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    executable: Mapped[str] = mapped_column(String, nullable=False)
    start: Mapped[str] = mapped_column(String, nullable=False)
    end: Mapped[str] = mapped_column(String, nullable=False)
    data: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
