from __future__ import annotations

from importlib import resources


def get_schema_sql() -> str:
    # Load the embedded SQL schema file from package data
    with resources.files("othello_coach.db").joinpath("schema.sql").open("r", encoding="utf-8") as f:
        return f.read()
