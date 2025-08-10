from __future__ import annotations

from .movegen_fast import legal_moves_mask, flip_mask


# Export with expected name for tests
generate_legal_mask = legal_moves_mask
generate_flip_mask = flip_mask