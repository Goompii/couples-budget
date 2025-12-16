from db_connection import execute_query, fetch_all, fetch_one

def send_pairing_request(user1_id, user2_username, couple_name=""):
    """Send a pairing request to another user"""
    try:
        # Find user2 by username
        query = "SELECT id FROM users WHERE username = ?"
        user2 = fetch_one(query, (user2_username,))
        
        if not user2:
            return False, "❌ User not found"
        
        user2_id = user2['id']
        
        # Check if already paired
        query = """
        SELECT id FROM couple_pairs 
        WHERE (user1_id = ? AND user2_id = ?) OR (user1_id = ? AND user2_id = ?)
        """
        existing = fetch_one(query, (user1_id, user2_id, user2_id, user1_id))
        
        if existing:
            return False, "❌ Already paired with this user"
        
        # Create pairing
        query = """
        INSERT INTO couple_pairs (user1_id, user2_id, couple_name)
        VALUES (?, ?, ?)
        """
        execute_query(query, (user1_id, user2_id, couple_name))
        return True, "✅ Paired successfully!"
        
    except Exception as e:
        return False, f"❌ Error: {str(e)}"

def get_couple_id(user_id):
    """Get couple_id for a user"""
    try:
        query = """
        SELECT id FROM couple_pairs 
        WHERE user1_id = ? OR user2_id = ?
        """
        result = fetch_one(query, (user_id, user_id))
        
        if result:
            return result['id']
        return None
    except Exception as e:
        print(f"Error: {str(e)}")
        return None

def get_partner_info(couple_id, current_user_id):
    """Get partner's info"""
    try:
        query = """
        SELECT u.id, u.username, u.full_name, u.email
        FROM users u
        JOIN couple_pairs cp ON (u.id = cp.user1_id OR u.id = cp.user2_id)
        WHERE cp.id = ? AND u.id != ?
        """
        result = fetch_one(query, (couple_id, current_user_id))
        return result
    except Exception as e:
        print(f"Error: {str(e)}")
        return None

def unpair_couple(couple_id):
    """Unpair a couple"""
    try:
        query = "DELETE FROM couple_pairs WHERE id = ?"
        execute_query(query, (couple_id,))
        return True, "✅ Unpairing successful"
    except Exception as e:
        return False, f"❌ Error: {str(e)}"
