from __future__ import annotations

from sqlalchemy import BigInteger, Identity
from sqlalchemy.orm import DeclarativeBase, mapped_column


class Base(DeclarativeBase):
    pass


def pk():
    return mapped_column(BigInteger, Identity(always=False), primary_key=True)
