from flask_mail import Message
from itsdangerous import URLSafeTimedSerializer
from app import mail
from config import SECRET_KEY
import re
from app.models import User
from app.models_dir.userhandle import userhandler

''''
    User valitadion (mostly)
'''


def send_confirmation_email(user_email):
    ''''
        Unused
    '''
    token = URLSafeTimedSerializer(SECRET_KEY).dumps(user_email, salt='email-confirm')

    confirm_url = f'localhost:5000/confirm/{token}'
    msg = Message('Confirm Your Account',
                  recipients=[user_email])
    msg.body = f'Click to confirm: {confirm_url}'
    mail.send(msg)


def email_validation(email: str):
    return bool(re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email))

def validate_user_data(data):
    errors = {}
    username = data.get('username', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password', '')
    password_confirm = data.get('confirm_password', '')

    print("u:",username)
    print("e:",email)
    print("u:",password)
    print("e:",password_confirm)
    # Store valid input into a handler object
    user_data = userhandler(username, email, password, password_confirm)
    

    
    # Validation
    if not username:
        errors['username'] = 'Username is required'
    elif User.query.filter_by(username=username).first():
        errors['username'] = 'Username already exists'

    if not email:
        errors['email'] = 'Email is required' 
    if not email_validation(email):
        errors['email'] = 'Invalid email format'
    elif User.query.filter_by(useremail=email).first():
        errors['email'] = 'Email already registered'

    if not password:
        errors['password'] = 'Password is required'
    elif len(password) < 3:
        errors['password'] = 'Password must be at least 3 characters'

    if not password_confirm:
        errors['password_confirm'] = 'Please confirm your password'
    elif password != password_confirm:
        errors['password_confirm'] = 'Passwords do not match'

    return errors, user_data