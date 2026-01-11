"""Client file that depends on demo_symbol_guard.py

This creates cross-file dependencies to properly test Symbol Guard.
"""

from demo_symbol_guard import (
    core_database_connector,  # Should be HIGH RISK when deleted
    authenticate_user,         # Should be MEDIUM/HIGH RISK
    handle_login_request,      # Should be MEDIUM RISK
    format_timestamp,          # Should be SAFE (utility)
)


def client_function_one():
    """Uses core_database_connector - creates external reference."""
    db = core_database_connector("prod-server", 3306)
    return db["status"]


def client_function_two():
    """Uses authentication - creates external reference."""
    result = authenticate_user("test_user", "test_pass")
    return result


def client_function_three():
    """Uses login handler - creates external reference."""
    response = handle_login_request({"username": "admin", "password": "secret"})
    return response["success"]


def client_function_four():
    """Also uses core_database_connector - multiple references."""
    db = core_database_connector("backup-server", 5432)
    status = db["status"]
    pool = db["pool_size"]
    return f"{status}:{pool}"


def client_utility():
    """Uses utility function - low risk dependency."""
    timestamp = format_timestamp(1704096000)
    return timestamp


if __name__ == "__main__":
    print("Client functions:")
    print(f"Function 1: {client_function_one()}")
    print(f"Function 2: {client_function_two()}")
    print(f"Function 3: {client_function_three()}")
    print(f"Function 4: {client_function_four()}")
    print(f"Utility: {client_utility()}")
