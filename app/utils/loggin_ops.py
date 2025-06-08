from flask import redirect, session
from functools import wraps



def login_required(f):
    """
    Decorate routes to require login.
    Thanks Harvad and CS50!
    https://flask.palletsprojects.com/en/latest/patterns/viewdecorators/
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated_function


def login():
    print()

def logout():
    print()

def register_user():
    print()

def update_user():
    print()

def userscookie_upload():
    print()

def usercookie_update():
    print()

def userqueue_update():
    print()

def usercache_update():
    print()