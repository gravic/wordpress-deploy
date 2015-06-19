from app import db, User

db.create_all()

user = User(
    'admin',
    'password',
    'Admin',
    'Account'
)

user.is_admin = True

db.session.add(user)
db.session.commit()
