"""
utils/security.py
------------------
Password hashing helpers and the @login_required decorator used
to protect admin-only routes.
"""

from functools import wraps
from flask import session, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash


def hash_password(plain_password):
    return generate_password_hash(plain_password)


def verify_password(plain_password, password_hash):
    return check_password_hash(password_hash, plain_password)


def login_required(view_func):
    """Redirects to the login page if no admin is logged in."""

    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not session.get("admin_id"):
            flash("Please log in to continue.", "warning")
            return redirect(url_for("auth.login"))
        return view_func(*args, **kwargs)

    return wrapped
