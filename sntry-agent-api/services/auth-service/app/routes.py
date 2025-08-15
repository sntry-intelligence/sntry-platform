"""
Authentication service API routes
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import List
from datetime import timedelta
import secrets
import hashlib

from .models import (
    User, Role, Permission, UserCreate, UserLogin, UserResponse, 
    TokenResponse, TokenRefresh, RoleCreate, RoleResponse,
    PermissionCreate, PermissionResponse, PermissionCheck,
    UserRoleAssignment, RolePermissionAssignment, OAuthProvider,
    OAuthAuthorizationRequest, OAuthAuthorizationResponse,
    OAuthCallbackRequest, OAuthTokenResponse, OAuthProviderResponse
)
from .auth import AuthManager, get_current_user, require_permission, require_role, security, OAuth2Config
from .database import get_db

router = APIRouter()


# Authentication endpoints
@router.post("/auth/register", response_model=UserResponse)
async def register_user(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
    # Check if user already exists
    existing_user = db.query(User).filter(
        (User.email == user_data.email) | (User.username == user_data.username)
    ).first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email or username already exists"
        )
    
    # Create new user
    hashed_password = AuthManager.get_password_hash(user_data.password)
    user = User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        is_active=True,
        is_verified=False
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Assign default role (api_user)
    default_role = db.query(Role).filter(Role.name == "api_user").first()
    if default_role:
        user.roles.append(default_role)
        db.commit()
    
    return UserResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        is_active=user.is_active,
        is_verified=user.is_verified,
        roles=[role.name for role in user.roles]
    )


@router.post("/auth/login", response_model=TokenResponse)
async def login(user_credentials: UserLogin, db: Session = Depends(get_db)):
    """Authenticate user and return JWT tokens"""
    user = AuthManager.authenticate_user(db, user_credentials.username, user_credentials.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create tokens
    access_token_expires = timedelta(minutes=30)
    access_token = AuthManager.create_access_token(
        data={"sub": str(user.id), "username": user.username},
        expires_delta=access_token_expires
    )
    refresh_token = AuthManager.create_refresh_token(
        data={"sub": str(user.id), "username": user.username}
    )
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=1800  # 30 minutes
    )


@router.post("/auth/refresh", response_model=TokenResponse)
async def refresh_token(token_data: TokenRefresh, db: Session = Depends(get_db)):
    """Refresh access token using refresh token"""
    payload = AuthManager.verify_token(token_data.refresh_token, "refresh")
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == int(user_id)).first()
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    # Create new tokens
    access_token_expires = timedelta(minutes=30)
    access_token = AuthManager.create_access_token(
        data={"sub": str(user.id), "username": user.username},
        expires_delta=access_token_expires
    )
    new_refresh_token = AuthManager.create_refresh_token(
        data={"sub": str(user.id), "username": user.username}
    )
    
    # Blacklist old refresh token
    AuthManager.blacklist_token(token_data.refresh_token, 7 * 24 * 3600)  # 7 days
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=1800
    )


@router.post("/auth/logout")
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: User = Depends(get_current_user)
):
    """Logout user by blacklisting their token"""
    token = credentials.credentials
    # Blacklist the token for remaining validity period
    AuthManager.blacklist_token(token, 1800)  # 30 minutes
    
    return {"message": "Successfully logged out"}


# User management endpoints
@router.get("/auth/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        roles=[role.name for role in current_user.roles if role.is_active]
    )


@router.get("/auth/permissions")
async def check_permissions(
    permission: PermissionCheck,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Check if current user has specific permission"""
    has_permission = AuthManager.check_permission(
        db, current_user.id, permission.resource, permission.action
    )
    
    return {
        "user_id": current_user.id,
        "resource": permission.resource,
        "action": permission.action,
        "has_permission": has_permission,
        "permissions": AuthManager.get_user_permissions(db, current_user.id)
    }


# Role management endpoints (admin only)
@router.post("/auth/roles", response_model=RoleResponse)
async def create_role(
    role_data: RoleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin"))
):
    """Create a new role (admin only)"""
    existing_role = db.query(Role).filter(Role.name == role_data.name).first()
    if existing_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role with this name already exists"
        )
    
    role = Role(name=role_data.name, description=role_data.description)
    db.add(role)
    db.commit()
    db.refresh(role)
    
    return RoleResponse(
        id=role.id,
        name=role.name,
        description=role.description,
        is_active=role.is_active,
        permissions=[f"{p.resource}:{p.action}" for p in role.permissions]
    )


@router.get("/auth/roles", response_model=List[RoleResponse])
async def list_roles(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("*", "read"))
):
    """List all roles"""
    roles = db.query(Role).all()
    return [
        RoleResponse(
            id=role.id,
            name=role.name,
            description=role.description,
            is_active=role.is_active,
            permissions=[f"{p.resource}:{p.action}" for p in role.permissions]
        )
        for role in roles
    ]


# Permission management endpoints (admin only)
@router.post("/auth/permissions", response_model=PermissionResponse)
async def create_permission(
    permission_data: PermissionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin"))
):
    """Create a new permission (admin only)"""
    existing_permission = db.query(Permission).filter(
        Permission.name == permission_data.name
    ).first()
    
    if existing_permission:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Permission with this name already exists"
        )
    
    permission = Permission(
        name=permission_data.name,
        resource=permission_data.resource,
        action=permission_data.action,
        description=permission_data.description
    )
    
    db.add(permission)
    db.commit()
    db.refresh(permission)
    
    return PermissionResponse(
        id=permission.id,
        name=permission.name,
        resource=permission.resource,
        action=permission.action,
        description=permission.description
    )


@router.get("/auth/permissions", response_model=List[PermissionResponse])
async def list_permissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("*", "read"))
):
    """List all permissions"""
    permissions = db.query(Permission).all()
    return [
        PermissionResponse(
            id=permission.id,
            name=permission.name,
            resource=permission.resource,
            action=permission.action,
            description=permission.description
        )
        for permission in permissions
    ]


# User role assignment endpoints (admin only)
@router.post("/auth/users/{user_id}/roles")
async def assign_user_roles(
    user_id: int,
    assignment: UserRoleAssignment,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin"))
):
    """Assign roles to a user (admin only)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Clear existing roles
    user.roles.clear()
    
    # Assign new roles
    for role_id in assignment.role_ids:
        role = db.query(Role).filter(Role.id == role_id).first()
        if role:
            user.roles.append(role)
    
    db.commit()
    
    return {
        "user_id": user_id,
        "assigned_roles": [role.name for role in user.roles]
    }


# Role permission assignment endpoints (admin only)
@router.post("/auth/roles/{role_id}/permissions")
async def assign_role_permissions(
    role_id: int,
    assignment: RolePermissionAssignment,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin"))
):
    """Assign permissions to a role (admin only)"""
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    # Clear existing permissions
    role.permissions.clear()
    
    # Assign new permissions
    for permission_id in assignment.permission_ids:
        permission = db.query(Permission).filter(Permission.id == permission_id).first()
        if permission:
            role.permissions.append(permission)
    
    db.commit()
    
    return {
        "role_id": role_id,
        "assigned_permissions": [f"{p.resource}:{p.action}" for p in role.permissions]
    }


# OAuth 2.0 endpoints
@router.post("/auth/oauth/authorize", response_model=OAuthAuthorizationResponse)
async def oauth_authorize(request: OAuthAuthorizationRequest):
    """Initiate OAuth 2.0 authorization flow"""
    try:
        # Generate state parameter for CSRF protection
        state = request.state or secrets.token_urlsafe(32)
        
        # Generate authorization URL
        authorization_url = OAuth2Config.get_authorization_url(
            request.provider,
            request.redirect_uri,
            state
        )
        
        return OAuthAuthorizationResponse(
            authorization_url=authorization_url,
            state=state
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/auth/oauth/callback", response_model=OAuthTokenResponse)
async def oauth_callback(request: OAuthCallbackRequest, db: Session = Depends(get_db)):
    """Handle OAuth 2.0 callback and create/login user"""
    try:
        # Exchange code for token and get user info
        oauth_data = await OAuth2Config.exchange_code_for_token(
            request.provider,
            request.code,
            request.redirect_uri
        )
        
        user_info = oauth_data["user_info"]
        
        # Check if OAuth provider account already exists
        oauth_provider = db.query(OAuthProvider).filter(
            OAuthProvider.provider == request.provider,
            OAuthProvider.provider_user_id == user_info["id"]
        ).first()
        
        if oauth_provider:
            # Update existing OAuth provider record
            oauth_provider.access_token = oauth_data["access_token"]
            oauth_provider.refresh_token = oauth_data.get("refresh_token")
            oauth_provider.email = user_info["email"]
            oauth_provider.name = user_info["name"]
            oauth_provider.picture = user_info["picture"]
            
            user = oauth_provider.user
        else:
            # Check if user exists by email
            user = db.query(User).filter(User.email == user_info["email"]).first()
            
            if not user:
                # Create new user
                user = User(
                    email=user_info["email"],
                    username=user_info["email"],  # Use email as username for OAuth users
                    hashed_password="",  # OAuth users don't have passwords
                    full_name=user_info["name"],
                    is_active=True,
                    is_verified=user_info.get("verified_email", False)
                )
                
                db.add(user)
                db.flush()
                
                # Assign default role
                default_role = db.query(Role).filter(Role.name == "api_user").first()
                if default_role:
                    user.roles.append(default_role)
            
            # Create OAuth provider record
            oauth_provider = OAuthProvider(
                user_id=user.id,
                provider=request.provider,
                provider_user_id=user_info["id"],
                email=user_info["email"],
                name=user_info["name"],
                picture=user_info["picture"],
                access_token=oauth_data["access_token"],
                refresh_token=oauth_data.get("refresh_token")
            )
            
            db.add(oauth_provider)
        
        db.commit()
        db.refresh(user)
        
        # Create JWT tokens for the user
        access_token_expires = timedelta(minutes=30)
        access_token = AuthManager.create_access_token(
            data={"sub": str(user.id), "username": user.username},
            expires_delta=access_token_expires
        )
        refresh_token = AuthManager.create_refresh_token(
            data={"sub": str(user.id), "username": user.username}
        )
        
        return OAuthTokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=1800,
            user=UserResponse(
                id=user.id,
                email=user.email,
                username=user.username,
                full_name=user.full_name,
                is_active=user.is_active,
                is_verified=user.is_verified,
                roles=[role.name for role in user.roles if role.is_active]
            )
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OAuth callback failed: {str(e)}"
        )


@router.get("/auth/oauth/providers", response_model=List[OAuthProviderResponse])
async def get_user_oauth_providers(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get OAuth providers linked to current user"""
    providers = db.query(OAuthProvider).filter(
        OAuthProvider.user_id == current_user.id
    ).all()
    
    return [
        OAuthProviderResponse(
            id=provider.id,
            provider=provider.provider,
            provider_user_id=provider.provider_user_id,
            email=provider.email,
            name=provider.name,
            picture=provider.picture,
            created_at=provider.created_at
        )
        for provider in providers
    ]


@router.delete("/auth/oauth/providers/{provider_id}")
async def unlink_oauth_provider(
    provider_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Unlink OAuth provider from current user"""
    provider = db.query(OAuthProvider).filter(
        OAuthProvider.id == provider_id,
        OAuthProvider.user_id == current_user.id
    ).first()
    
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OAuth provider not found"
        )
    
    # Check if user has a password or other OAuth providers
    user_has_password = bool(current_user.hashed_password)
    other_providers = db.query(OAuthProvider).filter(
        OAuthProvider.user_id == current_user.id,
        OAuthProvider.id != provider_id
    ).count()
    
    if not user_has_password and other_providers == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot unlink the only authentication method. Set a password first."
        )
    
    db.delete(provider)
    db.commit()
    
    return {"message": "OAuth provider unlinked successfully"}


# Password management for OAuth users
@router.post("/auth/set-password")
async def set_password(
    password_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Set password for OAuth users"""
    password = password_data.get("password")
    
    if not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password is required"
        )
    
    if len(password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long"
        )
    
    # Hash and set the password
    current_user.hashed_password = AuthManager.get_password_hash(password)
    db.commit()
    
    return {"message": "Password set successfully"}