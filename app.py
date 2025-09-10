from flask import Flask, render_template, request, redirect, url_for, session
from routes.auth import auth_register, auth_login, auth_logout, login_required

from datetime import datetime
app = Flask(__name__)
app.secret_key = "your-secret-key"

@app.route('/')
def index():
    return render_template('index.html', current_year = datetime.now().year)

@app.route('/register', methods=['GET', 'POST'])
def register():
    return auth_register()

@app.route('/login', methods=['GET', 'POST'])
def login():
    return auth_login()

@app.route('/logout')
def logout():
    return auth_logout() 

@app.route('/dashboard')
@login_required 
def dashboard():
    user_name = session.get('name', 'User')
    user_email = session.get('email')
    
    return render_template('/main/dashboard.html', user_name=user_name, user_email=user_email)

@app.context_processor
def inject_current_year():
    return {'current_year': datetime.now().year}

if __name__ == "__main__":
    app.run(debug=True)