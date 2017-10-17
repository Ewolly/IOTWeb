from __future__ import print_function
# from flask import Flask
from flask_sqlalchemy import SQLAlchemy
# http://docs.sqlalchemy.org/en/rel_0_9/dialects/postgresql.html
from sqlalchemy import func
from sqlalchemy.dialects import postgresql as pg
from datetime import datetime
from hashlib import sha512
from uuid import uuid4

db = SQLAlchemy()

def init_app(app):
    db.init_app(app)

class Users(db.Model):
    user_id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(254), unique=True)
    password = db.Column(db.String(128))
    nonce = db.Column(db.String(8))
    creation_time = db.Column(db.DateTime)
    last_accessed = db.Column(db.DateTime)
    password_reset_time = db.Column(db.DateTime)

    devices = db.relationship('Devices', backref='user',
        lazy='dynamic')
    clients = db.relationship('Clients', backref='user',
        lazy='dynamic')

    def __init__(self, email, password):
        self.email = email
        if password is not None:
            self.password = hash_pass(email, password)
        self.creation_time = self.last_accessed = datetime.utcnow()

class Clients(db.Model):
    client_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'))
    ip_address = db.Column(pg.INET)
    port = db.Column(db.Integer)
    friendly_name = db.Column(db.String(15))
    first_connected = db.Column(db.DateTime)
    last_connected = db.Column(db.DateTime)
    local_ip = db.Column(pg.INET)
    local_port = db.Column(db.Integer)

    devices = db.relationship('Devices', backref='client',
        lazy='dynamic')

    def __init__(self, user_id, ip_address, friendly_name):
        self.user_id = user_id
        self.ip_address = ip_address
        self.friendly_name = friendly_name
        self.first_connected = self.last_connected = datetime.utcnow()

class Devices(db.Model):
    device_id = db.Column(db.Integer,
        primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'))
    client_id = db.Column(db.Integer, db.ForeignKey('clients.client_id'))
    module_type = db.Column(db.Integer)
    friendly_name = db.Column(db.String(20))
    ip_address = db.Column(pg.INET)
    port = db.Column(db.Integer)
    first_connected = db.Column(db.DateTime)
    last_checked = db.Column(db.DateTime)
    token = db.Column(pg.UUID)
    current_consumption = db.Column(db.Numeric)
    plug_status = db.Column(db.Boolean)
    connecting = db.Column(db.Integer)
    local_ip = db.Column(pg.INET)
    local_port = db.Column(db.Integer)

    def __init__(self, user_id, module_type, friendly_name=None):
        self.user_id = user_id
        self.module_type = module_type
        self.ip_address = None
        self.port = None
        self.friendly_name = friendly_name
        self.plug_status = False
        self.first_connected = self.last_checked = datetime.utcnow()
        self.token = str(uuid4())
        self.connecting = 0

class Infrared(db.Model):
    device_id = db.Column(db.Integer, primary_key=True)
    buttons = db.Column(db.JSON)
    feedback = db.Column(db.JSON)
    repeater = db.Column(db.Boolean)
    learning = db.Column(db.Integer)

    def __init__(self, device_id):
        self.device_id = device_id
        self.feedback = [
            {'enabled': False},
            {'enabled': False},
            {'enabled': False},
            {'enabled': False},
        ]
        self.learning = -1
        self.repeater = False

def add_to_db(db_object):
    db.session.add(db_object)

def drop_from_db(db_object):
    db.session.delete(db_object)

def update_db():
    db.session.commit()

def hash_pass(email, password):
    return sha512(email+password).hexdigest()

def get_user(email):
    return Users.query.filter(func.lower(Users.email) == email.lower()).first()
