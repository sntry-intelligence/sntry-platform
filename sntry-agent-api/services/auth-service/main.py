import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from shared.interfaces.base_service import BaseService
from sqlalchemy.orm import Session

# Import auth service components
from app.routes import router as auth_router
from app.database import get_db, initialize_database
from app.models import User
from app.auth import get_current_user


class AuthService(BaseService):
    """Authentication and authorization service"""
    
    def __init__(self):
        super().__init__("auth-service")
        # Initialize database on startup
        initialize_database()
    
    def _setup_routes(self, app: FastAPI):
        """Setup authentication service routes"""
        
        # Add CORS middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Configure appropriately for production
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Health check endpoint
        @app.get("/health")
        async def health_check():
            return self.get_health_status()
        
        # Include authentication routes
        app.include_router(auth_router, tags=["authentication"])
        
        # Override the dependency injection for database sessions
        app.dependency_overrides[get_db] = self._get_db_session
        
        # Override the dependency injection for current user
        def get_current_user_with_db(
            current_user: User = Depends(get_current_user),
            db: Session = Depends(self._get_db_session)
        ):
            # Re-query user to ensure fresh data and proper session
            user = db.query(User).filter(User.id == current_user.id).first()
            if not user:
                raise HTTPException(status_code=401, detail="User not found")
            return user
        
        # Update the dependency
        from app.auth import get_current_user as original_get_current_user
        app.dependency_overrides[original_get_current_user] = get_current_user_with_db
    
    def _get_db_session(self):
        """Get database session for dependency injection"""
        from app.database import SessionLocal
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()


# Create service instance
auth_service = AuthService()
app = auth_service.app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)  # Use port 8001 for auth service