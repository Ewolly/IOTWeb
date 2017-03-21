from __future__ import print_function
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def init_app(app):
    db.init_app(app)

class users(db.Model):
    user_id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(254), unique=True)
    password = db.Column(db.String(128))

    def __init__(self, email, password):
        self.email = email
        self.password = password

    def __repr__(self):
        return '<email %r>' % self.email