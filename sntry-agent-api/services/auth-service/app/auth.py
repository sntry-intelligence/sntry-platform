"""
JWT authentication and authorization utilities
"""
from datetime import datetime, timedelta
from typing import Optional, List
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from .models import User, Role, Permission
import os
import redis
import json

# Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Bearer token scheme
security = HTTPBearer()

# Redis client for token blacklisting
redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    db=0,
    decode_responses=True
)


class AuthManager:
    """Handles authentication and authorization logic"""
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def get_password_hash(password: str) -> str:
        """Hash a password"""
        return pwd_context.hash(password)
    
    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT access token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire, "type": "access"})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def create_refresh_token(data: dict) -> str:
        """Create a JWT refresh token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({"exp": expire, "type": "refresh"})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def verify_token(token: str, token_type: str = "access") -> Optional[dict]:
        """Verify and decode a JWT token"""
        try:
            # Check if token is blacklisted
            if redis_client.get(f"blacklist:{token}"):
                return None
            
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            
            # Verify token type
            if payload.get("type") != token_type:
                return None
            
            return payload
        except JWTError:
            return None
    
    @staticmethod
    def blacklist_token(token: str, expires_in: int):
        """Add token to blacklist"""
        redis_client.setex(f"blacklist:{token}", expires_in, "true")
    
    @staticmethod
    def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
        """Authenticate a user with username and password"""
        user = db.query(User).filter(
            (User.username == username) | (User.email == username)
        ).first()
        
        if not user or not AuthManager.verify_password(password, user.hashed_password):
            return None
        
        if not user.is_active:
            return None
        
        return user
    
    @staticmethod
    def get_user_permissions(db: Session, user_id: int) -> List[str]:
        """Get all permissions for a user through their roles"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return []
        
        permissions = set()
        for role in user.roles:
            if role.is_active:
                for permission in role.permissions:
                    permissions.add(f"{permission.resource}:{permission.action}")
        
        return list(permissions)
    
    @staticmethod
    def check_permission(db: Session, user_id: int, resource: str, action: str) -> bool:
        """Check if user has specific permission"""
        permissions = AuthManager.get_user_permissions(db, user_id)
        required_permission = f"{resource}:{action}"
        
        # Check for exact permission or wildcard permissions
        return (
            required_permission in permissions or
            f"{resource}:*" in permissions or
            f"*:{action}" in permissions or
            "*:*" in permissions
        )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(lambda: None)  # Will be properly injected
) -> User:
    """Dependency to get current authenticated user"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        token = credentials.credentials
        payload = AuthManager.verify_token(token, "access")
        if payload is None:
            raise credentials_exception
        
        user_id: int = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    
    return user


def require_permission(resource: str, action: str):
    """Decorator factory for permission-based access control"""
    def permission_checker(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(lambda: None)  # Will be properly injected
    ):
        if not AuthManager.check_permission(db, current_user.id, resource, action):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions for {resource}:{action}"
            )
        return current_user
    
    return permission_checker


def require_role(role_name: str):
    """Decorator factory for role-based access control"""
    def role_checker(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(lambda: None)  # Will be properly injected
    ):
        user_roles = [role.name for role in current_user.roles if role.is_active]
        if role_name not in user_roles and "admin" not in user_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{role_name}' required"
            )
        return current_user
    
    return role_checker


class OAuth2Config:
    """OAuth 2.0 configuration and utilities"""
    
    # OAuth 2.0 provider configurations
    PROVIDERS = {
        "google": {
            "client_id": os.getenv("GOOGLE_CLIENT_ID"),
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
            "authorization_endpoint": "https://accounts.google.com/o/oauth2/v2/auth",
            "token_endpoint": "https://oauth2.googleapis.com/token",
            "userinfo_endpoint": "https://www.googleapis.com/oauth2/v2/userinfo",
            "scopes": ["openid", "email", "profile"]
        },
        "github": {
            "client_id": os.getenv("GITHUB_CLIENT_ID"),
            "client_secret": os.getenv("GITHUB_CLIENT_SECRET"),
            "authorization_endpoint": "https://github.com/login/oauth/authorize",
            "token_endpoint": "https://github.com/login/oauth/access_token",
            "userinfo_endpoint": "https://api.github.com/user",
            "scopes": ["user:email"]
        },
        "microsoft": {
            "client_id": os.getenv("MICROSOFT_CLIENT_ID"),
            "client_secret": os.getenv("MICROSOFT_CLIENT_SECRET"),
            "authorization_endpoint": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
            "token_endpoint": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
            "userinfo_endpoint": "https://graph.microsoft.com/v1.0/me",
            "scopes": ["openid", "email", "profile"]
        }
    }
    
    @staticmethod
    def get_authorization_url(provider: str, redirect_uri: str, state: str) -> str:
        """Generate OAuth 2.0 authorization URL"""
        if provider not in OAuth2Config.PROVIDERS:
            raise ValueError(f"Unsupported OAuth provider: {provider}")
        
        config = OAuth2Config.PROVIDERS[provider]
        client_id = config["client_id"]
        
        if not client_id:
            raise ValueError(f"Client ID not configured for provider: {provider}")
        
        scopes = " ".join(config["scopes"])
        
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": scopes,
            "response_type": "code",
            "state": state
        }
        
        # Add provider-specific parameters
        if provider == "microsoft":
            params["response_mode"] = "query"
        
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{config['authorization_endpoint']}?{query_string}"
    
    @staticmethod
    async def exchange_code_for_token(provider: str, code: str, redirect_uri: str) -> dict:
        """Exchange authorization code for access token"""
        import httpx
        
        if provider not in OAuth2Config.PROVIDERS:
            raise ValueError(f"Unsupported OAuth provider: {provider}")
        
        config = OAuth2Config.PROVIDERS[provider]
        client_id = config["client_id"]
        client_secret = config["client_secret"]
        
        if not client_id or not client_secret:
            raise ValueError(f"OAuth credentials not configured for provider: {provider}")
        
        token_data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri
        }
        
        headers = {"Accept": "application/json"}
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                config["token_endpoint"],
                data=token_data,
                headers=headers
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to exchange code for token: {response.text}"
                )
            
            token_response = response.json()
            access_token = token_response.get("access_token")
            
            if not access_token:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No access token received from OAuth provider"
                )
            
            # Get user info
            user_info = await OAuth2Config.get_user_info(provider, access_token)
            
            return {
                "access_token": access_token,
                "token_type": token_response.get("token_type", "Bearer"),
                "expires_in": token_response.get("expires_in"),
                "refresh_token": token_response.get("refresh_token"),
                "user_info": user_info
            }
    
    @staticmethod
    async def get_user_info(provider: str, access_token: str) -> dict:
        """Get user information from OAuth provider"""
        import httpx
        
        if provider not in OAuth2Config.PROVIDERS:
            raise ValueError(f"Unsupported OAuth provider: {provider}")
        
        config = OAuth2Config.PROVIDERS[provider]
        headers = {"Authorization": f"Bearer {access_token}"}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                config["userinfo_endpoint"],
                headers=headers
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to get user info: {response.text}"
                )
            
            user_data = response.json()
            
            # Normalize user data across providers
            normalized_data = OAuth2Config.normalize_user_data(provider, user_data)
            
            return normalized_data
    
    @staticmethod
    def normalize_user_data(provider: str, user_data: dict) -> dict:
        """Normalize user data from different OAuth providers"""
        if provider == "google":
            return {
                "id": user_data.get("id"),
                "email": user_data.get("email"),
                "name": user_data.get("name"),
                "picture": user_data.get("picture"),
                "verified_email": user_data.get("verified_email", False)
            }
        elif provider == "github":
            return {
                "id": str(user_data.get("id")),
                "email": user_data.get("email"),
                "name": user_data.get("name") or user_data.get("login"),
                "picture": user_data.get("avatar_url"),
                "verified_email": True  # GitHub emails are verified
            }
        elif provider == "microsoft":
            return {
                "id": user_data.get("id"),
                "email": user_data.get("mail") or user_data.get("userPrincipalName"),
                "name": user_data.get("displayName"),
                "picture": None,  # Microsoft Graph doesn't provide avatar in basic profile
                "verified_email": True  # Microsoft emails are verified
            }
        else:
            return user_data