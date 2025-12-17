import os
from dotenv import load_dotenv
import sys

def validate_env_file():
    """
    Validate that .env file exists and has required variables
    Prevents app crashes if .env is missing or incomplete
    """
    
    # Load environment variables from .env file
    load_dotenv()
    
    # Required variables
    required_vars = [
        'ADMIN_USERNAME',
        'ADMIN_PASSWORD_HASH',
        'DATABASE_URL'
    ]
    
    missing_vars = []
    
    # Check each required variable
    for var in required_vars:
        value = os.getenv(var)
        if not value or value.strip() == '':
            missing_vars.append(var)
    
    # If any variables are missing, show error and exit
    if missing_vars:
        error_message = f"""
❌ CONFIGURATION ERROR
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Missing required environment variables in .env file:
{', '.join(missing_vars)}

Please create/update your .env file with:

ADMIN_USERNAME=admin
ADMIN_PASSWORD_HASH=<your_hashed_password>
DATABASE_URL=database/budget.db

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        print(error_message)
        sys.exit(1)
    
    return True

def get_safe_env(var_name, default=None):
    """
    Safely get environment variable with fallback
    Returns default if variable doesn't exist
    """
    value = os.getenv(var_name, default)
    if value is None:
        raise ValueError(f"Environment variable '{var_name}' not found and no default provided")
    return value
