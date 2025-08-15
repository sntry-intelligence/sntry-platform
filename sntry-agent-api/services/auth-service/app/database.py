"""
Database configuration and session management for auth service
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from .models import Base, User, Role, Permission, OAuthProvider, user_roles, role_permissions
from .auth import AuthManager

# Database configuration
DATABASE_URL = os.getenv(
    "AUTH_DATABASE_URL",
    "postgresql://postgres:password@localhost:5432/auth_db"
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Create all database tables"""
    Base.metadata.create_all(bind=engine)


def init_default_data(db: Session):
    """Initialize default roles and permissions"""
    
    # Create default permissions
    default_permissions = [
        # Agent management permissions
        {"name": "create_agent", "resource": "agents", "action": "create", "description": "Create new AI agents"},
        {"name": "read_agent", "resource": "agents", "action": "read", "description": "View AI agents"},
        {"name": "update_agent", "resource": "agents", "action": "update", "description": "Modify AI agents"},
        {"name": "delete_agent", "resource": "agents", "action": "delete", "description": "Delete AI agents"},
        
        # Model management permissions
        {"name": "create_model", "resource": "models", "action": "create", "description": "Create new models"},
        {"name": "read_model", "resource": "models", "action": "read", "description": "View models"},
        {"name": "update_model", "resource": "models", "action": "update", "description": "Modify models"},
        {"name": "delete_model", "resource": "models", "action": "delete", "description": "Delete models"},
        
        # Training permissions
        {"name": "create_training", "resource": "training", "action": "create", "description": "Start training jobs"},
        {"name": "read_training", "resource": "training", "action": "read", "description": "View training jobs"},
        {"name": "update_training", "resource": "training", "action": "update", "description": "Modify training jobs"},
        {"name": "delete_training", "resource": "training", "action": "delete", "description": "Cancel training jobs"},
        
        # Data management permissions
        {"name": "create_data", "resource": "data", "action": "create", "description": "Upload data"},
        {"name": "read_data", "resource": "data", "action": "read", "description": "View data"},
        {"name": "update_data", "resource": "data", "action": "update", "description": "Modify data"},
        {"name": "delete_data", "resource": "data", "action": "delete", "description": "Delete data"},
        
        # System administration permissions
        {"name": "admin_all", "resource": "*", "action": "*", "description": "Full system access"},
        {"name": "read_all", "resource": "*", "action": "read", "description": "Read access to all resources"},
    ]
    
    for perm_data in default_permissions:
        existing_perm = db.query(Permission).filter(Permission.name == perm_data["name"]).first()
        if not existing_perm:
            permission = Permission(**perm_data)
            db.add(permission)
    
    # Create default roles
    default_roles = [
        {
            "name": "admin",
            "description": "System administrator with full access",
            "permissions": ["admin_all"]
        },
        {
            "name": "ai_engineer",
            "description": "AI engineer with model and training access",
            "permissions": [
                "create_agent", "read_agent", "update_agent", "delete_agent",
                "create_model", "read_model", "update_model", "delete_model",
                "create_training", "read_training", "update_training", "delete_training",
                "create_data", "read_data", "update_data", "delete_data"
            ]
        },
        {
            "name": "data_scientist",
            "description": "Data scientist with data and model access",
            "permissions": [
                "read_agent", "create_model", "read_model", "update_model",
                "create_training", "read_training", "update_training",
                "create_data", "read_data", "update_data", "delete_data"
            ]
        },
        {
            "name": "viewer",
            "description": "Read-only access to all resources",
            "permissions": ["read_all"]
        },
        {
            "name": "api_user",
            "description": "Basic API access for inference",
            "permissions": ["read_agent", "read_model"]
        }
    ]
    
    for role_data in default_roles:
        existing_role = db.query(Role).filter(Role.name == role_data["name"]).first()
        if not existing_role:
            role = Role(name=role_data["name"], description=role_data["description"])
            db.add(role)
            db.flush()  # Flush to get the role ID
            
            # Assign permissions to role
            for perm_name in role_data["permissions"]:
                permission = db.query(Permission).filter(Permission.name == perm_name).first()
                if permission:
                    role.permissions.append(permission)
    
    db.commit()


def create_admin_user(db: Session, email: str, username: str, password: str, full_name: str = None):
    """Create an admin user"""
    # Check if admin user already exists
    existing_user = db.query(User).filter(
        (User.email == email) | (User.username == username)
    ).first()
    
    if existing_user:
        return existing_user
    
    # Create admin user
    hashed_password = AuthManager.get_password_hash(password)
    admin_user = User(
        email=email,
        username=username,
        hashed_password=hashed_password,
        full_name=full_name or "System Administrator",
        is_active=True,
        is_verified=True
    )
    
    db.add(admin_user)
    db.flush()
    
    # Assign admin role
    admin_role = db.query(Role).filter(Role.name == "admin").first()
    if admin_role:
        admin_user.roles.append(admin_role)
    
    db.commit()
    return admin_user


def initialize_database():
    """Initialize database with tables and default data"""
    create_tables()
    
    db = SessionLocal()
    try:
        init_default_data(db)
        
        # Create default admin user if specified in environment
        admin_email = os.getenv("ADMIN_EMAIL")
        admin_username = os.getenv("ADMIN_USERNAME", "admin")
        admin_password = os.getenv("ADMIN_PASSWORD")
        
        if admin_email and admin_password:
            create_admin_user(
                db, 
                admin_email, 
                admin_username, 
                admin_password,
                "Default Administrator"
            )
            print(f"Created admin user: {admin_username}")
        
    finally:
        db.close()


if __name__ == "__main__":
    initialize_database()
    print("Database initialized successfully!")