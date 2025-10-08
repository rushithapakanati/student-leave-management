from flask import Flask, render_template, request, redirect, flash, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Email
import os
import requests

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///leaves.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ------------------- DATABASE MODELS -------------------
class Leave(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(50), nullable=False)
    student_name = db.Column(db.String(100), nullable=False)
    leave_reason = db.Column(db.String(300), nullable=False)

# ------------------- FORMS -------------------
class LeaveForm(FlaskForm):
    student_id = StringField('Student ID', validators=[DataRequired()])
    student_name = StringField('Student Name', validators=[DataRequired()])
    leave_reason = TextAreaField('Reason', validators=[DataRequired()])
    submit = SubmitField('Apply Leave')

class AdminLoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = StringField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

# ------------------- ROUTES -------------------
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/leave', methods=['GET', 'POST'])
def leave():
    form = LeaveForm()
    if form.validate_on_submit():
        new_leave = Leave(
            student_id=form.student_id.data,
            student_name=form.student_name.data,
            leave_reason=form.leave_reason.data
        )
        db.session.add(new_leave)
        db.session.commit()
        flash("Leave applied successfully!", "success")
        return redirect(url_for('index'))
    return render_template('leave.html', form=form)

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    form = AdminLoginForm()
    if form.validate_on_submit():
        if form.username.data == 'admin' and form.password.data == 'admin123':
            return redirect(url_for('admin_dashboard'))
        else:
            flash("Invalid credentials!", "danger")
    return render_template('admin_login.html', form=form)

@app.route('/admin', methods=['GET', 'POST'])
def admin_dashboard():
    leaves = Leave.query.all()
    if request.method == 'POST':
        leave_id = request.form.get('leave_id')
        student_email = request.form.get('email')
        send_email(student_email, "Leave Approved", "Your leave has been approved by Admin.")
        flash("Email sent successfully!", "success")
    return render_template('admin.html', leaves=leaves)

# ------------------- SEND EMAIL FUNCTION -------------------
def send_email(to_email, subject, content):
    api_key = os.environ.get('SENDGRID_API_KEY')
    sender_email = os.environ.get('SENDER_EMAIL')
    
    if not api_key or not sender_email:
        print("SendGrid API key or sender email missing.")
        return

    url = "https://api.sendgrid.com/v3/mail/send"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "personalizations": [{"to": [{"email": to_email}]}],
        "from": {"email": sender_email},
        "subject": subject,
        "content": [{"type": "text/plain", "value": content}]
    }

    response = requests.post(url, headers=headers, json=data)
    if response.status_code != 202:
        print(f"❌ Email failed ({response.status_code}): {response.text}")
    else:
        print("✅ Email sent successfully")

# ------------------- MAIN -------------------
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)), debug=True)
