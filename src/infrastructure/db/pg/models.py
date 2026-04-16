from typing import List, Optional
from datetime import date
from pgvector.sqlalchemy import Vector
from sqlalchemy import MetaData, event, DDL
from sqlalchemy import String, ARRAY, Text, BigInteger, Date, ForeignKey, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship, DeclarativeBase

from src.core.config import get_settings

settings = get_settings()
embedder_dimension = settings.MODELS["embedder"]["dimension"]

class Base(DeclarativeBase):
    metadata = MetaData(schema="edgar")

event.listen(
    Base.metadata,
    "before_create",
    DDL("CREATE SCHEMA IF NOT EXISTS edgar;")
)

event.listen(
    Base.metadata,
    "before_create",
    DDL("CREATE EXTENSION IF NOT EXISTS vector;")
)


class Companies(Base):
    __tablename__ = "companies"

    cusip6: Mapped[str] = mapped_column(String(6), primary_key=True)
    cik: Mapped[int] = mapped_column(BigInteger, ForeignKey("form10.cik"), index=True)
    cusip: Mapped[List[str]] = mapped_column(ARRAY(String(9)))
    names: Mapped[List[str]] = mapped_column(ARRAY(String(255)))
    name: Mapped[str] = mapped_column(String(255))

    holdings: Mapped[List["Holdings"]] = relationship("Holdings", back_populates="company")

    def __repr__(self) -> str:
        return f"<Company(cusip6={self.cusip6}, cik={self.cik}, name={self.name})>"


class Form10(Base):
    __tablename__ = "form10"

    form_id: Mapped[str] = mapped_column(primary_key=True)
    cik: Mapped[int] = mapped_column(BigInteger)
    cusip6: Mapped[str] = mapped_column()
    cusip: Mapped[List[str]] = mapped_column(ARRAY(String(9)))
    names: Mapped[List[str]] = mapped_column(ARRAY(String(255)))
    source: Mapped[Optional[str]] = mapped_column(Text)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<Form10(form_id={self.form_id}, cusip6={self.cusip6})>"


class Form10Embeddings(Base):
    __tablename__ = "form10_embeddings"

    form_id: Mapped[str] = mapped_column(ForeignKey("form10.form_id"), primary_key=True)
    embeddings: Mapped[List[float]] = mapped_column(Vector(embedder_dimension), nullable=True)


class Chunks(Base):
    __tablename__ = "chunks"

    chunk_id: Mapped[str] = mapped_column(primary_key=True)
    form_id: Mapped[str] = mapped_column(ForeignKey("form10.form_id"))
    cusip6: Mapped[str] = mapped_column()
    cik: Mapped[int] = mapped_column(BigInteger)
    item: Mapped[str] = mapped_column()
    text: Mapped[str] = mapped_column()
    names: Mapped[List[str]] = mapped_column(ARRAY(String(255)))
    source: Mapped[Optional[str]] = mapped_column(Text)

    def __repr__(self) -> str:
        return f"<Chunk(chunk_id={self.chunk_id}, form_id={self.form_id})>"

class ItemsEmbeddings(Base):
    __tablename__ = "item_embeddings"
    
    item_id: Mapped[str] = mapped_column(primary_key=True)
    embeddings: Mapped[List[float]] = mapped_column(Vector(embedder_dimension), nullable=True)

class ChunkEmbeddings(Base):
    __tablename__ = "chunk_embeddings"

    chunk_id: Mapped[str] = mapped_column(ForeignKey("chunks.chunk_id"), primary_key=True)
    item_id: Mapped[str] = mapped_column(nullable=True, index=True)
    embeddings: Mapped[List[float]] = mapped_column(Vector(embedder_dimension), nullable=True)


class Managers(Base):
    __tablename__ = "managers"

    manager_cik: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column()
    address: Mapped[Optional[str]] = mapped_column(Text)

    holdings: Mapped[List["Holdings"]] = relationship("Holdings", back_populates="manager")

    def __repr__(self) -> str:
        return f"<Manager(cik={self.manager_cik}, name={self.name[:20]}...)>"


class Holdings(Base):
    __tablename__ = "holdings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    manager_cik: Mapped[int] = mapped_column(ForeignKey("managers.manager_cik"), nullable=False)
    report_date: Mapped[date] = mapped_column(Date, index=True)
    cusip6: Mapped[str] = mapped_column(ForeignKey("companies.cusip6"), index=True)
    cusip: Mapped[str] = mapped_column(String(9), index=True)
    company_name: Mapped[str] = mapped_column(String(255))
    value: Mapped[float] = mapped_column(Float)
    shares: Mapped[int] = mapped_column(BigInteger)
    source: Mapped[Optional[str]] = mapped_column(Text)

    manager: Mapped["Managers"] = relationship("Managers", back_populates="holdings")
    company: Mapped["Companies"] = relationship("Companies", back_populates="holdings")

    def __repr__(self) -> str:
        return f"<Holding(ticker={self.company_name[:15]}, value={self.value})>"
