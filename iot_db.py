from __future__ import print_function
from flask import Flask
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
    mac_address = db.Column(pg.MACADDR)
    friendly_name = db.Column(db.String(15))
    past_ips = db.Column(pg.ARRAY(pg.INET))
    first_connected = db.Column(db.DateTime)
    last_connected = db.Column(db.DateTime)

    devices = db.relationship('Devices', backref='client',
        lazy='dynamic')

    def __init__(self, user_id, ip_address, port, mac_address,
        friendly_name=None):
        self.user_id = user_id
        self.ip_address = ip_address
        self.past_ips = [ip_address]
        self.port = port
        self.mac_address = mac_address
        self.friendly_name = friendly_name

class Devices(db.Model):
    device_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'))
    client_id = db.Column(db.Integer, db.ForeignKey('clients.client_id'))
    module_type = db.Column(db.Integer)
    friendly_name = db.Column(db.String(20))
    ip_address = db.Column(pg.INET)
    port = db.Column(db.Integer)
    first_connected = db.Column(db.DateTime)
    last_checked = db.Column(db.DateTime)
    token = db.Column(pg.UUID)

    def __init__(self, user_id, module_type, ip_address, port, 
        friendly_name=None):
        self.user_id = user_id
        self.module_type = module_type
        self.ip_address = ip_address
        self.port = port
        self.friendly_name = friendly_name
        self.first_connected = self.last_checked = datetime.utcnow()
        self.token = str(uuid4())

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
