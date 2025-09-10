from authlib.integrations.flask_client import OAuth
from instance.api_key import *
from app import app

oauth = OAuth(app)

google = oauth.register(
    name='google',
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    server_metadata_uri = "https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs = {'scope': 'openid profile email'}
)