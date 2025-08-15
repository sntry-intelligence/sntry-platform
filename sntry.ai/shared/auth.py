"""
Authentication and authorization utilities for the API Gateway.
Implements OAuth 2.0 with JWT token validation as per requirements 7.1 and 7.2.
"""

import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
import httpx
from pydantic import BaseModel

from shared.config import get_settings
from shared.utils.logging import get_logger

logger = get_logger("auth")
settings = get_settings()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
SECRET_KEY = settings.jwt_secret_key
JWT_SECRET_KEY = settings.jwt_secret_key  # Alias for compatibility
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# OAuth 2.0 settings
OAUTH_TOKEN_URL = settings.oauth_token_url
OAUTH_USERINFO_URL = settings.oauth_userinfo_url
OAUTH_CLIENT_ID = settings.oauth_client_id
OAUTH_CLIENT_SECRET = settings.oauth_client_secret

# Security scheme
security = HTTPBearer()


class TokenData(BaseModel):
    """Token data model"""
    user_id: Optional[str] = None
    username: Optional[str] = None
    scopes: list[str] = []
    exp: Optional[datetime] = None


class User(BaseModel):
    """User model for authentication"""
    id: str
    username: str
    email: str
    is_active: bool = True
    scopes: list[str] = []


class AuthenticationError(HTTPException):
    """Custom authentication error"""
    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class AuthorizationError(HTTPException):
    """Custom authorization error"""
    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> TokenData:
    """Verify and decode a JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        username: str = payload.get("username")
        scopes: list = payload.get("scopes", [])
        exp_timestamp: int = payload.get("exp")
        
        if user_id is None:
            raise AuthenticationError("Invalid token: missing user ID")
        
        exp = datetime.fromtimestamp(exp_timestamp) if exp_timestamp else None
        
        return TokenData(
            user_id=user_id,
            username=username,
            scopes=scopes,
            exp=exp
        )
    except JWTError as e:
        logger.warning(f"JWT verification failed: {str(e)}")
        raise AuthenticationError("Invalid token")


async def verify_oauth_token(token: str) -> Dict[str, Any]:
    """Verify OAuth 2.0 token with the authorization server"""
    try:
        async with httpx.AsyncClient() as client:
            # Verify token with OAuth provider
            response = await client.get(
                OAUTH_USERINFO_URL,
                headers={"Authorization": f"Bearer {token}"},
                timeout=10.0
            )
            
            if response.status_code != 200:
                logger.warning(f"OAuth token verification failed: {response.status_code}")
                raise AuthenticationError("Invalid OAuth token")
            
            user_info = response.json()
            return user_info
            
    except httpx.RequestError as e:
        logger.error(f"OAuth verification request failed: {str(e)}")
        raise AuthenticationError("OAuth verification failed")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    request: Request = None
) -> User:
    """Get the current authenticated user"""
    token = credentials.credentials
    request_id = getattr(request.state, 'request_id', 'unknown') if request else 'unknown'
    
    logger.info(f"Authenticating user", request_id=request_id)
    
    try:
        # First try to verify as JWT token
        token_data = verify_token(token)
        
        # Create user object from token data
        user = User(
            id=token_data.user_id,
            username=token_data.username or "unknown",
            email="",  # Would be populated from database in real implementation
            scopes=token_data.scopes
        )
        
        logger.info(f"User authenticated successfully", 
                   user_id=user.id, username=user.username, request_id=request_id)
        return user
        
    except AuthenticationError:
        # If JWT fails, try OAuth 2.0 verification
        try:
            user_info = await verify_oauth_token(token)
            
            user = User(
                id=user_info.get("sub", user_info.get("id", "unknown")),
                username=user_info.get("preferred_username", user_info.get("name", "unknown")),
                email=user_info.get("email", ""),
                scopes=user_info.get("scopes", [])
            )
            
            logger.info(f"OAuth user authenticated successfully", 
                       user_id=user.id, username=user.username, request_id=request_id)
            return user
            
        except AuthenticationError:
            logger.warning(f"Authentication failed for token", request_id=request_id)
            raise


def require_scopes(*required_scopes: str):
    """Decorator to require specific scopes for an endpoint"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Extract user from kwargs (injected by dependency)
            user = None
            for arg in args:
                if isinstance(arg, User):
                    user = arg
                    break
            
            if not user:
                for value in kwargs.values():
                    if isinstance(value, User):
                        user = value
                        break
            
            if not user:
                raise AuthenticationError("User not found in request context")
            
            # Check if user has required scopes
            user_scopes = set(user.scopes)
            required_scopes_set = set(required_scopes)
            
            if not required_scopes_set.issubset(user_scopes):
                missing_scopes = required_scopes_set - user_scopes
                logger.warning(f"Authorization failed: missing scopes {missing_scopes}", 
                             user_id=user.id)
                raise AuthorizationError(f"Missing required scopes: {', '.join(missing_scopes)}")
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


class AuthMiddleware:
    """Authentication middleware for protecting routes"""
    
    def __init__(self, protected_paths: list[str] = None):
        self.protected_paths = protected_paths or ["/v1/"]
    
    def is_protected_path(self, path: str) -> bool:
        """Check if a path requires authentication"""
        # Skip authentication for health checks and docs
        if path in ["/", "/health", "/docs", "/redoc", "/openapi.json"]:
            return False
        
        # Check if path matches protected patterns
        for protected_path in self.protected_paths:
            if path.startswith(protected_path):
                return True
        
        return False


# Dependency for optional authentication
async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    request: Request = None
) -> Optional[User]:
    """Get current user if authenticated, None otherwise"""
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials, request)
    except (AuthenticationError, AuthorizationError):
        return None


# Common scopes
class Scopes:
    """Common authorization scopes"""
    AGENT_READ = "agent:read"
    AGENT_WRITE = "agent:write"
    AGENT_DELETE = "agent:delete"
    WORKFLOW_READ = "workflow:read"
    WORKFLOW_WRITE = "workflow:write"
    WORKFLOW_EXECUTE = "workflow:execute"
    TOOL_READ = "tool:read"
    TOOL_WRITE = "tool:write"
    VECTOR_READ = "vector:read"
    VECTOR_WRITE = "vector:write"
    EVALUATION_READ = "evaluation:read"
    EVALUATION_WRITE = "evaluation:write"
    ADMIN = "admin"