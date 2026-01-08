def record_login(username: str) -> None:
    print(f"[AUDIT] User logged in: {username}")


def record_logout(username: str) -> None:
    print(f"[AUDIT] User logged out: {username}")
