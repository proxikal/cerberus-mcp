"""Comprehensive Symbol Guard Demo - Phase 13.2 Testing

This file demonstrates Symbol Guard risk-aware mutation protection with:
1. HIGH RISK symbols: Heavily referenced, low stability
2. MEDIUM RISK symbols: Moderately referenced, medium stability
3. SAFE symbols: Rarely referenced, high stability
"""


# Core infrastructure function - Will be HIGH RISK (many dependencies)
def core_database_connector(host: str, port: int) -> dict:
    """Critical database connection function used throughout the system.

    This is a core infrastructure component that many modules depend on.
    Deleting or modifying this without care would break the entire system.
    """
    return {
        "host": host,
        "port": port,
        "status": "connected",
        "pool_size": 10
    }


# Authentication function - Will be MEDIUM RISK (moderate dependencies)
def authenticate_user(username: str, password: str) -> bool:
    """Authenticate user credentials.

    Used by several authentication flows but not critical infrastructure.
    Changes here require careful review but won't break everything.
    """
    db = core_database_connector("localhost", 5432)
    # Simplified auth logic
    return username and password and db["status"] == "connected"


# API endpoint handler - Will be MEDIUM RISK
def handle_login_request(data: dict) -> dict:
    """Handle login API endpoint.

    Entry point for user authentication flow.
    """
    username = data.get("username", "")
    password = data.get("password", "")

    if authenticate_user(username, password):
        return {"success": True, "token": "abc123"}
    return {"success": False, "error": "Invalid credentials"}


# Secondary API endpoint
def handle_logout_request(token: str) -> dict:
    """Handle logout API endpoint.

    Used by logout flows.
    """
    db = core_database_connector("localhost", 5432)
    return {"success": True, "logged_out": True}


# Data processing function
def process_user_data(user_id: int) -> dict:
    """Process user data from database.

    Fetches and processes user information.
    """
    db = core_database_connector("localhost", 5432)
    return {"user_id": user_id, "data": "processed"}


# Report generation
def generate_user_report(user_id: int) -> str:
    """Generate user activity report.

    Creates formatted report from user data.
    """
    data = process_user_data(user_id)
    return f"Report for user {data['user_id']}: {data['data']}"


# Batch processing
def batch_process_users(user_ids: list) -> list:
    """Process multiple users in batch.

    Efficient batch processing of user data.
    """
    db = core_database_connector("localhost", 5432)
    results = []
    for user_id in user_ids:
        data = process_user_data(user_id)
        results.append(data)
    return results


# Analytics function
def calculate_user_metrics(user_id: int) -> dict:
    """Calculate analytics metrics for a user.

    Computes various user engagement metrics.
    """
    data = process_user_data(user_id)
    return {
        "user_id": user_id,
        "engagement_score": 85,
        "activity_count": 42
    }


# Notification system
def send_user_notification(user_id: int, message: str) -> bool:
    """Send notification to user.

    Handles user notification delivery.
    """
    db = core_database_connector("localhost", 5432)
    # Simplified notification logic
    return True


# Helper function - Will be SAFE (few/no dependencies)
def format_timestamp(timestamp: int) -> str:
    """Format Unix timestamp to human-readable string.

    Simple utility function with no external dependencies.
    Low risk - safe to modify or delete.
    """
    from datetime import datetime
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")


# Another safe helper
def validate_email(email: str) -> bool:
    """Validate email format.

    Simple validation utility.
    Safe to modify - standalone function.
    """
    return "@" in email and "." in email


# Rarely used debugging function - SAFE
def debug_connection_pool() -> dict:
    """Debug utility for connection pool inspection.

    Rarely used debugging function.
    Safe to delete or modify.
    """
    return {
        "active_connections": 5,
        "idle_connections": 5,
        "total": 10
    }


if __name__ == "__main__":
    # Demonstrate usage
    print("=== Symbol Guard Demo ===")

    # Core infrastructure (HIGH RISK to delete)
    db = core_database_connector("localhost", 5432)
    print(f"Database: {db}")

    # Authentication flow (MEDIUM RISK)
    auth_result = authenticate_user("admin", "password123")
    print(f"Auth: {auth_result}")

    # API endpoints (MEDIUM RISK)
    login = handle_login_request({"username": "admin", "password": "password123"})
    print(f"Login: {login}")

    # Data processing (referenced by multiple functions)
    user_data = process_user_data(1)
    print(f"User data: {user_data}")

    # Reports (depends on data processing)
    report = generate_user_report(1)
    print(f"Report: {report}")

    # Batch operations
    batch = batch_process_users([1, 2, 3])
    print(f"Batch: {batch}")

    # Analytics
    metrics = calculate_user_metrics(1)
    print(f"Metrics: {metrics}")

    # Utilities (SAFE to modify)
    timestamp_str = format_timestamp(1704096000)
    print(f"Timestamp: {timestamp_str}")

    email_valid = validate_email("user@example.com")
    print(f"Email valid: {email_valid}")
