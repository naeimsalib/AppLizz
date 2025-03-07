# Example pseudo-code:

from werkzeug.security import generate_password_hash, check_password_hash
from job_app_tracker.models import User
from job_app_tracker import db

def register_user(email, password):
    hashed_pw = generate_password_hash(password)
    new_user = User(email=email, password=hashed_pw)
    db.session.add(new_user)
    db.session.commit()

def verify_credentials(email, password):
    user = User.query.filter_by(email=email).first()
    if user and check_password_hash(user.password, password):
        return user
    return None
