from __future__ import annotations

import sqlite3


def cap_moves_per_position(conn: sqlite3.Connection, cap: int) -> None:
    """Ensure at most `cap` moves per from_hash, deleting the lowest-visit rows.

    Uses a window function to rank by visits descending within each from_hash,
    then deletes rows where row_number exceeds the cap.
    """
    # SQLite 3.25+ supports window functions
    conn.execute(
        """
        DELETE FROM moves
        WHERE rowid IN (
            SELECT rowid FROM (
                SELECT rowid,
                       ROW_NUMBER() OVER (PARTITION BY from_hash ORDER BY visits DESC) AS rn
                FROM moves
            )
            WHERE rn > ?
        )
        """,
        (cap,),
    )
