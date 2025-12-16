import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database
DATABASE_PATH = os.getenv('DATABASE_PATH', 'database/budget.db')

# App Settings
APP_NAME = "Couples Budget App"
APP_VERSION = "1.0.0"
SECRET_KEY = os.getenv('SECRET_KEY', 'change-me-in-production')
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

# Session timeout (minutes)
SESSION_TIMEOUT = int(os.getenv('SESSION_TIMEOUT', 30))

# Default budget categories
DEFAULT_CATEGORIES = {
    'Housing': 'expense',
    'Food & Groceries': 'expense',
    'Transportation': 'expense',
    'Entertainment': 'expense',
    'Utilities': 'expense',
    'Healthcare': 'expense',
    'Savings': 'income',
    'Salary': 'income',
    'Bonus': 'income',
}
