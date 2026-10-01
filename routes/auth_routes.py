"""
routes/auth_routes.py
----------------------
Module 1: Login / Admin Module
- Admin login & logout
- Session management
- Dashboard with summary stats
"""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash

from models.admin_model import get_admin_by_username, update_last_login
from models.dashboard_model import get_dashboard_stats, get_recent_evaluations
from utils.security import verify_password, login_required
from utils.logger import log_activity

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/", methods=["GET"])
def index():
    if session.get("admin_id"):
        return redirect(url_for("auth.dashboard"))
    return redirect(url_for("auth.login"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("admin_id"):
        return redirect(url_for("auth.dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            flash("Please enter both username and password.", "danger")
            return render_template("login.html")

        admin = get_admin_by_username(username)

        if admin and verify_password(password, admin["password_hash"]):
            session.permanent = True
            session["admin_id"] = admin["admin_id"]
            session["admin_username"] = admin["username"]
            session["admin_full_name"] = admin["full_name"]

            update_last_login(admin["admin_id"])
            log_activity(admin["admin_id"], "LOGIN", f"Admin '{username}' logged in.")

            flash(f"Welcome back, {admin['full_name'] or admin['username']}!", "success")
            return redirect(url_for("auth.dashboard"))

        flash("Invalid username or password.", "danger")
        return render_template("login.html")

    return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    admin_id = session.get("admin_id")
    if admin_id:
        log_activity(admin_id, "LOGOUT", f"Admin '{session.get('admin_username')}' logged out.")
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/dashboard")
@login_required
def dashboard():
    stats = get_dashboard_stats()
    recent = get_recent_evaluations(limit=5)
    return render_template("dashboard.html", stats=stats, recent=recent)
