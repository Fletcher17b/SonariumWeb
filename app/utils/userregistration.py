from itsdangerous import URLSafeTimedSerializer
from flask import url_for
from app import mail
from flask_mail import Message

import os




def generate_registration_token(data):
    s = URLSafeTimedSerializer(os.getenv('SECRET_KEY'))
    return s.dumps(data, salt='register-confirm')

def send_registration_email(email, token):
    confirm_url = url_for('app.confirm_email', token=token, _external=True)
    html = f'''
        <p>Hey! Click the link to confirm your registration :D</p>

        <a href="{confirm_url}">Link </a>
    '''
    msg = Message('Confirm Your Account', recipients=[email])
    msg.html = html
    mail.send(msg)