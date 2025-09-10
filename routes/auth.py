from flask import request, flash, render_template, redirect, url_for, session
from db import users_collection as users
from functools import wraps
from utils.auth_checker import validate_email, validate_password

def auth_register():
    if request.method == 'POST':
        fname = request.form['fname'].strip()
        lname = request.form['lname'].strip()
        email = request.form['email'].strip().lower()
        password = request['password']
        confirm_password = request['confirm_password']

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
            user_data = {
                'firstname': fname,
                'lastname': lname,
                'email': email,
                'password': password,
                'email_verified': False
            }
            
            result = users.insert_one(user_data)
            
            if result.inserted_id:
                return render_template('/auth/register.html', success=True)
            else:
                flash('Registration failed. Please try again.', 'error')
                return render_template('/auth/register.html')
            
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
            
            if user and user['password'] == password:
                session['user_id'] = str(user['_id'])
                session['name'] = f"{user['firstname']} {user['lastname']}"
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

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access the page.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

    
