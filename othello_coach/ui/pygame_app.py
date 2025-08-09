from __future__ import annotations
import pygame
import sys
import threading
from typing import Optional, List

from ..engine.bitboard import Position
from ..engine.search import Searcher, SearchConfig
from ..engine.policies import policy_for_elo
from ..engine.openings import name_for_prefix, sq_to_alg
from ..db.store import upsert_position, upsert_analysis

TILE = 72
MARGIN = 20
WIDTH = HEIGHT = TILE*8 + MARGIN*2

class App:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Othello Coach (MVP)")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT+80))
        self.font = pygame.font.SysFont("Arial", 18)
        self.big = pygame.font.SysFont("Arial", 24, bold=True)
        self.pos = Position.initial()
        self.history: List[int] = []
        self.engine = Searcher()
        self.elo = 1400
        self.depth = policy_for_elo(self.elo).max_depth
        self.mode = "HvsCPU"  # "HvsH", "CPUvsCPU"
        self.overlay_scores = {}
        self.thinking = False
        self.stop_flag = False

    def draw_board(self):
        self.screen.fill((20,120,20))
        # board
        for r in range(8):
            for c in range(8):
                rect = (MARGIN + c*TILE, MARGIN + r*TILE, TILE-2, TILE-2)
                pygame.draw.rect(self.screen, (10,90,10), rect)
        # grid
        for i in range(9):
            pygame.draw.line(self.screen, (0,0,0), (MARGIN, MARGIN+i*TILE), (MARGIN+8*TILE, MARGIN+i*TILE))
            pygame.draw.line(self.screen, (0,0,0), (MARGIN+i*TILE, MARGIN), (MARGIN+i*TILE, MARGIN+8*TILE))
        # discs
        for i in range(64):
            r,c = divmod(i,8)
            x = MARGIN + c*TILE + TILE//2
            y = MARGIN + r*TILE + TILE//2
            if (self.pos.black >> i) & 1:
                pygame.draw.circle(self.screen, (0,0,0), (x,y), TILE//2 - 6)
            if (self.pos.white >> i) & 1:
                pygame.draw.circle(self.screen, (230,230,230), (x,y), TILE//2 - 6)
        # legal moves overlay & scores
        lm = self.pos.legal_mask()
        for i in range(64):
            if (lm >> i) & 1:
                r,c = divmod(i,8)
                x = MARGIN + c*TILE + TILE//2
                y = MARGIN + r*TILE + TILE//2
                pygame.draw.circle(self.screen, (200,200,60), (x,y), 8)
                if i in self.overlay_scores:
                    txt = self.font.render(f"{self.overlay_scores[i]:+.1f}", True, (255,255,255))
                    self.screen.blit(txt, (x-16, y-30))
        # info bar
        bar = pygame.Rect(0, HEIGHT, WIDTH, 80)
        pygame.draw.rect(self.screen, (30,30,30), bar)
        txt1 = self.big.render(f"Mode: {self.mode}  ELO: {self.elo}  Depth: {self.depth}  To move: {'Black' if self.pos.stm==0 else 'White'}", True, (255,255,255))
        self.screen.blit(txt1, (MARGIN, HEIGHT+8))
        # opening name
        opening = name_for_prefix(self.history)
        if opening:
            on = self.font.render(f"Opening: {opening[0]} {opening[1]}", True, (200,200,200))
            self.screen.blit(on, (MARGIN, HEIGHT+40))

    def square_at(self, x,y) -> Optional[int]:
        if x < MARGIN or y < MARGIN or x >= MARGIN+8*TILE or y >= MARGIN+8*TILE:
            return None
        c = (x - MARGIN)//TILE
        r = (y - MARGIN)//TILE
        return r*8 + c

    def compute_overlay(self):
        self.overlay_scores = {}
        lm = self.pos.legal_mask()
        moves = [i for i in range(64) if (lm >> i) & 1]
        cfg = SearchConfig(max_depth=min(3, self.depth))
        for m in moves:
            child = self.pos.apply(m)
            a = self.engine.search(child, cfg)
            self.overlay_scores[m] = -a.score/100.0

    def engine_move(self):
        self.thinking = True
        cfg = policy_for_elo(self.elo)
        cfg.max_depth = self.depth
        a = self.engine.search(self.pos, cfg)
        # record analysis in DB (minimal)
        upsert_position(self.pos.hash64(), self.pos.black, self.pos.white, self.pos.stm)
        if a.best_move is not None:
            upsert_analysis(self.pos.hash64(), a.depth, a.score, 0, a.best_move, a.nodes, a.time_ms)
        self.thinking = False
        if a.best_move is None:
            self.pos = self.pos.pass_move()
        else:
            if a.best_move != 64:
                self.pos = self.pos.apply(a.best_move)
                self.history.append(a.best_move)
        self.compute_overlay()

    def mainloop(self):
        clock = pygame.time.Clock()
        self.compute_overlay()
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); sys.exit(0)
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_1:
                        self.mode = "HvsCPU"
                    elif event.key == pygame.K_2:
                        self.mode = "HvsH"
                    elif event.key == pygame.K_3:
                        self.mode = "CPUvsCPU"
                    elif event.key == pygame.K_UP:
                        self.elo = min(2500, self.elo+100); self.depth = policy_for_elo(self.elo).max_depth
                    elif event.key == pygame.K_DOWN:
                        self.elo = max(200, self.elo-100); self.depth = policy_for_elo(self.elo).max_depth
                    elif event.key == pygame.K_d:
                        self.depth = max(1, self.depth+1)
                    elif event.key == pygame.K_s:
                        self.depth = max(1, self.depth-1)
                    elif event.key == pygame.K_r:
                        self.pos = Position.initial(); self.history.clear(); self.engine.tt.clear(); self.compute_overlay()
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    sq = self.square_at(*event.pos)
                    if sq is not None:
                        if (self.pos.legal_mask() >> sq) & 1:
                            self.pos = self.pos.apply(sq)
                            self.history.append(sq)
                            self.compute_overlay()
            # engine turn
            if self.mode == "HvsCPU" and self.pos.stm == 1 and not self.thinking:
                threading.Thread(target=self.engine_move, daemon=True).start()
            elif self.mode == "CPUvsCPU" and not self.thinking:
                threading.Thread(target=self.engine_move, daemon=True).start()
            self.draw_board()
            pygame.display.flip()
            clock.tick(60)


