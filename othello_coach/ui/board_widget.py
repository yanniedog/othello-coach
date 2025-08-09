from __future__ import annotations

from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene
from PyQt6.QtGui import QBrush, QColor, QPen
from PyQt6.QtCore import QRectF, Qt, QPointF

from ..engine.board import start_board, legal_moves_mask, make_move, compute_hash, Board
from ..insights.overlays import mobility_heat as ov_mobility_heat
from ..insights.overlays import stability_heat as ov_stability_heat
from ..insights.overlays import parity_map as ov_parity_map
from ..insights.overlays import corner_tension as ov_corner_tension
from ..tools.diag import log_event


class BoardWidget(QGraphicsView):
    def __init__(self) -> None:
        super().__init__()
        self.setScene(QGraphicsScene(self))
        self.setMinimumSize(300, 300)
        self.board = start_board()
        self.game_over = False
        self.overlay_flags = {"mobility": False, "parity": False, "stability": False, "corner": False}
        self._ensure_playable_state()
        self._draw()

    def _draw(self) -> None:
        s = self.scene()
        assert s is not None
        s.clear()
        size = 8
        square = 40.0
        board_px = square * size
        s.setSceneRect(QRectF(0, 0, board_px, board_px))
        dark_green = QColor(20, 110, 50)
        light_green = QColor(30, 140, 70)
        # Draw squares
        for r in range(size):
            for c in range(size):
                rect = QRectF(c * square, r * square, square, square)
                color = dark_green if (r + c) % 2 == 0 else light_green
                s.addRect(rect, QPen(Qt.PenStyle.NoPen), QBrush(color))
        # Draw discs
        B = self.board.B
        W = self.board.W
        for i in range(64):
            bit = 1 << i
            if not (B & bit or W & bit):
                continue
            r, c = divmod(i, 8)
            rect = QRectF(c * square + 4, r * square + 4, square - 8, square - 8)
            color = QColor("black") if (B & bit) else QColor("white")
            s.addEllipse(rect, QPen(Qt.GlobalColor.black), QBrush(color))
        # Legal move pips for current player
        legal = legal_moves_mask(self.board)
        pen = QPen(QColor(255, 255, 0))
        pen.setWidth(2)
        for i in range(64):
            if legal & (1 << i):
                r, c = divmod(i, 8)
                rect = QRectF(c * square + square / 2 - 4, r * square + square / 2 - 4, 8, 8)
                s.addEllipse(rect, pen)

        # Overlays
        try:
            if self.overlay_flags.get("mobility"):
                t0 = Qt.QElapsedTimer()
                t0.start()
                heat = ov_mobility_heat(self.board)
                for sq, val in heat.items():
                    r, c = divmod(sq, 8)
                    alpha = max(30, min(255, 30 + val * 20))
                    color = QColor(0, 200, 255, alpha)
                    rect = QRectF(c * square + 10, r * square + 10, square - 20, square - 20)
                    s.addEllipse(rect, QPen(Qt.PenStyle.NoPen), QBrush(color))
                log_event("ui.board", "overlay_mobility", ms=int(t0.elapsed()))
            if self.overlay_flags.get("stability"):
                t0 = Qt.QElapsedTimer(); t0.start()
                heat = ov_stability_heat(self.board)
                for sq, val in heat.items():
                    r, c = divmod(sq, 8)
                    alpha = max(30, min(255, 30 + val * 10))
                    color = QColor(255, 140, 0, alpha)
                    rect = QRectF(c * square + 12, r * square + 12, square - 24, square - 24)
                    s.addEllipse(rect, QPen(Qt.PenStyle.NoPen), QBrush(color))
                log_event("ui.board", "overlay_stability", ms=int(t0.elapsed()))
            if self.overlay_flags.get("parity"):
                t0 = Qt.QElapsedTimer(); t0.start()
                pm = ov_parity_map(self.board)
                for sq in pm.get("odd", []):
                    r, c = divmod(sq, 8)
                    rect = QRectF(c * square + 2, r * square + 2, square - 4, square - 4)
                    s.addRect(rect, QPen(QColor(200, 0, 200)))
                for sq in pm.get("must_move_border", []):
                    r, c = divmod(sq, 8)
                    rect = QRectF(c * square + 6, r * square + 6, square - 12, square - 12)
                    s.addRect(rect, QPen(QColor(255, 0, 0)))
                log_event("ui.board", "overlay_parity", ms=int(t0.elapsed()))
            if self.overlay_flags.get("corner"):
                t0 = Qt.QElapsedTimer(); t0.start()
                arrows = ov_corner_tension(self.board)
                for frm, corner, kind in arrows:
                    r1, c1 = divmod(frm, 8)
                    r2, c2 = divmod(corner, 8)
                    pen = QPen(QColor(0, 180, 0) if kind == "secures" else QColor(180, 0, 0))
                    pen.setWidth(2)
                    s.addLine(c1 * square + square/2, r1 * square + square/2, c2 * square + square/2, r2 * square + square/2, pen)
                log_event("ui.board", "overlay_corner", ms=int(t0.elapsed()))
        except Exception:
            # overlays are best-effort; never break board drawing
            pass

    def _ensure_playable_state(self) -> None:
        """Pass turn automatically if current side has no legal moves.
        If both sides have no legal moves, mark game over.
        """
        # Try at most twice to avoid infinite loops
        for _ in range(2):
            if legal_moves_mask(self.board) != 0:
                return
            # No legal moves for current side → try passing
            next_stm = 1 - self.board.stm
            # Check if opponent has moves
            temp = Board(self.board.B, self.board.W, next_stm, self.board.ply, compute_hash(self.board.B, self.board.W, next_stm))
            if legal_moves_mask(temp) == 0:
                # Game over: neither side can move
                self.game_over = True
                return
            # Apply pass: toggle stm and increment ply, recompute hash
            self.board = Board(self.board.B, self.board.W, next_stm, self.board.ply + 1, compute_hash(self.board.B, self.board.W, next_stm))

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        # If current side has no moves, auto-pass first
        self._ensure_playable_state()
        if self.game_over:
            return
        if event.button() == Qt.MouseButton.LeftButton:
            pos: QPointF = self.mapToScene(event.position().toPoint())  # type: ignore[attr-defined]
            square = 40.0
            c = int(pos.x() // square)
            r = int(pos.y() // square)
            if 0 <= r < 8 and 0 <= c < 8:
                idx = r * 8 + c
                legal = legal_moves_mask(self.board)
                if legal & (1 << idx):
                    self.board, _ = make_move(self.board, idx)
                    # After a move, opponent might have to pass
                    self._ensure_playable_state()
                    self._draw()
                    return
        super().mousePressEvent(event)

    def apply_overlays(self, flags: dict) -> None:
        self.overlay_flags.update(flags)
        self._draw()
