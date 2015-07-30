import os
import re
import sqlite3
from flask import Flask, redirect, render_template, Response, request, session, url_for
from flask.ext.sqlalchemy import SQLAlchemy
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from celery import Celery
from compiler import Compiler
import settings as SETTINGS

app = Flask(__name__)
app.config.from_object(__name__)

app.config.update(dict(
    SQLALCHEMY_DATABASE_URI='sqlite:///db/deploy.db',
    USERNAME=SETTINGS.DB_USERNAME,
    PASSWORD=SETTINGS.DB_PASSWORD,
    SECRET_KEY=SETTINGS.SECRET_KEY,
    CELERY_BROKER_URL=SETTINGS.CELERY_BROKER_URL,
    CELERY_RESULT_BACKEND=SETTINGS.CELERY_RESULT_BACKEND,
    DEBUG=True
))

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), unique=True)
    password = db.Column(db.String(255), unique=True)
    first_name = db.Column(db.String(255), unique=True)
    last_name = db.Column(db.String(255), unique=True)
    is_admin = db.Column(db.Boolean)
    permissions = db.relationship('Site', backref='site', secondary='permissions', lazy='dynamic')

    def __init__(self, username, password, first_name, last_name):
        self.username = generate_slug(username)
        self.password = generate_password_hash(password)
        self.first_name = first_name
        self.last_name = last_name
        self.is_admin = False

    def can_access(self, slug):
        return any(slug == site.slug for site in self.permissions)

    def __repr__(self):
        return '<User %r>' % self.username

class Site(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(255), unique=True)
    name = db.Column(db.String(255), unique=True)
    testing_url = db.Column(db.String(255), unique=False)
    production_url = db.Column(db.String(255), unique=False)
    theme_url = db.Column(db.String(255), unique=False)
    production_server = db.Column(db.String(255), unique=False)
    production_dir = db.Column(db.String(255), unique=False)

    def __init__(self, name, testing_url, production_url, theme_url, production_server, production_dir):
        self.slug = generate_slug(name)
        self.name = name
        self.testing_url = testing_url
        self.production_url = production_url
        self.theme_url = theme_url
        self.production_server = production_server
        self.production_dir = production_dir

    def __repr__(self):
        return '<Site %r>' % self.slug

permissions = db.Table('permissions',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('site_id', db.Integer, db.ForeignKey('site.id'))
)

def generate_slug(string):
    string = re.sub(r'\s', '-', string)
    string = re.sub(r'[^A-Za-z0-9\-]', '', string)
    string = re.sub(r'--', '-', string)

    return string.lower()

def make_celery(app):
    celery = Celery('tasks', broker=app.config['CELERY_BROKER_URL'])
    celery.conf.update(app.config)
    TaskBase = celery.Task
    class ContextTask(TaskBase):
        abstract = True
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)
    celery.Task = ContextTask
    return celery

celery = make_celery(app)

import tasks

def get_authed_user():
    return User.query.filter_by(username=session.get('username')).first()

def authorize(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('username'):
            return redirect(url_for('login'))

        return f(*args, **kwargs)

    return decorated

def admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not get_authed_user().is_admin:
            return redirect(request.headers['Referer'])

        return f(*args, **kwargs)

    return decorated

active_tasks = dict()

@app.route('/')
@authorize
def index():
    sites = Site.query.all()

    archives = dict()

    for site in sites:
        archive_dir = os.path.join('./dist/archive/', site.slug)
        if not os.path.exists(archive_dir):
            continue
        site_archives = [f for f in os.listdir(archive_dir) if os.path.isfile(os.path.join(archive_dir, f))]
        site_archives.sort()
        archives[site.slug] = site_archives

    completed = []

    for site, task in active_tasks.iteritems():
        if task.ready():
            completed.append(site)

    for task in completed:
        active_tasks.pop(task)

    return render_template('index.html', title='Home', authed_user=get_authed_user(), sites=sites, tasks=active_tasks, archives=archives)

@app.errorhandler(404)
def error_404(error):
    return render_template('errors/404.html', title='404'), 404

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if not user is None and check_password_hash(user.password, password):
            session['username'] = user.username

            return redirect(url_for('index'))
        else:
            return redirect(url_for('login'))

    return render_template('login.html', title='Login')

@app.route('/logout')
def logout():
    session.pop('username', None)

    return redirect(url_for('login'))

@app.route('/users')
@authorize
def users():
    users = User.query.all()

    return render_template('users/users.html', title='Users', authed_user=get_authed_user(), users=users)

@app.route('/users/add', methods=['GET', 'POST'])
@authorize
@admin
def users_add():
    sites = Site.query.all()

    if request.method == 'POST':
        user = User(
            request.form['username'],
            request.form['password'],
            request.form['first_name'],
            request.form['last_name']
        )

        for site in sites:
            key = 'site_{0}'.format(site.slug)

            if request.form.has_key(key):
                user.permissions.extend([site for site in sites if key.replace('site_', '') == site.slug])

        db.session.add(user)
        db.session.commit()

        return redirect(url_for('users'))

    return render_template('users/add.html', title='Add User', sites=sites)

@app.route('/users/<string:username>/edit', methods=['GET', 'POST'])
@authorize
def users_edit(username):
    user = User.query.filter_by(username=username).first()
    sites = Site.query.all()

    placeholder_password = '********'

    if request.method == 'POST':
        user.username = generate_slug(request.form['username'])

        if not request.form['password'] == placeholder_password:
            user.password = generate_password_hash(request.form['password'])

        user.first_name = request.form['first_name']
        user.last_name = request.form['last_name']
        user.permissions = []

        for site in sites:
            key = 'site_{0}'.format(site.slug)

            if request.form.has_key(key):
                user.permissions.extend([site for site in sites if key.replace('site_', '') == site.slug])

        db.session.commit()

        return redirect(url_for('users'))

    return render_template('users/edit.html', title='Edit User', user=user, placeholder_password=placeholder_password, sites=sites)

@app.route('/users/<string:username>/delete')
@authorize
@admin
def users_delete(username):
    user = User.query.filter_by(username=username).first()

    db.session.delete(user)
    db.session.commit()

    return redirect(url_for('users'))

@app.route('/sites')
@authorize
def sites():
    sites = Site.query.all()

    return render_template('sites/sites.html', title='Sites', authed_user=get_authed_user(), sites=sites)

@app.route('/sites/add', methods=['GET', 'POST'])
@authorize
@admin
def sites_add():
    if request.method == 'POST':
        site = Site(
            request.form['name'],
            request.form['testing_url'],
            request.form['production_url'],
            request.form['theme_url'],
            request.form['production_server'],
            request.form['production_dir']
        )

        db.session.add(site)
        db.session.commit()

        return redirect(url_for('sites'))

    return render_template('sites/add.html', title='Add Site')

@app.route('/sites/<string:slug>/edit', methods=['GET', 'POST'])
@authorize
def sites_edit(slug):
    site = Site.query.filter_by(slug=slug).first()

    if request.method == 'POST':
        site.name = request.form['name']
        site.slug = generate_slug(request.form['name'])
        site.testing_url = request.form['testing_url']
        site.production_url = request.form['production_url']
        site.theme_url = request.form['theme_url']
        site.production_server = request.form['production_server']
        site.production_dir = request.form['production_dir']

        db.session.commit()

        return redirect(url_for('sites'))

    return render_template('sites/edit.html', title='Edit Site', site=site)

@app.route('/sites/<string:slug>/delete')
@authorize
@admin
def sites_delete(slug):
    site = Site.query.filter_by(slug=slug).first()

    db.session.delete(site)
    db.session.commit()

    return redirect(url_for('sites'))

@app.route('/sites/<string:slug>/deploy')
@authorize
def sites_deploy(slug):
    site = Site.query.filter_by(slug=slug).first()

    result = tasks.deploy.delay(site.slug, site.testing_url, site.production_url, site.theme_url, site.production_server, site.production_dir)

    active_tasks[slug] = result

    return redirect(url_for('index'))

@app.route('/sites/<string:slug>/restore', methods=['GET', 'POST'])
@authorize
def sites_restore(slug):
    site = Site.query.filter_by(slug=slug).first()

    archives = []

    archive_dir = os.path.join('./dist/archive/', site.slug)

    if not os.path.exists(archive_dir):
        return redirect(url_for('index'))

    archives = [f for f in os.listdir(archive_dir) if os.path.isfile(os.path.join(archive_dir, f))]
    archives.sort()

    if request.method == 'POST':
        archive = request.form['archive']

        result = tasks.restore.delay(site.slug, archive, site.production_server, site.production_dir)

        return redirect(url_for('index'))

    return render_template('sites/restore.html', title='Restore Site', site=site, archives=archives)

if __name__ == '__main__':
    app.run(host='0.0.0.0')
