from flask import Flask, render_template, request, redirect, url_for, session
from routes.auth import auth_register, auth_login, auth_logout, login_required
from db import users_collection as users
from datetime import datetime

from authlib.integrations.flask_client import OAuth
from instance.api_key import *

from flask_mail import Mail, Message

app = Flask(__name__)
app.secret_key = "224ae51b_80A8"

oauth = OAuth(app)
mail = Mail(app)

google = oauth.register(
    name="google",
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = DEL_EMAIL
app.config['MAIL_PASSWORD'] = DEL_PASSWORD
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True

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

@app.route('/login/google')
def login_google():
    try:
        redirect_uri = url_for('authorize_google', _external=True)
        return google.authorize_redirect(redirect_uri)
    except Exception as e:
        app.logger.error(f"Error during login: {str(e)}")
        return f"Error occurred during login: {str(e)}", 500

@app.route('/authorize/google')
def authorize_google():
    token = google.authorize_access_token()
    
    res = google.get("https://openidconnect.googleapis.com/v1/userinfo")
    user_info = res.json()

    email = user_info.get("email")
    firstname = user_info.get("given_name")
    lastname = user_info.get("family_name")
    picture = user_info.get("picture")
    email_verified = user_info.get("email_verified", False)

    existing_user = users.find_one({"email": email})
    
    if not existing_user:
        new_user = {
            "firstname": firstname,
            "lastname": lastname,
            "email": email,
            "picture": picture,
            "email_verified": email_verified,
            "oauth_provider": "google",
            "google_id": user_info.get("sub"),
            "role": "user"
        }
        result = users.insert_one(new_user)
        user_id = result.inserted_id
    else:
        user_id = existing_user["_id"]

    session['user_id'] = str(user_id)
    session['name'] = f"{firstname} {lastname}"
    session['email'] = email
    session['role'] = existing_user.get("role", "user") if existing_user else "user"
    session['picture'] = picture

    next_page = request.args.get('next')
    if next_page:
        return redirect(next_page)
    return redirect(url_for("dashboard"))

@app.route('/dashboard')
@login_required 
def dashboard():
    user_name = session.get('name', 'User')
    user_email = session.get('email')
    
    return render_template('/main/dashboard.html', user_name=user_name, user_email=user_email)

@app.route('/projects')
@login_required
def projects():
    return render_template('/main/projects.html')

@app.context_processor
def inject_current_year():
    return {'current_year': datetime.now().year}

if __name__ == "__main__":
    app.run(debug=True)