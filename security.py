import re
import streamlit as st
from functools import wraps
import time

# Session timeout tracking
SESSION_TIMEOUT_MINUTES = 30

def validate_username(username):
    """Validate username - alphanumeric and underscore only"""
    if len(username) < 3 or len(username) > 20:
        return False, "Username must be 3-20 characters"
    
    if not re.match("^[a-zA-Z0-9_]+$", username):
        return False, "Username can only contain letters, numbers, and underscore"
    
    return True, "Valid"

def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if re.match(pattern, email):
        return True, "Valid"
    return False, "Invalid email format"

def validate_password(password):
    """Validate password strength"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    
    if not any(c.isupper() for c in password):
        return False, "Password must contain uppercase letter"
    
    if not any(c.isdigit() for c in password):
        return False, "Password must contain number"
    
    return True, "Strong password"

def sanitize_input(user_input):
    """Remove dangerous characters"""
    if not isinstance(user_input, str):
        return user_input
    
    # Remove SQL injection attempts
    dangerous = ["';", "--", "/*", "*/", "xp_", "sp_", "exec", "execute"]
    sanitized = user_input
    
    for danger in dangerous:
        sanitized = sanitized.replace(danger, "")
    
    return sanitized.strip()

def check_session_timeout():
    """Check if session has timed out"""
    if 'last_activity' not in st.session_state:
        st.session_state.last_activity = time.time()
        return False
    
    # Handle None value
    if st.session_state.last_activity is None:
        st.session_state.last_activity = time.time()
        return False
    
    elapsed = time.time() - st.session_state.last_activity
    timeout_seconds = SESSION_TIMEOUT_MINUTES * 60
    
    if elapsed > timeout_seconds:
        st.session_state.logged_in = False
        st.session_state.user_id = None
        st.session_state.username = None
        st.warning("⏱️ Session timed out. Please login again.")
        return True
    
    # Update last activity
    st.session_state.last_activity = time.time()
    return False
