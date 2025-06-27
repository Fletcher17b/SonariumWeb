from flask import Flask,Blueprint, render_template,request, jsonify, send_file, Response, stream_with_context,after_this_request,session,url_for
from flask_sqlalchemy import SQLAlchemy
import yt_dlp,os,time,re,json,pprint
from itsdangerous import URLSafeTimedSerializer
from flask_bcrypt import Bcrypt
from flask_mail import Message

from app.utils.spotifyhandler.spotify_apicalls import get_renderableplaylist
from app.utils.ythandler.youtubeall import normalize_youtube_url,downloader,evalUrl_source,tempserver_downloader,progress_updates
from app.utils.userregistration import generate_registration_token,send_registration_email
from app import db,mail,bcrypt
from app.models import User
from app.utils.helpers.helpers_file import email_validation,validate_user_data
from app.utils.loggin_ops import login_required
from app.utils.DBhandler.dbhandler import email_query



app = Blueprint('app', __name__)


# ------------------------------------      GET        -------------------------------------------------------------------------

@app.route('/')
def index():
    return render_template('content/index.html')

@app.route('/song')
def single_song():
    return render_template('content/song.html')

@app.route('/playlist')
def playlist():
    return render_template('content/playlist.html')

@app.route('/mp3player')
def mp3player():
    return render_template('content/player.html')

@app.route('/settings')
def settingsview():
    return render_template('content/settings.html')

@app.route('/usersettings')
def usersettingsview():
    return render_template('usersettings.html')

@app.route('/test')
def testview():
    return render_template('logging/resultpage.html')

@app.route('/register') 
def register_user():
    return render_template('logging/register.html')

@app.route('/registersuccess')
def registrationsuccesful():
    return render_template('logging/resultpage.html')

@app.route('/login')
def loggin():
   return render_template('logging/login.html')

@app.route('/admin')
def adminview():
    users = User.query.all()
    return render_template('admin/adminpage.html',users=users)

# ------------------------------------      POST        -------------------------------------------------------------------------
@app.route('/download-mp3', methods=['POST']) # nts: change name download-mp3 -> download_song
def download_mp3():
    data = request.get_json()
    #print("JSON Data:", data)
    url = data.get('url')
    title = data.get('title')
    if not url:
        return jsonify({'error': 'URL is required'}), 400
    
    normalized_url = normalize_youtube_url(url)
    try:
        success,status = downloader(normalized_url,title)
        if success:
            filename = status
            return jsonify({'message': 'Download successful', 'file': f"/download/{os.path.basename(filename)}"})
        else:
            return jsonify({'error': status}), 500
        

    except Exception as e:
        print("Error in download_mp3: "+str(e))
        return jsonify({'error': str(e)}), 500

@app.route('/getplaylist', methods=['POST'])
def get_playlist():
    """

    |   returns renderable list of songs to be displayed in front end, |
    |    direct yt-dlp implementation, spotify custom backend in spotifyhandler -> get_renderableplaylist()
    """
    data = request.get_json()
    playlist_url = data.get("url")

    if not playlist_url:
        return jsonify({"error": "No URL provided"}), 400

    source = evalUrl_source(playlist_url)
    if  source != 1 and source != 2:
        return jsonify({"error": "Unknown URL provided"}), 400


    if source == 1: # youtube
       
        try:
            ydl_opts_local = {
                 'quiet': True,  
                 'extract_flat': 'in_playlist',  
                 'noplaylist': False,
                 'force_generic_extractor': False,
                }
    
            with yt_dlp.YoutubeDL(ydl_opts_local) as ydl:
                info = ydl.extract_info(playlist_url, download=False)
                if "entries" in info:
                    videos = [{
                        "title": entry["title"],
                        "url": entry["url"],
                        "thumbnail": entry.get("thumbnail", "https://via.placeholder.com/150")
                    } for entry in info["entries"]]

                    return jsonify({"videos": videos,"source":source})
                else:
                    return jsonify({"error": "No videos found in the playlist"}), 404

        except Exception as e:
            return jsonify({"error": str(e)}), 500
        
    if source == 2: # spotify   
        try: 
            tracklist,status = get_renderableplaylist(playlist_url)

            print(status)
            if (tracklist==None or status == 429):
                return jsonify({"error": "error on API call",}), 500

            if status == 200:
                return jsonify({"videos": tracklist,"source":source}), 200

            return jsonify({"error": "error somewhere jeje",}), 500
        except Exception as e: 
            return jsonify({"error": str(e)}), 500
    
@app.route('/serverdownload', methods=['POST'])
def download_onserver():
    """

    |    Download on memory to be sent to user, no disk IOPs on server |
    |    custom logic in ythandler -> tempserver_downloader()
    """
    data = request.get_json()
    url = data.get('url')
    #print("recieved url:",url)
    if not url:
        return jsonify({'error': 'No URL provided'}), 400

    source = evalUrl_source(url)

    #print("source: ",source)

    success, result, filename = tempserver_downloader(url,source)
    if not success:
        return jsonify({"error": result}),500
    
    return send_file(result,as_attachment=True,download_name=filename,mimetype="audio/mpeg")

@app.route('/localdownload', methods=['POST'])
def download_onclient():
    """
        deprecated
    """
    data = request.get_json()
    url = data.get('url')

    if not url:
        return jsonify({'error': 'No URL provided'}), 400
    
    
    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'noplaylist': True,
            'verbose': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            direct_url = info.get("url")
            filename = f"{info.get('title')}.webm"  # Could be webm/m4a depending on source

        
        return jsonify({"direct_url": direct_url, "filename": filename})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ???    
@app.route('/proxy_audio')
def proxy_audio():
    youtube_url = request.args.get("url")

    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=False)
            direct_url = info.get("url")

        def generate():
            with request.get(direct_url, stream=True) as r:
                r.raise_for_status()
                for chunk in r.iter_content(chunk_size=8192):
                    yield chunk

        return Response(generate(), content_type="audio/webm")

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/progress', methods=['GET'])
def progress():
    def stream():
        while True:
            json_data = json.dumps(progress_updates)
            yield f"data: {json_data}\n\n"
            time.sleep(1)
    return Response(stream_with_context(stream()), content_type='text/event-stream')

# ------------------------------------      Logging ops Routes       -------------------------------------------------------------------------



@app.route('/loginuser')
def loggin_user():
    print()

@app.route('/logginenp')
def login_user():
    session.clear()

@app.route('/loggout')
def loggout():

    session.clear()
    print()

@app.route('/registeruser',methods=['POST'])
def registerUser():
    errors,user_data = validate_user_data(request.form)
    hashed_password = bcrypt.generate_password_hash(user_data.password).decode('utf-8')

    tempdata = {
        'username': user_data.username,
        'email': user_data.email,
        'password': hashed_password
    }

    print("Errors: ", errors)
    if errors:
        return jsonify({'success': False, 'errors': errors}), 400

    token = generate_registration_token(tempdata)
    send_registration_email(user_data.email, token)
    
    #user = User(username=user_data.username, useremail=user_data.email, password=hashed_password)
    #db.session.add(user)
    #db.session.commit()

    #return jsonify({'success': True, 'message': 'User registered successfully'}), 201
    return jsonify({'success': True, 'message': 'Please confirm your email to complete registration.'}), 202
    

@app.route('/confirm/<token>')
def confirm_email(token):
    s = URLSafeTimedSerializer(os.getenv('SECRET_KEY'))
    try:
        data = s.loads(token, salt='register-confirm', max_age=3600)
    except:
        return jsonify({'message':'Invalid or expired token'}), 400

    if User.query.filter_by(useremail=data['email']).first():
        return jsonify({'message':'Account already exists.'})

    new_user = User(
        username=data['username'],
        useremail=data['email'],
        password=data['password'],
    )

    db.session.add(new_user)
    db.session.commit()
#jsonify({'message': 'Account confirmed and created! You can now log in.'}), 201
    return render_template('logging/resultpage.html', username=data['username'])