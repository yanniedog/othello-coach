"""GDL Parser implementation"""

import re
from typing import Dict, Any, Optional, List, Tuple
from .ast_nodes import *


class GDLParseError(Exception):
    """GDL parsing error"""
    def __init__(self, message: str, line: int = 0, column: int = 0):
        super().__init__(message)
        self.line = line
        self.column = column


class GDLLexer:
    """Tokenizer for GDL"""
    
    TOKEN_PATTERNS = [
        ('SCORE', r'\bscore\b'),
        ('MIN_OPP_MOB', r'\bmin_opp_mob\b'),
        ('EARLIEST_CORNER', r'\bearliest_corner\b'),
        ('MAX_STABILITY', r'\bmax_stability\b'),
        ('CUSTOM', r'\bcustom\b'),
        ('MAX_DEPTH', r'\bmax_depth\b'),
        ('WIDTH', r'\bwidth\b'),
        ('PREFER', r'\bprefer\b'),
        ('WEIGHT', r'\bweight\b'),
        ('MAX_PLIES', r'\bmax_plies\b'),
        ('WEIGHTS', r'\bweights\b'),
        ('SIDE', r'\bside\b'),
        ('WHITE', r'\bwhite\b'),
        ('BLACK', r'\bblack\b'),
        ('STM', r'\bstm\b'),
        ('CORNERS', r'\bcorners\b'),
        ('STABILITY', r'\bstability\b'),
        ('MOBILITY', r'\bmobility\b'),
        ('PARITY', r'\bparity\b'),
        ('FRONTIER', r'\bfrontier\b'),
        ('IDENTIFIER', r'[a-zA-Z_][a-zA-Z0-9_]*'),
        ('NUMBER', r'\d+(?:\.\d+)?'),
        ('EQUALS', r'='),
        ('LPAREN', r'\('),
        ('RPAREN', r'\)'),
        ('LBRACE', r'\{'),
        ('RBRACE', r'\}'),
        ('COMMA', r','),
        ('COLON', r':'),
        ('WHITESPACE', r'\s+'),
        ('COMMENT', r'#.*'),
    ]
    
    def __init__(self, text: str):
        self.text = text
        self.tokens = []
        self.pos = 0
        self.line = 1
        self.column = 1
        self._tokenize()
    
    def _tokenize(self):
        """Tokenize the input text"""
        while self.pos < len(self.text):
            matched = False
            for token_type, pattern in self.TOKEN_PATTERNS:
                regex = re.compile(pattern)
                match = regex.match(self.text, self.pos)
                if match:
                    value = match.group(0)
                    if token_type not in ('WHITESPACE', 'COMMENT'):
                        self.tokens.append((token_type, value, self.line, self.column))
                    
                    # Update position
                    self.pos = match.end()
                    if '\n' in value:
                        self.line += value.count('\n')
                        self.column = len(value.split('\n')[-1]) + 1
                    else:
                        self.column += len(value)
                    matched = True
                    break
            
            if not matched:
                raise GDLParseError(
                    f"Unexpected character: {self.text[self.pos]}", 
                    self.line, self.column
                )


class GDLParser:
    """Parser for Goal Definition Language"""
    
    def __init__(self):
        self.tokens = []
        self.pos = 0
        
    def parse(self, text: str) -> GDLProgram:
        """Parse GDL text into AST"""
        lexer = GDLLexer(text)
        self.tokens = lexer.tokens
        self.pos = 0
        
        if not self.tokens:
            raise GDLParseError("Empty program")
        
        goal = self._parse_goal()
        params = self._parse_params() if self._peek() else None
        
        if self._peek():
            raise GDLParseError(f"Unexpected token: {self._peek()[1]}")
        
        return GDLProgram(
            gdl_v=1,
            goal=goal,
            params=params,
            source=text.strip()
        )
    
    def _peek(self) -> Optional[Tuple[str, str, int, int]]:
        """Peek at current token"""
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None
    
    def _consume(self, expected_type: Optional[str] = None) -> Tuple[str, str, int, int]:
        """Consume current token"""
        if self.pos >= len(self.tokens):
            raise GDLParseError("Unexpected end of input")
        
        token = self.tokens[self.pos]
        self.pos += 1
        
        if expected_type and token[0] != expected_type:
            raise GDLParseError(
                f"Expected {expected_type}, got {token[0]}", 
                token[2], token[3]
            )
        
        return token
    
    def _parse_goal(self) -> GDLGoal:
        """Parse goal definition"""
        token = self._peek()
        if not token:
            raise GDLParseError("Expected goal definition")
        
        if token[0] == 'SCORE':
            return self._parse_score_goal()
        elif token[0] == 'MIN_OPP_MOB':
            self._consume('MIN_OPP_MOB')
            return MinOppMobGoal()
        elif token[0] == 'EARLIEST_CORNER':
            return self._parse_earliest_corner_goal()
        elif token[0] == 'MAX_STABILITY':
            self._consume('MAX_STABILITY')
            return MaxStabilityGoal()
        elif token[0] == 'CUSTOM':
            return self._parse_custom_goal()
        else:
            raise GDLParseError(f"Unknown goal type: {token[1]}", token[2], token[3])
    
    def _parse_score_goal(self) -> ScoreGoal:
        """Parse score goal"""
        self._consume('SCORE')
        self._consume('LPAREN')
        self._consume('SIDE')
        self._consume('EQUALS')
        
        side_token = self._consume()
        if side_token[0] not in ('WHITE', 'BLACK', 'STM'):
            raise GDLParseError(
                f"Invalid side: {side_token[1]}", 
                side_token[2], side_token[3]
            )
        
        self._consume('RPAREN')
        return ScoreGoal(side=side_token[1].lower())
    
    def _parse_earliest_corner_goal(self) -> EarliestCornerGoal:
        """Parse earliest corner goal"""
        self._consume('EARLIEST_CORNER')
        self._consume('LPAREN')
        self._consume('MAX_PLIES')
        self._consume('EQUALS')
        
        plies_token = self._consume('NUMBER')
        max_plies = int(plies_token[1])
        if max_plies < 1:
            raise GDLParseError(
                "max_plies must be >= 1", 
                plies_token[2], plies_token[3]
            )
        
        self._consume('RPAREN')
        return EarliestCornerGoal(max_plies=max_plies)
    
    def _parse_custom_goal(self) -> CustomGoal:
        """Parse custom weighted goal"""
        self._consume('CUSTOM')
        self._consume('LPAREN')
        self._consume('WEIGHTS')
        self._consume('EQUALS')
        self._consume('LBRACE')
        
        weights = {}
        while True:
            token = self._peek()
            if not token or token[0] == 'RBRACE':
                break
            
            # Parse feature:weight pair
            feature_token = self._consume()
            if feature_token[0] not in ('MOBILITY', 'PARITY', 'STABILITY', 'FRONTIER', 'CORNERS'):
                raise GDLParseError(
                    f"Unknown feature: {feature_token[1]}", 
                    feature_token[2], feature_token[3]
                )
            
            self._consume('COLON')
            weight_token = self._consume('NUMBER')
            weights[feature_token[1].lower()] = float(weight_token[1])
            
            # Optional comma
            if self._peek() and self._peek()[0] == 'COMMA':
                self._consume('COMMA')
        
        self._consume('RBRACE')
        self._consume('RPAREN')
        
        if not weights:
            raise GDLParseError("Custom goal must have at least one weight")
        
        return CustomGoal(weights=weights)
    
    def _parse_params(self) -> Optional[GDLParams]:
        """Parse optional parameters"""
        params = GDLParams()
        
        while self._peek():
            token = self._peek()
            
            if token[0] == 'MAX_DEPTH':
                self._consume('MAX_DEPTH')
                self._consume('EQUALS')
                depth_token = self._consume('NUMBER')
                params.max_depth = int(depth_token[1])
                if params.max_depth < 1:
                    raise GDLParseError(
                        "max_depth must be >= 1", 
                        depth_token[2], depth_token[3]
                    )
            
            elif token[0] == 'WIDTH':
                self._consume('WIDTH')
                self._consume('EQUALS')
                width_token = self._consume('NUMBER')
                params.width = int(width_token[1])
                if params.width < 1:
                    raise GDLParseError(
                        "width must be >= 1", 
                        width_token[2], width_token[3]
                    )
            
            elif token[0] == 'PREFER':
                self._consume('PREFER')
                self._consume('EQUALS')
                prefer_token = self._consume()
                if prefer_token[0] not in ('CORNERS', 'STABILITY', 'MOBILITY'):
                    raise GDLParseError(
                        f"Invalid prefer value: {prefer_token[1]}", 
                        prefer_token[2], prefer_token[3]
                    )
                params.prefer = prefer_token[1].lower()
            
            elif token[0] == 'WEIGHT':
                if not params.weights:
                    params.weights = {}
                self._consume('WEIGHT')
                self._consume('LPAREN')
                
                name_token = self._consume('IDENTIFIER')
                self._consume('EQUALS')
                value_token = self._consume('NUMBER')
                
                params.weights[name_token[1]] = float(value_token[1])
                self._consume('RPAREN')
            
            else:
                break
        
        return params
