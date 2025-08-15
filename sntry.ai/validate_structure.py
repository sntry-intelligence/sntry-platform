#!/usr/bin/env python3
"""
Validate the project structure and file contents
"""

import os
from pathlib import Path

def check_file_exists(file_path: str) -> bool:
    """Check if a file exists"""
    return Path(file_path).exists()

def check_directory_exists(dir_path: str) -> bool:
    """Check if a directory exists"""
    return Path(dir_path).is_dir()

def validate_project_structure():
    """Validate the overall project structure"""
    print("Validating project structure...")
    
    # Check core directories
    directories = [
        "shared",
        "shared/models",
        "shared/repositories",
        "shared/utils",
        "services",
        "tests",
        "scripts",
        "prisma"
    ]
    
    for directory in directories:
        if check_directory_exists(directory):
            print(f"✅ Directory exists: {directory}")
        else:
            print(f"❌ Directory missing: {directory}")
    
    # Check core files
    files = [
        "shared/__init__.py",
        "shared/config.py",
        "shared/database.py",
        "shared/models/__init__.py",
        "shared/models/base.py",
        "shared/models/agent.py",
        "shared/models/workflow.py",
        "shared/models/tool.py",
        "shared/models/conversation.py",
        "shared/models/vector_store.py",
        "shared/models/mcp.py",
        "shared/models/evaluation.py",
        "shared/repositories/__init__.py",
        "shared/repositories/base.py",
        "shared/repositories/agent_repository.py",
        "shared/repositories/workflow_repository.py",
        "shared/repositories/tool_repository.py",
        "shared/repositories/conversation_repository.py",
        "shared/repositories/vector_store_repository.py",
        "prisma/schema.prisma",
        "scripts/migrate.py",
        "tests/test_models.py",
        "tests/test_repositories.py",
        "tests/test_database.py",
        "requirements.txt"
    ]
    
    for file in files:
        if check_file_exists(file):
            print(f"✅ File exists: {file}")
        else:
            print(f"❌ File missing: {file}")

def validate_model_files():
    """Validate model file contents"""
    print("\nValidating model files...")
    
    model_files = [
        "shared/models/agent.py",
        "shared/models/workflow.py", 
        "shared/models/tool.py",
        "shared/models/conversation.py",
        "shared/models/vector_store.py",
        "shared/models/mcp.py",
        "shared/models/evaluation.py"
    ]
    
    for model_file in model_files:
        if check_file_exists(model_file):
            with open(model_file, 'r') as f:
                content = f.read()
                
            # Check for key patterns
            if "from pydantic import BaseModel" in content:
                print(f"✅ {model_file} has Pydantic imports")
            else:
                print(f"❌ {model_file} missing Pydantic imports")
                
            if "class " in content:
                print(f"✅ {model_file} has class definitions")
            else:
                print(f"❌ {model_file} missing class definitions")

def validate_repository_files():
    """Validate repository file contents"""
    print("\nValidating repository files...")
    
    repo_files = [
        "shared/repositories/agent_repository.py",
        "shared/repositories/workflow_repository.py",
        "shared/repositories/tool_repository.py", 
        "shared/repositories/conversation_repository.py",
        "shared/repositories/vector_store_repository.py"
    ]
    
    for repo_file in repo_files:
        if check_file_exists(repo_file):
            with open(repo_file, 'r') as f:
                content = f.read()
                
            # Check for key patterns
            if "class " in content and "Repository" in content:
                print(f"✅ {repo_file} has Repository class")
            else:
                print(f"❌ {repo_file} missing Repository class")
                
            if "async def create" in content:
                print(f"✅ {repo_file} has async create method")
            else:
                print(f"❌ {repo_file} missing async create method")

def validate_database_schema():
    """Validate Prisma database schema"""
    print("\nValidating database schema...")
    
    schema_file = "prisma/schema.prisma"
    if check_file_exists(schema_file):
        with open(schema_file, 'r') as f:
            content = f.read()
            
        # Check for key models
        models = [
            "model Agent",
            "model Workflow", 
            "model Tool",
            "model ConversationSession",
            "model Message",
            "model VectorStore",
            "model Embedding",
            "model MCPServer",
            "model Evaluation"
        ]
        
        for model in models:
            if model in content:
                print(f"✅ Schema has {model}")
            else:
                print(f"❌ Schema missing {model}")
    else:
        print("❌ Prisma schema file not found")

def validate_test_files():
    """Validate test file contents"""
    print("\nValidating test files...")
    
    test_files = [
        "tests/test_models.py",
        "tests/test_repositories.py",
        "tests/test_database.py"
    ]
    
    for test_file in test_files:
        if check_file_exists(test_file):
            with open(test_file, 'r') as f:
                content = f.read()
                
            # Check for key patterns
            if "import pytest" in content:
                print(f"✅ {test_file} has pytest imports")
            else:
                print(f"❌ {test_file} missing pytest imports")
                
            if "def test_" in content:
                print(f"✅ {test_file} has test functions")
            else:
                print(f"❌ {test_file} missing test functions")

def count_lines_of_code():
    """Count lines of code in the project"""
    print("\nCounting lines of code...")
    
    total_lines = 0
    file_count = 0
    
    # Python files to count
    python_files = []
    for root, dirs, files in os.walk("."):
        # Skip certain directories
        if any(skip in root for skip in [".git", "__pycache__", ".pytest_cache", "node_modules"]):
            continue
            
        for file in files:
            if file.endswith(".py"):
                python_files.append(os.path.join(root, file))
    
    for file_path in python_files:
        try:
            with open(file_path, 'r') as f:
                lines = len(f.readlines())
                total_lines += lines
                file_count += 1
        except Exception as e:
            print(f"Warning: Could not read {file_path}: {e}")
    
    print(f"📊 Total Python files: {file_count}")
    print(f"📊 Total lines of code: {total_lines}")
    
    # Count Prisma schema lines
    if check_file_exists("prisma/schema.prisma"):
        with open("prisma/schema.prisma", 'r') as f:
            schema_lines = len(f.readlines())
        print(f"📊 Prisma schema lines: {schema_lines}")

def main():
    """Run all validations"""
    print("🔍 Validating sntry.ai project structure and implementation...\n")
    
    validate_project_structure()
    validate_model_files()
    validate_repository_files()
    validate_database_schema()
    validate_test_files()
    count_lines_of_code()
    
    print("\n🎉 Validation complete!")

if __name__ == "__main__":
    main()