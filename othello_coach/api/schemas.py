"""API request/response schemas"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


class AnalysisRequest(BaseModel):
    """Request for position analysis"""
    hash: int = Field(..., description="Position hash")
    depth: int = Field(8, ge=1, le=20, description="Search depth")


class FeatureData(BaseModel):
    """Feature analysis data"""
    mobility: int
    potential_mobility: int
    frontier: int
    stability: int
    parity: int
    corners: int
    x_squares: int


class RationaleData(BaseModel):
    """Rationale explanation"""
    type: str
    template: str
    confidence: float
    features_delta: Dict[str, float]


class AnalysisResponse(BaseModel):
    """Position analysis response"""
    hash: int
    score: float
    depth: int
    pv: List[int]
    nodes: int
    time_ms: int
    features: FeatureData
    rationales: List[RationaleData]
    best_move_square: str
    engine_version: str


class TreeRequest(BaseModel):
    """Request for tree building"""
    gdl: str = Field(..., description="GDL program source")
    root_hash: int = Field(..., description="Root position hash")
    max_time_ms: int = Field(2000, ge=100, le=10000, description="Time limit")


class TreeNode(BaseModel):
    """Tree node data"""
    hash: int
    stm: int
    score: float
    attrs: Dict[str, Any]


class TreeEdge(BaseModel):
    """Tree edge data"""
    from_hash: int
    to_hash: int
    move: int
    score: float


class TreeResponse(BaseModel):
    """Tree building response"""
    root_hash: int
    nodes: Dict[int, TreeNode]
    edges: List[TreeEdge]
    gdl_program: str
    build_time_ms: int
    nodes_explored: int


class SearchRequest(BaseModel):
    """Notes search request"""
    q: str = Field(..., min_length=1, max_length=100, description="Search query")
    limit: int = Field(10, ge=1, le=50, description="Result limit")


class SearchResult(BaseModel):
    """Single search result"""
    hash: int
    text: str
    relevance: float


class SearchResponse(BaseModel):
    """Notes search response"""
    query: str
    results: List[SearchResult]
    total_matches: int


class GameMoveData(BaseModel):
    """Game move information"""
    move: int
    square: str
    time_ms: int
    score: Optional[float] = None
    depth: Optional[int] = None


class GameResponse(BaseModel):
    """Game data response"""
    id: int
    start_hash: int
    result: int  # -1=black wins, 0=draw, 1=white wins
    length: int
    moves: List[GameMoveData]
    tags: Optional[Dict[str, str]] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response"""
    ok: bool
    version: str
    uptime_seconds: float
    features_enabled: Dict[str, bool]


class ErrorResponse(BaseModel):
    """Error response"""
    error: str
    details: Optional[str] = None
    code: Optional[str] = None
