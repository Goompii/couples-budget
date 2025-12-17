import os
from dotenv import load_dotenv
from db_connection import execute_query, fetch_all, fetch_one
from datetime import datetime
from logger import log_admin_action  # <-- IMPORT THE LOGGER

# Load environment variables from .env file
load_dotenv()

# Get admin credentials from .env file (safe, not in code!)
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD_HASH = os.getenv('ADMIN_PASSWORD_HASH')


def is_admin(username, password_hash):
    """Check if user is admin"""
    import bcrypt
    return username == ADMIN_USERNAME and bcrypt.checkpw(password_hash.encode('utf-8'), ADMIN_PASSWORD_HASH.encode('utf-8'))


def check_admin_permission(user_id, username):
    """Verify user has admin access - SECURITY CHECK"""
    if username != ADMIN_USERNAME:
        return False, "❌ Admin access required"
    return True, "Authorized"


def get_all_users():
    """Get all users in system"""
    try:
        query = "SELECT id, username, email, full_name, created_at FROM users ORDER BY created_at DESC"
        results = fetch_all(query)
        return results
    except Exception as e:
        print(f"Error: {str(e)}")
        return []


def delete_user(admin_username, user_id):
    """Delete a user and all their data - REQUIRES ADMIN"""
    try:
        # SECURITY: Check if user is admin
        has_permission, msg = check_admin_permission(None, admin_username)
        if not has_permission:
            return False, msg
        
        # Prevent deleting admin user
        if str(user_id) == str(1) or admin_username == user_id: # Basic check to protect admin account
            return False, "❌ Cannot delete admin/primary user"
        
        # Get couple_id associated with this user
        query = """
        SELECT id FROM couple_pairs 
        WHERE user1_id = ? OR user2_id = ?
        """
        couple = fetch_one(query, (user_id, user_id))
        
        if couple:
            couple_id = couple['id']
            # Delete all transactions for this couple
            execute_query("DELETE FROM transactions WHERE couple_id = ?", (couple_id,))
            execute_query("DELETE FROM budgets WHERE couple_id = ?", (couple_id,))
            execute_query("DELETE FROM categories WHERE couple_id = ?", (couple_id,))
            execute_query("DELETE FROM recurring_transactions WHERE couple_id = ?", (couple_id,))
            execute_query("DELETE FROM couple_pairs WHERE id = ?", (couple_id,))
        
        # Delete the user
        execute_query("DELETE FROM users WHERE id = ?", (user_id,))
        
        # LOG THE ACTION
        log_admin_action(admin_username, "DELETE_USER", user_id, "Deleted user and all associated data")
        
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


def delete_transaction(admin_username, transaction_id):
    """Delete a specific transaction - REQUIRES ADMIN"""
    try:
        # SECURITY: Check if user is admin
        has_permission, msg = check_admin_permission(None, admin_username)
        if not has_permission:
            return False, msg
        
        query = "DELETE FROM transactions WHERE id = ?"
        execute_query(query, (transaction_id,))
        
        # LOG THE ACTION
        log_admin_action(admin_username, "DELETE_TRANSACTION", transaction_id, "Deleted single transaction")
        
        return True, "✅ Transaction deleted"
    except Exception as e:
        return False, f"❌ Error: {str(e)}"


def reset_user_password(admin_username, user_id, new_password):
    """Reset user password (admin only) - REQUIRES ADMIN"""
    try:
        # SECURITY: Check if user is admin
        has_permission, msg = check_admin_permission(None, admin_username)
        if not has_permission:
            return False, msg
        
        import bcrypt
        password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        query = "UPDATE users SET password_hash = ? WHERE id = ?"
        execute_query(query, (password_hash, user_id))
        
        # LOG THE ACTION
        log_admin_action(admin_username, "RESET_PASSWORD", user_id, "Admin reset user password")
        
        return True, "✅ Password reset successfully"
    except Exception as e:
        return False, f"❌ Error: {str(e)}"
