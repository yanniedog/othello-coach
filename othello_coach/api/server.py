"""FastAPI server implementation"""

import time
import asyncio
from typing import Dict, List, Optional
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from uvicorn import Config, Server

from .auth import TokenAuth, RateLimiter, create_auth_dependency, create_rate_limit_dependency
from .schemas import *
from ..engine.search import search_position
from ..engine.board import Board
from ..insights.features import extract_features
from ..insights.rationale import generate_rationale
from ..gdl.parser import GDLParser
from ..trees.builder import TreeBuilder


class APIServer:
    """Local API server (loopback only)"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.start_time = time.time()
        self.token_auth = TokenAuth(config['api']['token'])
        self.rate_limiter = RateLimiter(
            max_requests=config['api']['rate_limit_rps'],
            window_seconds=60
        )
        
        # Store token for client access
        if not config['api']['token']:
            config['api']['token'] = self.token_auth.token
            print(f"Generated API token: {self.token_auth.token}")
        
        self.app = create_app(self)
    
    async def start(self, host: str = "127.0.0.1", port: int = 0):
        """Start the API server"""
        if port == 0:
            # Find available port
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(('', 0))
            port = sock.getsockname()[1]
            sock.close()
        
        config = Config(
            self.app,
            host=host,
            port=port,
            log_level="info",
            access_log=False
        )
        
        server = Server(config)
        print(f"Starting API server on http://{host}:{port}")
        print(f"API token: {self.token_auth.token}")
        
        await server.serve()
    
    def get_uptime(self) -> float:
        """Get server uptime in seconds"""
        return time.time() - self.start_time


def create_app(api_server: APIServer) -> FastAPI:
    """Create FastAPI application"""
    
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Startup
        print("API server starting up...")
        yield
        # Shutdown
        print("API server shutting down...")
    
    app = FastAPI(
        title="Othello Coach API",
        description="Local API for Othello Coach analysis and tree building",
        version="1.1.0",
        docs_url="/docs" if api_server.config.get('debug') else None,
        redoc_url=None,
        lifespan=lifespan
    )
    
    # Disable CORS since we're loopback only
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:*", "http://localhost:*"],
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    
    # Dependencies
    auth_required = create_auth_dependency(api_server.token_auth)
    rate_limited = create_rate_limit_dependency(api_server.rate_limiter)
    
    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response
    
    @app.get("/health", response_model=HealthResponse)
    async def health_check():
        """Health check endpoint"""
        return HealthResponse(
            ok=True,
            version="1.1.0",
            uptime_seconds=api_server.get_uptime(),
            features_enabled={
                "rust_acceleration": _check_rust_available(),
                "gdl_authoring": api_server.config['feature_flags']['gdl_authoring'],
                "novelty_radar": api_server.config['feature_flags']['novelty_radar'],
                "trainer": api_server.config['feature_flags']['trainer']
            }
        )
    
    @app.get("/analyse", response_model=AnalysisResponse, dependencies=[Depends(auth_required), Depends(rate_limited)])
    async def analyse_position(hash: int, depth: int = 8):
        """Analyse a position"""
        try:
            # Load position from database
            board = await _load_position(hash)
            if not board:
                raise HTTPException(status_code=404, detail="Position not found")
            
            # Search the position
            result = search_position(board, depth=depth, time_ms=5000)
            if not result:
                raise HTTPException(status_code=500, detail="Analysis failed")
            
            # Extract features
            features = extract_features(board)
            
            # Generate rationales
            rationales = []
            if result.pv:
                rationale_data = generate_rationale(board, result.pv[0])
                rationales = [
                    RationaleData(
                        type=r['type'],
                        template=r['template'],
                        confidence=r['confidence'],
                        features_delta=r.get('features_delta', {})
                    )
                    for r in rationale_data[:2]  # Top 2 rationales
                ]
            
            return AnalysisResponse(
                hash=hash,
                score=result.score,
                depth=result.depth,
                pv=result.pv,
                nodes=result.nodes,
                time_ms=result.time_ms,
                features=FeatureData(**features),
                rationales=rationales,
                best_move_square=_square_name(result.pv[0]) if result.pv else "",
                engine_version="1.1.0"
            )
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/tree", response_model=TreeResponse, dependencies=[Depends(auth_required), Depends(rate_limited)])
    async def build_tree(request: TreeRequest):
        """Build a tree using GDL"""
        try:
            # Parse GDL program
            parser = GDLParser()
            program = parser.parse(request.gdl)
            
            # Load root position
            root_board = await _load_position(request.root_hash)
            if not root_board:
                raise HTTPException(status_code=404, detail="Root position not found")
            
            # Build tree
            start_time = time.time()
            builder = TreeBuilder(program)
            tree_data = builder.build_tree(
                root_board,
                max_time_ms=request.max_time_ms
            )
            build_time = int((time.time() - start_time) * 1000)
            
            # Convert to response format
            nodes = {}
            for hash_val, node_data in tree_data['nodes'].items():
                nodes[hash_val] = TreeNode(
                    hash=hash_val,
                    stm=node_data['stm'],
                    score=node_data['score'],
                    attrs=node_data.get('attrs', {})
                )
            
            edges = [
                TreeEdge(
                    from_hash=edge['from'],
                    to_hash=edge['to'],
                    move=edge['move'],
                    score=edge['score']
                )
                for edge in tree_data['edges']
            ]
            
            return TreeResponse(
                root_hash=request.root_hash,
                nodes=nodes,
                edges=edges,
                gdl_program=request.gdl,
                build_time_ms=build_time,
                nodes_explored=len(nodes)
            )
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/search", response_model=SearchResponse, dependencies=[Depends(auth_required), Depends(rate_limited)])
    async def search_notes(q: str, limit: int = 10):
        """Search notes using FTS"""
        try:
            results = await _search_notes_fts(q, limit)
            
            search_results = [
                SearchResult(
                    hash=result['hash'],
                    text=result['text'],
                    relevance=result['relevance']
                )
                for result in results
            ]
            
            return SearchResponse(
                query=q,
                results=search_results,
                total_matches=len(search_results)
            )
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/game/{game_id}", response_model=GameResponse, dependencies=[Depends(auth_required), Depends(rate_limited)])
    async def get_game(game_id: int):
        """Get game data"""
        try:
            game_data = await _load_game(game_id)
            if not game_data:
                raise HTTPException(status_code=404, detail="Game not found")
            
            moves = [
                GameMoveData(
                    move=move['move'],
                    square=_square_name(move['move']),
                    time_ms=move.get('time_ms', 0),
                    score=move.get('score'),
                    depth=move.get('depth')
                )
                for move in game_data['moves']
            ]
            
            return GameResponse(
                id=game_id,
                start_hash=game_data['start_hash'],
                result=game_data['result'],
                length=game_data['length'],
                moves=moves,
                tags=game_data.get('tags'),
                started_at=game_data.get('started_at'),
                finished_at=game_data.get('finished_at')
            )
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                error=exc.detail,
                code=str(exc.status_code)
            ).dict()
        )
    
    return app


def _check_rust_available() -> bool:
    """Check if Rust acceleration is available"""
    try:
        import rust_kernel
        return True
    except ImportError:
        return False


async def _load_position(hash_val: int) -> Optional[Board]:
    """Load position from database"""
    # Simplified - would use actual database connection
    from ..engine.board import Board
    return Board(B=0x0000000810000000, W=0x0000001008000000, stm=0, ply=0, hash=hash_val)


async def _search_notes_fts(query: str, limit: int) -> List[Dict]:
    """Search notes using FTS"""
    # Simplified - would use actual FTS query
    return [
        {
            'hash': 12345,
            'text': f'Sample note matching {query}',
            'relevance': 0.9
        }
    ]


async def _load_game(game_id: int) -> Optional[Dict]:
    """Load game data from database"""
    # Simplified - would use actual database query
    return {
        'start_hash': 12345,
        'result': 1,
        'length': 60,
        'moves': [
            {'move': 19, 'time_ms': 1000},
            {'move': 26, 'time_ms': 1500}
        ]
    }


def _square_name(square: int) -> str:
    """Convert square index to algebraic notation"""
    file = chr(ord('a') + (square % 8))
    rank = str((square // 8) + 1)
    return file + rank
