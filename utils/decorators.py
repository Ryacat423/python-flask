from flask import request, flash, redirect, url_for, session
from functools import wraps

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access the page.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function