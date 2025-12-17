import bcrypt
from db_connection import execute_query, fetch_one
from security import validate_username, validate_email, validate_password, sanitize_input

def hash_password(password):
    """Hash a password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password, password_hash):
    """Verify a password against its hash"""
    return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))

def register_user(username, email, password, full_name):
    """Register a new user with validation"""
    try:
        # Validate inputs
        valid, msg = validate_username(username)
        if not valid:
            return False, msg
        
        valid, msg = validate_email(email)
        if not valid:
            return False, msg
        
        valid, msg = validate_password(password)
        if not valid:
            return False, msg
        
        if len(full_name) < 2 or len(full_name) > 50:
            return False, "Full name must be 2-50 characters"
        
        # Sanitize inputs
        username = sanitize_input(username)
        email = sanitize_input(email)
        full_name = sanitize_input(full_name)
        
        # Hash password
        password_hash = hash_password(password)
        
        query = """
        INSERT INTO users (username, email, password_hash, full_name)
        VALUES (?, ?, ?, ?)
        """
        execute_query(query, (username, email, password_hash, full_name))
        return True, "✅ Registration successful!"
        
    except Exception as e:
        if "UNIQUE constraint failed" in str(e):
            return False, "❌ Username or email already exists"
        return False, f"❌ Registration failed"

def login_user(username, password):
    """Login a user and return user info"""
    # Get user info AND password hash in ONE query (not two!)
    query = "SELECT id, username, email, full_name, password_hash FROM users WHERE username = ?"
    user = fetch_one(query, (username,))
    
    if not user:
        return False, None, "Username not found"
    
    # Verify password
    if verify_password(password, user['password_hash']):
        # Return without the password hash (security)
        return True, {
            'id': user['id'],
            'username': user['username'],
            'email': user['email'],
            'full_name': user['full_name']
        }, "Login successful!"
    else:
        return False, None, "Incorrect password"

def get_user_by_id(user_id):
    """Get user information by ID"""
    query = "SELECT id, username, email, full_name FROM users WHERE id = ?"
    return fetch_one(query, (user_id,))

def reset_user_password(user_id, new_password):
    """Reset a user's password (Admin function)"""
    try:
        hashed_password = hash_password(new_password)
        
        query = "UPDATE users SET password_hash = ? WHERE id = ?"
        execute_query(query, (hashed_password, user_id))
        
        return True, "✅ Password reset successfully!"
    except Exception as e:
        return False, f"❌ Error: {str(e)}"
