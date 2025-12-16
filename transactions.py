from db_connection import execute_query, fetch_all, fetch_one
from datetime import datetime

def save_transaction(user_id, couple_id, amount, category, description, trans_date, trans_type):
    """Save a transaction to database"""
    try:
        # Check if category exists
        query = "SELECT id FROM categories WHERE couple_id = ? AND category_name = ?"
        category_result = fetch_one(query, (couple_id, category))
        
        if category_result:
            category_id = category_result['id']
        else:
            # Create new category
            category_type = 'expense' if trans_type == 'Expense' else 'income'
            query = "INSERT INTO categories (couple_id, category_name, category_type) VALUES (?, ?, ?)"
            execute_query(query, (couple_id, category, category_type))
            
            # Get the newly created category id
            query = "SELECT id FROM categories WHERE couple_id = ? AND category_name = ?"
            category_result = fetch_one(query, (couple_id, category))
            category_id = category_result['id']
        
        # Save the transaction
        query = "INSERT INTO transactions (couple_id, user_id, category_id, amount, description, transaction_date, transaction_type) VALUES (?, ?, ?, ?, ?, ?, ?)"
        execute_query(query, (couple_id, user_id, category_id, amount, description, trans_date, trans_type))
        return True, "✅ Transaction saved!"
        
    except Exception as e:
        return False, f"❌ Error: {str(e)}"

def get_user_transactions(couple_id, user_id=None):
    """Get transactions for a user or couple"""
    try:
        if user_id:
            query = """
            SELECT t.id, t.amount, t.description, t.transaction_date, t.transaction_type, c.category_name
            FROM transactions t
            JOIN categories c ON t.category_id = c.id
            WHERE t.couple_id = ? AND t.user_id = ?
            ORDER BY t.transaction_date DESC
            """
            params = (couple_id, user_id)
        else:
            query = """
            SELECT t.id, t.amount, t.description, t.transaction_date, t.transaction_type, c.category_name
            FROM transactions t
            JOIN categories c ON t.category_id = c.id
            WHERE t.couple_id = ?
            ORDER BY t.transaction_date DESC
            """
            params = (couple_id,)
        
        results = fetch_all(query, params)
        return results
    except Exception as e:
        print(f"Error fetching transactions: {str(e)}")
        return []

def get_category_summary(couple_id, month=None, year=None):
    """Get spending summary by category"""
    try:
        if not month or not year:
            now = datetime.now()
            month = now.month
            year = now.year
        
        query = """
        SELECT c.category_name, t.transaction_type, SUM(t.amount) as total
        FROM transactions t
        JOIN categories c ON t.category_id = c.id
        WHERE t.couple_id = ? 
        AND strftime('%m', t.transaction_date) = ? 
        AND strftime('%Y', t.transaction_date) = ?
        GROUP BY c.category_name, t.transaction_type
        """
        results = fetch_all(query, (couple_id, f"{month:02d}", f"{year}"))
        return results
    except Exception as e:
        print(f"Error fetching summary: {str(e)}")
        return []

def get_monthly_total(couple_id, month=None, year=None):
    """Get total income and expenses for the month"""
    try:
        if not month or not year:
            now = datetime.now()
            month = now.month
            year = now.year
        
        query = """
        SELECT transaction_type, SUM(amount) as total
        FROM transactions
        WHERE couple_id = ? 
        AND strftime('%m', transaction_date) = ? 
        AND strftime('%Y', transaction_date) = ?
        GROUP BY transaction_type
        """
        results = fetch_all(query, (couple_id, f"{month:02d}", f"{year}"))
        return results
    except Exception as e:
        print(f"Error fetching monthly total: {str(e)}")
        return []

def save_budget(couple_id, category_name, planned_amount, month, year):
    """Save or update a budget for a category"""
    try:
        # Get category id
        query = "SELECT id FROM categories WHERE couple_id = ? AND category_name = ?"
        cat = fetch_one(query, (couple_id, category_name))
        
        if not cat:
            st.error(f"Category {category_name} not found")
            return False, "Category not found"
        
        category_id = cat['id']
        month_year = f"{year}-{month:02d}"
        
        # Check if budget already exists
        query = "SELECT id FROM budgets WHERE couple_id = ? AND category_id = ? AND month_year = ?"
        existing = fetch_one(query, (couple_id, category_id, month_year))
        
        if existing:
            # Update existing budget
            query = "UPDATE budgets SET planned_amount = ? WHERE couple_id = ? AND category_id = ? AND month_year = ?"
            execute_query(query, (planned_amount, couple_id, category_id, month_year))
        else:
            # Create new budget
            query = "INSERT INTO budgets (couple_id, category_id, planned_amount, month_year) VALUES (?, ?, ?, ?)"
            execute_query(query, (couple_id, category_id, planned_amount, month_year))
        
        return True, "✅ Budget saved!"
        
    except Exception as e:
        return False, f"❌ Error: {str(e)}"

def get_budgets(couple_id, month=None, year=None):
    """Get all budgets for a month"""
    try:
        if not month or not year:
            now = datetime.now()
            month = now.month
            year = now.year
        
        month_year = f"{year}-{month:02d}"
        
        query = """
        SELECT b.id, c.category_name, b.planned_amount, b.month_year
        FROM budgets b
        JOIN categories c ON b.category_id = c.id
        WHERE b.couple_id = ? AND b.month_year = ?
        """
        results = fetch_all(query, (couple_id, month_year))
        return results
    except Exception as e:
        print(f"Error fetching budgets: {str(e)}")
        return []

def get_budget_vs_actual(couple_id, month=None, year=None):
    """Get budget vs actual spending by category"""
    try:
        if not month or not year:
            now = datetime.now()
            month = now.month
            year = now.year
        
        month_year = f"{year}-{month:02d}"
        
        query = """
        SELECT 
            c.category_name,
            COALESCE(b.planned_amount, 0) as budgeted,
            COALESCE(SUM(t.amount), 0) as actual
        FROM categories c
        LEFT JOIN budgets b ON c.id = b.category_id AND b.month_year = ? AND b.couple_id = ?
        LEFT JOIN transactions t ON c.id = t.category_id 
            AND t.transaction_type = 'Expense'
            AND strftime('%m', t.transaction_date) = ?
            AND strftime('%Y', t.transaction_date) = ?
            AND t.couple_id = ?
        WHERE c.couple_id = ? AND c.category_type = 'expense'
        GROUP BY c.category_name
        """
        results = fetch_all(query, (month_year, couple_id, f"{month:02d}", f"{year}", couple_id, couple_id))
        return results
    except Exception as e:
        print(f"Error: {str(e)}")
        return []
