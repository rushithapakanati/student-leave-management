import os
import requests
from email.message import EmailMessage
from datetime import datetime
from flask import (
    Flask, render_template, request, redirect, url_for, session, flash
)
from flask_sqlalchemy import SQLAlchemy

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
app = Flask(__name__)

# Secret key (used for sessions & security)
app.secret_key = os.environ.get("SECRET_KEY", "fallback-secret")

# SQLite DB (simple and works well for Render)
DB_PATH = os.environ.get("DATABASE_URL", "sqlite:///leaves.db")
app.config["SQLALCHEMY_DATABASE_URI"] = DB_PATH
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# Admin credentials (set via Render environment variables)
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")

# -----------------------------------------------------------------------------
# Database Model
# -----------------------------------------------------------------------------
class LeaveRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    idno = db.Column(db.String(60), nullable=False)
    fromdate = db.Column(db.String(20), nullable=False)
    todate = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(200), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default="Pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Create tables if they don't exist
with app.app_context():
    db.create_all()

# -----------------------------------------------------------------------------
# Helper: Send Email (Render-Friendly using SendGrid)
# -----------------------------------------------------------------------------
def send_email(to_email: str, subject: str, body: str):
    """Send email using SendGrid API (works on Render)."""
    SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY")
    if not SENDGRID_API_KEY:
        app.logger.error("Missing SENDGRID_API_KEY environment variable.")
        return

    try:
        response = requests.post(
            "https://api.sendgrid.com/v3/mail/send",
            headers={
                "Authorization": f"Bearer {SENDGRID_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "personalizations": [{"to": [{"email": to_email}]}],
                "from": {"email": "student.leave.system@gmail.com", "name": "Leave Management Admin"},
                "subject": subject,
                "content": [{"type": "text/plain", "value": body}],
            },
        )

        if 200 <= response.status_code < 300:
            app.logger.info(f"✅ Email sent to {to_email}")
        else:
            app.logger.error(f"❌ Email failed ({response.status_code}): {response.text}")

    except Exception as e:
        app.logger.error(f"SendGrid email error: {e}")

# -----------------------------------------------------------------------------
# Helper: Check Admin Session
# -----------------------------------------------------------------------------
def is_admin():
    return session.get("admin", False)

# -----------------------------------------------------------------------------
# Routes
# -----------------------------------------------------------------------------
@app.route("/")
def home():
    return render_template("index.html")

# ---------------------------------------------------------------------
# Leave Request Form
# ---------------------------------------------------------------------
@app.route("/leave", methods=["GET", "POST"])
def leave():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        idno = request.form.get("idno", "").strip()
        fromdate = request.form.get("fromdate", "").strip()
        todate = request.form.get("todate", "").strip()
        email = request.form.get("email", "").strip()
        type_of_leave = request.form.get("type", "").strip()
        reason = request.form.get("reason", "").strip()

        if not all([name, idno, fromdate, todate, email, type_of_leave, reason]):
            flash("⚠️ Please fill all fields.", "error")
            return render_template("leave.html")

        req = LeaveRequest(
            name=name,
            idno=idno,
            fromdate=fromdate,
            todate=todate,
            email=email,
            type=type_of_leave,
            reason=reason,
            status="Pending",
        )
        db.session.add(req)
        db.session.commit()

        flash("✅ Leave request submitted successfully!", "success")
        return redirect(url_for("home"))

    return render_template("leave.html")

# ---------------------------------------------------------------------
# Admin Login
# ---------------------------------------------------------------------
@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect(url_for("admin_dashboard"))
        flash("❌ Invalid username or password", "error")
    return render_template("admin_login.html")

# ---------------------------------------------------------------------
# Admin Dashboard
# ---------------------------------------------------------------------
@app.route("/admin", methods=["GET", "POST"])
def admin_dashboard():
    if not is_admin():
        return redirect(url_for("admin_login"))

    if request.method == "POST":
        action = request.form.get("action")
        rid = request.form.get("id")

        req = LeaveRequest.query.get(int(rid))
        if req and action in {"Approved", "Rejected"}:
            req.status = action
            db.session.commit()

            # Notify student via email
            subject = f"Leave Request {action}"
            body = (
                f"Hello {req.name},\n\n"
                f"Your leave request (from {req.fromdate} to {req.todate}) "
                f"has been {action}.\n\n"
                "Regards,\nAdmin\nLeave Management System"
            )
            send_email(req.email, subject, body)
            flash(f"Request #{req.id} marked as {action}.", "success")
        else:
            flash("⚠️ Invalid request or action.", "error")

    leave_requests = LeaveRequest.query.order_by(LeaveRequest.created_at.desc()).all()
    return render_template("admin.html", leave_requests=leave_requests)

# ---------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------
@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect(url_for("home"))

# -----------------------------------------------------------------------------
# Entry Point
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
