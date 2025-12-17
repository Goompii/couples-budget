from db_connection import execute_query, fetch_all, fetch_one
from datetime import datetime


def send_pairing_request(user1_id, user2_username, couple_name=""):
    """Send a pairing invitation to another user"""
    try:
        # Find user2 by username
        query = "SELECT id, username FROM users WHERE username = ?"
        user2 = fetch_one(query, (user2_username,))
        
        if not user2:
            return False, "❌ User not found"
        
        user2_id = user2['id']
        
        # Prevent pairing with self
        if user1_id == user2_id:
            return False, "❌ You cannot pair with yourself"
        
        # Check if already paired (either direction)
        query = """
        SELECT id FROM couple_pairs 
        WHERE (user1_id = ? AND user2_id = ?) OR (user1_id = ? AND user2_id = ?)
        """
        existing = fetch_one(query, (user1_id, user2_id, user2_id, user1_id))
        
        if existing:
            return False, "❌ Already paired with this user"
        
        # Check if invitation already pending (either direction)
        query = """
        SELECT id FROM pairing_invitations 
        WHERE ((sender_id = ? AND receiver_id = ?) OR (sender_id = ? AND receiver_id = ?))
        AND status = 'Pending'
        """
        pending = fetch_one(query, (user1_id, user2_id, user2_id, user1_id))
        
        if pending:
            return False, "⚠️ Invitation already pending with this user"
        
        # Create invitation
        query = """
        INSERT INTO pairing_invitations (sender_id, receiver_id, couple_name, status, created_at)
        VALUES (?, ?, ?, 'Pending', ?)
        """
        execute_query(query, (user1_id, user2_id, couple_name, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        
        return True, f"✅ Invitation sent to {user2_username}! Waiting for their response..."
        
    except Exception as e:
        return False, f"❌ Error: {str(e)}"


def get_pending_invitations(user_id):
    """Get all pending invitations for a user"""
    try:
        query = """
        SELECT 
            pi.id, 
            u.username, 
            u.full_name, 
            pi.couple_name, 
            pi.created_at,
            CASE 
                WHEN pi.sender_id = ? THEN 'Sent'
                ELSE 'Received'
            END as invitation_type
        FROM pairing_invitations pi
        JOIN users u ON (
            CASE 
                WHEN pi.sender_id = ? THEN pi.receiver_id = u.id
                ELSE pi.sender_id = u.id
            END
        )
        WHERE (pi.sender_id = ? OR pi.receiver_id = ?)
        AND pi.status = 'Pending'
        ORDER BY pi.created_at DESC
        """
        results = fetch_all(query, (user_id, user_id, user_id, user_id))
        return results
    except Exception as e:
        print(f"Error fetching invitations: {str(e)}")
        return []


def accept_invitation(invitation_id, user_id):
    """Accept a pairing invitation"""
    try:
        # Get invitation details
        query = "SELECT sender_id, receiver_id, couple_name FROM pairing_invitations WHERE id = ?"
        invitation = fetch_one(query, (invitation_id,))
        
        if not invitation:
            return False, "❌ Invitation not found"
        
        # Security: Check if user is the receiver
        if invitation['receiver_id'] != user_id:
            return False, "❌ You can only accept invitations sent to you"
        
        # Create couple pairing
        query = """
        INSERT INTO couple_pairs (user1_id, user2_id, couple_name, created_at)
        VALUES (?, ?, ?, ?)
        """
        execute_query(query, (invitation['sender_id'], invitation['receiver_id'], invitation['couple_name'], datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        
        # Update invitation status
        query = "UPDATE pairing_invitations SET status = 'Accepted' WHERE id = ?"
        execute_query(query, (invitation_id,))
        
        return True, "✅ Invitation accepted! You are now paired!"
        
    except Exception as e:
        return False, f"❌ Error: {str(e)}"


def reject_invitation(invitation_id, user_id):
    """Reject a pairing invitation"""
    try:
        # Get invitation details
        query = "SELECT sender_id, receiver_id FROM pairing_invitations WHERE id = ?"
        invitation = fetch_one(query, (invitation_id,))
        
        if not invitation:
            return False, "❌ Invitation not found"
        
        # Security: Check if user is the receiver
        if invitation['receiver_id'] != user_id:
            return False, "❌ You can only reject invitations sent to you"
        
        # Update invitation status
        query = "UPDATE pairing_invitations SET status = 'Rejected' WHERE id = ?"
        execute_query(query, (invitation_id,))
        
        return True, "✅ Invitation rejected"
        
    except Exception as e:
        return False, f"❌ Error: {str(e)}"


def cancel_invitation(invitation_id, user_id):
    """Cancel a sent invitation (sender only)"""
    try:
        # Get invitation details
        query = "SELECT sender_id FROM pairing_invitations WHERE id = ?"
        invitation = fetch_one(query, (invitation_id,))
        
        if not invitation:
            return False, "❌ Invitation not found"
        
        # Security: Check if user is the sender
        if invitation['sender_id'] != user_id:
            return False, "❌ You can only cancel invitations you sent"
        
        # Delete invitation
        query = "DELETE FROM pairing_invitations WHERE id = ?"
        execute_query(query, (invitation_id,))
        
        return True, "✅ Invitation cancelled"
        
    except Exception as e:
        return False, f"❌ Error: {str(e)}"


def get_couple_id(user_id):
    """Get couple_id for a user (only if officially paired)"""
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
    """Get partner's info (only if officially paired)"""
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
