from db_connection import execute_query, fetch_all, fetch_one
from datetime import datetime

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD_HASH = "$2b$12$R9h7cIPz0gi.URNNVZ3IqeIVVQKrm7XZeKrVl5/P.yt1ySa7dVDaC"  # bcrypt hash of "Admin@123"

def is_admin(username, password_hash):
    """Check if user is admin"""
    import bcrypt
    return username == ADMIN_USERNAME and bcrypt.checkpw(password_hash.encode('utf-8'), ADMIN_PASSWORD_HASH.encode('utf-8'))

def get_all_users():
    """Get all users in system"""
    try:
        query = "SELECT id, username, email, full_name, created_at FROM users ORDER BY created_at DESC"
        results = fetch_all(query)
        return results
    except Exception as e:
        print(f"Error: {str(e)}")
        return []

def delete_user(user_id):
    """Delete a user and all their data"""
    try:
        # Get couple_id associated with this user
        query = """
        SELECT id FROM couple_pairs 
        WHERE user1_id = ? OR user2_id = ?
        """
        couple = fetch_one(query, (user_id, user_id))
        
        if couple:
            couple_id = couple['id']
            # Delete all transactions for this couple
            query = "DELETE FROM transactions WHERE couple_id = ?"
            execute_query(query, (couple_id,))
            
            # Delete all budgets for this couple
            query = "DELETE FROM budgets WHERE couple_id = ?"
            execute_query(query, (couple_id,))
            
            # Delete all categories for this couple
            query = "DELETE FROM categories WHERE couple_id = ?"
            execute_query(query, (couple_id,))
            
            # Delete the couple pair
            query = "DELETE FROM couple_pairs WHERE id = ?"
            execute_query(query, (couple_id,))
        
        # Delete the user
        query = "DELETE FROM users WHERE id = ?"
        execute_query(query, (user_id,))
        
        return True, "✅ User deleted successfully"
    except Exception as e:
        return False, f"❌ Error: {str(e)}"

def get_user_details(user_id):
    """Get detailed info about a user"""
    try:
        query = """
        SELECT id, username, email, full_name, created_at 
        FROM users WHERE id = ?
        """
        user = fetch_one(query, (user_id,))
        
        if not user:
            return None
        
        # Get transaction count
        query = """
        SELECT COUNT(*) as count FROM transactions WHERE user_id = ?
        """
        trans_result = fetch_one(query, (user_id,))
        trans_count = trans_result['count'] if trans_result else 0
        
        # Get couple info if exists
        query = """
        SELECT cp.id, cp.couple_name, u.username, u.full_name
        FROM couple_pairs cp
        JOIN users u ON (u.id = cp.user1_id OR u.id = cp.user2_id)
        WHERE (cp.user1_id = ? OR cp.user2_id = ?) AND u.id != ?
        """
        partner = fetch_one(query, (user_id, user_id, user_id))
        
        return {
            'user': user,
            'transaction_count': trans_count,
            'partner': partner
        }
    except Exception as e:
        print(f"Error: {str(e)}")
        return None

def get_system_stats():
    """Get overall system statistics"""
    try:
        # Total users
        query = "SELECT COUNT(*) as count FROM users"
        users_result = fetch_one(query)
        total_users = users_result['count'] if users_result else 0
        
        # Total couples
        query = "SELECT COUNT(*) as count FROM couple_pairs"
        couples_result = fetch_one(query)
        total_couples = couples_result['count'] if couples_result else 0
        
        # Total transactions
        query = "SELECT COUNT(*) as count FROM transactions"
        trans_result = fetch_one(query)
        total_transactions = trans_result['count'] if trans_result else 0
        
        # Total budgets
        query = "SELECT COUNT(*) as count FROM budgets"
        budget_result = fetch_one(query)
        total_budgets = budget_result['count'] if budget_result else 0
        
        return {
            'total_users': total_users,
            'total_couples': total_couples,
            'total_transactions': total_transactions,
            'total_budgets': total_budgets
        }
    except Exception as e:
        print(f"Error: {str(e)}")
        return {}

def get_all_transactions():
    """Get all transactions in system"""
    try:
        query = """
        SELECT t.id, u.username, c.category_name, t.amount, t.transaction_type, t.transaction_date, t.description
        FROM transactions t
        JOIN users u ON t.user_id = u.id
        JOIN categories c ON t.category_id = c.id
        ORDER BY t.transaction_date DESC
        LIMIT 100
        """
        results = fetch_all(query)
        return results
    except Exception as e:
        print(f"Error: {str(e)}")
        return []
    
def get_transactions_by_user_id(user_id):
    """Get all transactions for a specific user (admin view)"""
    try:
        query = """
        SELECT t.id, t.amount, t.description, t.transaction_date, t.transaction_type, c.category_name
        FROM transactions t
        JOIN categories c ON t.category_id = c.id
        WHERE t.user_id = ?
        ORDER BY t.transaction_date DESC
        """
        results = fetch_all(query, (user_id,))
        return results
    except Exception as e:
        print(f"Error fetching user transactions: {str(e)}")
        return []

def delete_transaction(transaction_id):
    """Delete a specific transaction"""
    try:
        query = "DELETE FROM transactions WHERE id = ?"
        execute_query(query, (transaction_id,))
        return True, "✅ Transaction deleted"
    except Exception as e:
        return False, f"❌ Error: {str(e)}"

def reset_user_password(user_id, new_password):
    """Reset user password (admin only)"""
    try:
        import bcrypt
        password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        query = "UPDATE users SET password_hash = ? WHERE id = ?"
        execute_query(query, (password_hash, user_id))
        return True, "✅ Password reset successfully"
    except Exception as e:
        return False, f"❌ Error: {str(e)}"
