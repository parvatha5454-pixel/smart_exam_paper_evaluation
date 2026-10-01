"""
create_admin.py
-----------------
Run this once after setting up the database to create your first
admin login.

Usage:
    python create_admin.py
"""

import getpass
from models.admin_model import get_admin_by_username, create_admin, count_admins
from utils.security import hash_password


def main():
    print("=== Create Admin Account ===")
    username = input("Username: ").strip()
    email = input("Email: ").strip()
    full_name = input("Full name: ").strip()
    password = getpass.getpass("Password: ")
    confirm = getpass.getpass("Confirm password: ")

    if password != confirm:
        print("Passwords do not match. Aborting.")
        return

    if get_admin_by_username(username):
        print(f"An admin with username '{username}' already exists.")
        return

    password_hash = hash_password(password)
    admin_id = create_admin(username, email, password_hash, full_name)
    print(f"Admin '{username}' created successfully (id={admin_id}).")
    print(f"Total admins now: {count_admins()}")


if __name__ == "__main__":
    main()
