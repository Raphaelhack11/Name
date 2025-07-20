from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from email_validator import validate_email, EmailNotValidError
import random
import smtplib
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Replace with a strong secret key
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///grants.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

ADMIN_EMAIL = "marshabills9@gmail.com"

class GrantRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    reason = db.Column(db.Text)
    approved = db.Column(db.Boolean, default=False)

with app.app_context():
    db.create_all()

def send_otp(to_email, otp):
    gmail_user = os.environ.get("GMAIL_USER")
    gmail_pass = os.environ.get("GMAIL_PASS")
    
    if not gmail_user or not gmail_pass:
        raise Exception("Missing Gmail credentials in environment variables")

    subject = "Your Admin OTP Code"
    body = f"Your one-time login OTP is: {otp}"

    email_text = f"""\
From: {gmail_user}
To: {to_email}
Subject: {subject}

{body}
"""

    server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
    server.login(gmail_user, gmail_pass)
    server.sendmail(gmail_user, to_email, email_text)
    server.quit()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/submit', methods=['POST'])
def submit():
    name = request.form['name']
    email = request.form['email']
    reason = request.form['reason']

    try:
        validate_email(email)
    except EmailNotValidError:
        flash('Invalid email address.', 'error')
        return redirect(url_for('index'))

    existing_user = GrantRequest.query.filter_by(email=email).first()
    if existing_user:
        flash('Email already submitted.', 'error')
        return redirect(url_for('index'))

    grant = GrantRequest(name=name, email=email, reason=reason)
    db.session.add(grant)
    db.session.commit()
    return redirect(url_for('thank_you'))

@app.route('/thank-you')
def thank_you():
    return render_template('thank_you.html')

@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form['email']
        if email == ADMIN_EMAIL:
            otp = str(random.randint(100000, 999999))
            session['otp'] = otp
            session['admin_email'] = email
            send_otp(email, otp)
            return redirect(url_for('verify_otp'))
        else:
            flash('Unauthorized email', 'error')
    return render_template('admin_login.html')

@app.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    if request.method == 'POST':
        input_otp = request.form['otp']
        if input_otp == session.get('otp'):
            session['admin_logged_in'] = True
            return redirect(url_for('admin'))
        else:
            flash('Incorrect OTP', 'error')
    return render_template('verify_otp.html')

@app.route('/admin')
def admin():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    grants = GrantRequest.query.all()
    return render_template('admin.html', grants=grants)

@app.route('/approve/<int:id>')
def approve(id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    grant = GrantRequest.query.get_or_404(id)
    grant.approved = True
    db.session.commit()
    flash('User approved. Please send email manually.')
    return redirect(url_for('admin'))

if __name__ == '__main__':
    app.run(debug=True)
