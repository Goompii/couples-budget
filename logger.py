import logging
import os

# Configure logging to save to a file named 'admin_audit.log'
logging.basicConfig(
    filename='admin_audit.log',
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def log_admin_action(admin_username, action, target_id, details=""):
    """
    Log an admin action to the file
    Example: log_admin_action("admin", "DELETE_USER", 5, "Deleted user John")
    """
    message = f"ADMIN: {admin_username} | ACTION: {action} | TARGET_ID: {target_id} | {details}"
    
    # Write to file
    logging.info(message)
    
    # Print to console (so you see it in VS Code terminal)
    print(f"📝 Audit Log: {message}")
