from flask import request, flash, render_template, redirect, url_for, session, current_app

from db import users_collection as users

from utils.auth_checker import validate_email, validate_password
from utils.token import generate_confirmation_token
from functools import wraps

from flask_mail import Message

from extensions.bcrypt import bcrypt
from extensions.mail import mail
# from extensions.captcha import recaptcha

def auth_register():
    if request.method == 'POST':
        fname = request.form['fname'].strip()
        lname = request.form['lname'].strip()
        email = request.form['email'].strip().lower()
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if not all([fname, lname, email, password, confirm_password]):
            flash('All fields are required!', 'error')
            return render_template('/auth/register.html')
        
        if not validate_email(email):
            flash('Please enter a valid email address!', 'error')
            return render_template('/auth/register.html')
        
        if password != confirm_password:
            flash('Passwords do not match!', 'error')
            return render_template('/auth/register.html')
        
        is_valid, password_message = validate_password(password)
        if not is_valid:
            flash(password_message, 'error')
            return render_template('/auth/register.html')

        if users.find_one({'email': email}):
            flash('Email already registered! Please use a different email or try logging in.', 'error')
            return render_template('/auth/register.html')
        
        try:
            hashed_password = bcrypt.generate_password_hash(password)
            user_data = {
                'firstname': fname,
                'lastname': lname,
                'email': email,
                'password': hashed_password,
                'email_verified': False
            }
            
            result = users.insert_one(user_data)
            
            if result.inserted_id:
                token = generate_confirmation_token(email)
                if isinstance(token, bytes):
                    token = token.decode('utf-8')
                
                confirm_url = url_for('confirm_email', token=token, _external=True)
                try:
                    msg = Message(
                        subject="Confirm Your Email - KanFlow",
                        sender=current_app.config['MAIL_USERNAME'],
                        recipients=[email]
                    )
                    msg.html = f"""
                    <h2>Hi {fname},</h2>
                    <p>Please confirm your email by clicking the link below:</p>
                    <p><a href="{confirm_url}" style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Confirm Email</a></p>
                    <p>Or copy and paste this URL in your browser:</p>
                    <p>{confirm_url}</p>
                    <p>If you did not sign up, please ignore this message.</p>
                    """
                    
                    msg.body = f"Hi {fname},\n\nPlease confirm your email by clicking the link below:\n{confirm_url}\n\nIf you did not sign up, ignore this message."
                    mail.send(msg)
                    
                    flash('A confirmation email has been sent. Please check your inbox.', 'info')
                    return redirect(url_for('login'))
                    
                except Exception as email_error:
                    print(f"Email sending error: {email_error}")
                    flash('Registration successful, but email could not be sent. Contact support for email verification.', 'warning')
                    return redirect(url_for('login'))
            
        except Exception as e:
            print(f"Registration error: {e}")
            flash('An error occurred during registration. Please try again later.', 'error')
            return render_template('/auth/register.html')
    
    return render_template('/auth/register.html')
def auth_login():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        password = request.form['password']
        
        if not email or not password:
            flash('Email and password are required!', 'error')
            return render_template('/auth/login.html')
        
        try:
            user = users.find_one({'email': email})
            
            if user and bcrypt.check_password_hash(user['password'], password):
                if not user.get('email_verified', False):
                    flash('Please confirm your email before logging in.', 'warning')
                    return render_template('/auth/login.html')
                
                session['user_id'] = str(user['_id'])
                session['name'] = f"{user['firstname']} {user['lastname']}"
                session['fname'] = user['firstname']
                session['lname'] = user['lastname']

                session['picture'] = user.get('picture') or None

                session['email'] = user['email']
                session['role'] = user.get('role', 'user')

                next_page = request.form.get('next') or request.args.get('next')
                if next_page:
                    return redirect(next_page)
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid email or password!', 'error')
                return render_template('/auth/login.html')
                
        except Exception as e:
            print(f"Login error: {e}")
            flash('An error occurred during login. Please try again.', 'error')
            return render_template('/auth/login.html')
    
    return render_template('/auth/login.html')

def auth_logout():
    session.clear()
    return redirect(url_for('login'))