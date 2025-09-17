from flask import Flask, render_template, request, redirect, url_for, session, flash
from routes.auth import auth_register, auth_login, auth_logout
from routes.projects import *
from utils.token import confirm_token
from utils.decorators import login_required

from authlib.integrations.flask_client import OAuth
from instance.api_key import *
from extensions.mail import mail
from db import users_collection as users
from datetime import datetime

app = Flask(__name__)
app.secret_key = SECRET_KEY

oauth = OAuth(app)

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USERNAME'] = DEL_EMAIL
app.config['MAIL_PASSWORD'] = DEL_PASSWORD
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_DEFAULT_SENDER'] = DEL_EMAIL
app.config['MAIL_DEBUG'] = True 

mail.init_app(app)

google = oauth.register(
    name="google",
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

# ====== LANDING & AUTH ROUTES ======
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

@app.route('/confirm/<token>')
def confirm_email(token):
    try:
        email = confirm_token(token)
        if not email:
            return redirect(url_for('login'))
            
    except Exception as e:
        return redirect(url_for('login'))
    user = users.find_one({'email': email})
    
    if user:        
        if not user.get('email_verified', False):
            result = users.update_one(
                {'email': email}, 
                {'$set': {'email_verified': True}}
            )
            
            if result.modified_count > 0:
                flash('Email confirmed successfully! You can now log in.', 'success')
            else:
                flash('Error confirming email. Please try again.', 'error')
        else:
            flash('Account already confirmed. Please log in.', 'info')
    else:
        flash('User not found.', 'error')

    print("🔄 Redirecting to login page")
    return redirect(url_for('login'))
    
# ====== END OF LANDING & AUTH ROUTES ======

# ====== MAIN APPLICATION ROUTES ======
@app.route('/dashboard')
@login_required 
def dashboard():    
    return projects_list('dashboard')

# ====== PROJECT ROUTES ======

@app.route('/projects')
@login_required
def projects():
    return projects_list('projects')

@app.route('/projects/create', methods=['GET', 'POST'])
@login_required
def create_project():
    return project_create()

@app.route('/projects/<project_id>', methods=['GET'])
@login_required
def view_project(project_id):
    return project_view(project_id)


@app.route('/projects/<project_id>/add-member', methods=['GET', 'POST'])
@login_required
def add_member_to_project(project_id):
    return project_add_member(project_id)

@app.route('/projects/<project_id>/columns/create', methods=['POST'])
@login_required
def create_column(project_id):
    return column_create(project_id)


# ====== END OF PROJECT ROUTES ======

@app.context_processor
def inject_current_year():
    return {'current_year': datetime.now().year}

@app.context_processor
def inject_user():
    raw_profile = session.get('picture')

    if raw_profile:
        if raw_profile.startswith("http"):
            profile_url = raw_profile
        else:
            profile_url = url_for('static', filename=f'uploads/{raw_profile}')
    else:
        profile_url = url_for('static', filename='images/boy.png')

    return dict(
        user_name=session.get('name', 'User'),
        profile=profile_url,
        user_email=session.get('email')
    )

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True)

