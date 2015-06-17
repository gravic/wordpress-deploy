import re
import sqlite3
from flask import Flask, redirect, render_template, request, url_for
from flask.ext.sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config.from_object(__name__)

app.config.update(dict(
    SQLALCHEMY_DATABASE_URI='sqlite:///db/deploy.db',
    USERNAME='',
    PASSWORD='',
    DEBUG=True
))

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), unique=True)
    password = db.Column(db.String(255), unique=True)
    first_name = db.Column(db.String(255), unique=True)
    last_name = db.Column(db.String(255), unique=True)

    def __init__(self, username, password, first_name, last_name):
        self.username = username
        self.password = generate_password_hash(password)
        self.first_name = first_name
        self.last_name = last_name

    def __repr__(self):
        return '<User %r>' % self.username

class Site(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(255), unique=True)
    name = db.Column(db.String(255), unique=True)
    testing = db.Column(db.String(255), unique=False)
    production = db.Column(db.String(255), unique=False)

    def __init__(self, name, testing, production):
        self.slug = generate_slug(name)
        self.name = name
        self.testing = testing
        self.production = production

    def __repr__(self):
        return '<Site %r>' % self.slug

def generate_slug(string):
    string = re.sub(r'\s', '-', string)
    string = re.sub(r'[^A-Za-z0-9\-]', '', string)
    string = re.sub(r'--', '-', string)

    return string.lower()

@app.route('/')
def index():
    return render_template('index.html', title='Home')

@app.errorhandler(404)
def error_404(error):
    return render_template('errors/404.html'), 404

@app.route('/login')
def login():
    return render_template('login.html', title='Login')

@app.route('/users')
def users():
    users = User.query.all()

    return render_template('users/users.html', title='Users', users=users)

@app.route('/users/add', methods=['GET', 'POST'])
def users_add():
    if request.method == 'POST':
        user = User(
            request.form['username'],
            request.form['password'],
            request.form['first_name'],
            request.form['last_name']
        )

        db.session.add(user)
        db.session.commit()

        return redirect(url_for('users'))

    return render_template('users/add.html')

@app.route('/users/<string:username>/edit', methods=['GET', 'POST'])
def users_edit(username):
    user = User.query.filter_by(username=username).first()

    return render_template('users/edit.html', title='', user=user)

@app.route('/sites')
def sites():
    sites = Site.query.all()

    return render_template('sites/sites.html', title='Sites', sites=sites)

@app.route('/sites/add', methods=['GET', 'POST'])
def sites_add():
    if request.method == 'POST':
        site = Site(
            request.form['name'],
            request.form['testing'],
            request.form['production']
        )

        db.session.add(site)
        db.session.commit()

        return redirect(url_for('sites'))

    return render_template('sites/add.html')

@app.route('/sites/<string:slug>/edit', methods=['GET', 'POST'])
def sites_edit(slug):
    site = Site.query.filter_by(slug=slug).first()

    if request.method == 'POST':
        site.name = request.form['name']
        site.testing = request.form['testing']
        site.production = request.form['production']

        db.session.commit()

        return redirect(url_for('sites'))

    return render_template('sites/edit.html', title='', site=site)

if __name__ == '__main__':
    app.run()
