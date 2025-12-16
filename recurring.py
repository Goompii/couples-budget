from db_connection import execute_query, fetch_all, fetch_one
from datetime import datetime, timedelta


def save_recurring_transaction(couple_id, category, amount, frequency, next_date, description, status="Active"):
    """Save a recurring transaction/subscription"""
    try:
        query = """
        INSERT INTO recurring_transactions (couple_id, category_name, amount, frequency, next_date, description, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        execute_query(query, (couple_id, category, amount, frequency, next_date, description, status, datetime.now().strftime('%Y-%m-%d')))
        return True, "✅ Recurring transaction added!"
    except Exception as e:
        return False, f"❌ Error: {str(e)}"


def get_recurring_transactions(user_or_couple_id):
    """Get all recurring transactions for a user or couple"""
    try:
        query = """
        SELECT id, category_name, amount, frequency, next_date, description, status, created_at
        FROM recurring_transactions
        WHERE couple_id = ?
        ORDER BY next_date ASC
        """
        results = fetch_all(query, (user_or_couple_id,))
        return results
    except Exception as e:
        print(f"Error: {str(e)}")
        return []

def update_recurring_status(recurring_id, status):
    """Update recurring transaction status (Active/Paused/Cancelled)"""
    try:
        query = "UPDATE recurring_transactions SET status = ? WHERE id = ?"
        execute_query(query, (status, recurring_id))
        return True, f"Status updated to {status}"
    except Exception as e:
        return False, f"Error: {str(e)}"


def delete_recurring_transaction(recurring_id):
    """Delete a recurring transaction"""
    try:
        query = "DELETE FROM recurring_transactions WHERE id = ?"
        execute_query(query, (recurring_id,))
        return True, "Recurring transaction deleted"
    except Exception as e:
        return False, f"Error: {str(e)}"


def process_due_recurring_transactions(couple_id):
    """Automatically create transactions for due recurring items"""
    try:
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Get all active recurring transactions that are due
        query = """
        SELECT id, category_name, amount, frequency, next_date
        FROM recurring_transactions
        WHERE couple_id = ? AND status = 'Active' AND next_date <= ?
        """
        due_items = fetch_all(query, (couple_id, today))
        
        created_count = 0
        
        for item in due_items:
            # Create actual transaction
            from transactions import save_transaction
            success, _ = save_transaction(
                user_id=couple_id,  # Use couple_id as user for tracking
                couple_id=couple_id,
                amount=item['amount'],
                category=item['category_name'],
                description=f"[RECURRING] {item['category_name']}",
                trans_date=today,
                trans_type='Expense'
            )
            
            if success:
                created_count += 1
                # Calculate next date
                next_date = calculate_next_date(item['next_date'], item['frequency'])
                
                # Update recurring transaction with next date
                query = "UPDATE recurring_transactions SET next_date = ? WHERE id = ?"
                execute_query(query, (next_date, item['id']))
        
        return created_count
    except Exception as e:
        print(f"Error processing recurring: {str(e)}")
        return 0


def calculate_next_date(current_date, frequency):
    """Calculate next due date based on frequency"""
    current = datetime.strptime(current_date, '%Y-%m-%d')
    
    if frequency == 'Weekly':
        next_date = current + timedelta(days=7)
    elif frequency == 'Bi-weekly':
        next_date = current + timedelta(days=14)
    elif frequency == 'Monthly':
        if current.month == 12:
            next_date = current.replace(year=current.year + 1, month=1)
        else:
            next_date = current.replace(month=current.month + 1)
    elif frequency == 'Quarterly':
        next_date = current + timedelta(days=90)
    elif frequency == 'Yearly':
        next_date = current.replace(year=current.year + 1)
    else:
        next_date = current
    
    return next_date.strftime('%Y-%m-%d')


def get_upcoming_subscriptions(couple_id, days_ahead=30):
    """Get subscriptions due in next N days"""
    try:
        today = datetime.now().strftime('%Y-%m-%d')
        future = (datetime.now() + timedelta(days=days_ahead)).strftime('%Y-%m-%d')
        
        query = """
        SELECT id, category_name, amount, frequency, next_date, description, status
        FROM recurring_transactions
        WHERE couple_id = ? AND status = 'Active' AND next_date BETWEEN ? AND ?
        ORDER BY next_date ASC
        """
        results = fetch_all(query, (couple_id, today, future))
        return results
    except Exception as e:
        print(f"Error: {str(e)}")
        return []


def get_monthly_subscription_cost(couple_id):
    """Calculate total monthly subscription cost"""
    try:
        query = """
        SELECT SUM(amount) as total
        FROM recurring_transactions
        WHERE couple_id = ? AND status = 'Active'
        AND frequency IN ('Monthly', 'Weekly', 'Bi-weekly')
        """
        result = fetch_one(query, (couple_id,))
        
        # Calculate monthly equivalent
        monthly_total = 0
        
        query2 = "SELECT amount, frequency FROM recurring_transactions WHERE couple_id = ? AND status = 'Active'"
        items = fetch_all(query2, (couple_id,))
        
        for item in items:
            if item['frequency'] == 'Weekly':
                monthly_total += item['amount'] * 4.33  # Average weeks per month
            elif item['frequency'] == 'Bi-weekly':
                monthly_total += item['amount'] * 2.17  # Average bi-weeks per month
            elif item['frequency'] == 'Monthly':
                monthly_total += item['amount']
        
        return monthly_total
    except Exception as e:
        print(f"Error: {str(e)}")
        return 0
