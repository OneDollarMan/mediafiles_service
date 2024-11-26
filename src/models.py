import uuid
from sqlalchemy import UUID, Text, BigInteger
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped


class Base(DeclarativeBase):
    ...


class FileModel(Base):
    __tablename__ = 'file_model'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(Text)
    format: Mapped[str] = mapped_column(Text)
    extension: Mapped[str] = mapped_column(Text)
    size: Mapped[int] = mapped_column(BigInteger)
