from . import db
from flask_login import UserMixin

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

class JobApplication(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    company_name = db.Column(db.String(120))
    position_title = db.Column(db.String(120))
    status = db.Column(db.String(50))  # e.g. "SUBMITTED", "REJECTED", "ARCHIVED"
    provider_message_id = db.Column(db.String(200))  # reference to email ID
