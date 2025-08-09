"""API authentication and rate limiting"""

import time
import secrets
from typing import Dict, Optional
from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from collections import defaultdict, deque


class TokenAuth:
    """Simple token-based authentication"""
    
    def __init__(self, token: str):
        self.token = token if token else self._generate_token()
    
    def _generate_token(self) -> str:
        """Generate a secure random token"""
        return secrets.token_urlsafe(32)
    
    def verify_token(self, credentials: HTTPAuthorizationCredentials) -> bool:
        """Verify the provided token"""
        return credentials.credentials == self.token


class RateLimiter:
    """Simple in-memory rate limiter"""
    
    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.clients: Dict[str, deque] = defaultdict(deque)
    
    def is_allowed(self, client_ip: str) -> bool:
        """Check if client is within rate limits"""
        now = time.time()
        client_requests = self.clients[client_ip]
        
        # Remove old requests outside the window
        while client_requests and client_requests[0] < now - self.window_seconds:
            client_requests.popleft()
        
        # Check if under limit
        if len(client_requests) >= self.max_requests:
            return False
        
        # Add current request
        client_requests.append(now)
        return True


def create_auth_dependency(token_auth: TokenAuth):
    """Create authentication dependency"""
    security = HTTPBearer()
    
    async def verify_auth(credentials: HTTPAuthorizationCredentials = Depends(security)):
        if not token_auth.verify_token(credentials):
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return credentials
    
    return verify_auth


def create_rate_limit_dependency(rate_limiter: RateLimiter):
    """Create rate limiting dependency"""
    
    async def check_rate_limit(request: Request):
        client_ip = request.client.host
        
        # Always allow localhost
        if client_ip in ('127.0.0.1', '::1', 'localhost'):
            return
        
        if not rate_limiter.is_allowed(client_ip):
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded",
                headers={"Retry-After": str(rate_limiter.window_seconds)},
            )
    
    return check_rate_limit


class SecurityHeaders:
    """Add security headers to responses"""
    
    @staticmethod
    def add_headers(response):
        """Add security headers"""
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Content-Security-Policy"] = "default-src 'none'"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response
