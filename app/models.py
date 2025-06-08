from app import db
import uuid
from datetime import datetime


class User(db.Model):
    """ 
    db  2
    """
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    
    # Basic info
    username = db.Column(db.String(80), unique=True, nullable=False)
    userid = db.Column(db.String(8), unique=True, default=lambda: str(uuid.uuid4().int)[:8])
    password = db.Column(db.String(256), nullable=False) 

    # Permissions and grade
    userperms = db.Column(db.Integer, default=1)  # 1 = user, 2 = superuser
    usergrade = db.Column(db.String(10), default="free")  # "free" or "prem"

    # Cookies
    user_cookies = db.Column(db.Text, nullable=True)  # Store as raw string or JSON blob

    # Histories
    yt_download_history = db.Column(db.JSON, default=list)  # List of YouTube downloads
    sp_download_history = db.Column(db.JSON, default=list)  # List of Spotify downloads

    yt_playlist_requests = db.Column(db.JSON, default=list)
    sp_playlist_requests = db.Column(db.JSON, default=list)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

   
    user_queue = db.Column(db.JSON, default=list)
    #user_cache = db.Column(db.JSON, default=dict)
    #usage_dashboard = db.Column(db.JSON, default=dict)

    def __repr__(self):
        return f"<User {self.username} ({self.userid})>"
    

class Song(db.Model):
    __tablename__ = 'songs' 
    id = db.Column(db.Integer, primary_key=True)

    

    def __repr__(self):
        return f"<Song {self.username} ({self.userid})>"