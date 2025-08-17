import os
import smtplib
from email.message import EmailMessage
from datetime import datetime

from flask import (
    Flask, render_template, request, redirect, url_for, session, flash
)
from flask_sqlalchemy import SQLAlchemy

# -----------------------------------------------------------------------------
# Config
# -----------------------------------------------------------------------------
app = Flask(__name__)

# Secret key (used for sessions & security) -> set in environment
app.secret_key = os.environ.get("SECRET_KEY", "fallback-secret")

# SQLite DB (file-based, simple and works for demos)
DB_PATH = os.environ.get("DATABASE_URL", "sqlite:///leaves.db")
app.config["SQLALCHEMY_DATABASE_URI"] = DB_PATH
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# Admin credentials (stored in environment, safer than hardcoding)
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")

# Email credentials (set Gmail app password in env)
EMAIL_USER = os.environ.get("EMAIL_USER")
EMAIL_PASS = os.environ.get("EMAIL_PASS")

# -----------------------------------------------------------------------------
# DB Model
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

with app.app_context():
    db.create_all()

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def send_email(to_email: str, subject: str, body: str) -> None:
    """Send email if EMAIL_USER and EMAIL_PASS are configured."""
    if not EMAIL_USER or not EMAIL_PASS:
        app.logger.warning("Email creds not set; skipping email to %s", to_email)
        return

    try:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = EMAIL_USER
        msg["To"] = to_email
        msg.set_content(body)

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)

        app.logger.info("Email sent to %s", to_email)
    except Exception as e:
        app.logger.error("Email error: %s", e)

def is_admin():
    return session.get("admin", False)

# -----------------------------------------------------------------------------
# Routes
# -----------------------------------------------------------------------------
@app.route("/")
def home():
    return render_template("index.html")

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
            flash("Please fill all fields.", "error")
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

        flash("Leave request submitted successfully!", "success")
        return redirect(url_for("home"))

    return render_template("leave.html")

@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect(url_for("admin_dashboard"))
        flash("Invalid username or password", "error")
    return render_template("admin_login.html")

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
            # email notify
            subject = f"Leave Request {action}"
            body = f"Hello {req.name},\n\nYour leave request has been {action}.\n\nRegards,\nAdmin"
            send_email(req.email, subject, body)
            flash(f"Request #{req.id} marked as {action}.", "success")
        else:
            flash("Invalid request/action.", "error")

    leave_requests = LeaveRequest.query.order_by(LeaveRequest.created_at.desc()).all()
    return render_template("admin.html", leave_requests=leave_requests)

@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect(url_for("home"))

# -----------------------------------------------------------------------------
# Entry
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
