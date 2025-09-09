from flask import request, flash, render_template, redirect, url_for, session
from db import users_collection as users
from datetime import datetime

def auth_register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if password != confirm_password:
            flash('Passwords do not match!', 'error')
            return render_template('/auth/register.html')
        
        if users.find_one({'email': email}):
            flash('Email already registered!', 'error')
            return render_template('/auth/register.html')
        
        user_data = {
            'name': name,
            'email': email,
            'password': password,
            'role': 'user',
            'created_at': datetime.now()
        }
        
        result = users.insert_one(user_data)
        
        if result.inserted_id:
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Registration failed. Please try again.', 'error')
    
    return render_template('/auth/register.html')

def auth_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        user = users.find_one({'email': email})
        
        if user and user['password'] == password:
            session['user_id'] = str(user['_id'])
            session['name'] = user['name']
            session['email'] = user['email']
            session['role'] = user.get('role', 'user')
            
            flash(f'Welcome back, {user["name"]}!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid email or password!', 'error')
    
    return render_template('/auth/login.html')

def auth_logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('index'))