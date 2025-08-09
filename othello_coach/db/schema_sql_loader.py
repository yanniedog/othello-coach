from __future__ import annotations

from importlib import resources


def get_schema_sql() -> str:
    from . import schema
    with resources.files("othello_coach.db").joinpath("schema.sql").open("r", encoding="utf-8") as f:
        return f.read()
