import yt_dlp,os,shutil,threading, queue,time,re,json,uuid,subprocess,spotdl,imageio_ffmpeg
from io import BytesIO
from spotdl.utils.spotify import SpotifyClient
from spotdl.utils.search import parse_query
from spotdl.types.song import Song as song
from spotdl.utils.config import DEFAULT_CONFIG

from app.utils.spotifyhandler.spotify_apicalls import get_spotifyplaylist,get_renderableplaylist

from app.resources.credentials.spotifyapi_creds.apicreds import SPOTIFY_CLIENT_ID,SPOTIFY_CLIENT_SECRET


# --------------Utils---------------------------------- -------------------------------------------------------------------------

DOWNLOAD_FOLDER = 'downloads'
TEMP_FOLDER = 'temp'
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

#------------- Paths ---------------
base_dir = os.path.dirname(os.path.abspath(__file__))

cookies_dir = os.path.abspath(
    os.path.join(base_dir, '..', '..','..', 'resources', 'credentials', 'dev_cookies')
)

cookies_path = os.path.join(cookies_dir, 'cookies.txt')
source_path = os.path.join(cookies_dir, 'cookiesmain.txt')
#------------------------------------

ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
os.environ['PATH'] = os.path.dirname(ffmpeg_path) + os.pathsep + os.environ['PATH']


download_queue = queue.Queue() 
is_downloading = False  
queue_lock = threading.Lock()
progress_updates = {}

# Caches Spotfity - Youtube search results and matches, not songs
spotify_youtube_cache = {}


SpotifyClient.init(
             client_id=SPOTIFY_CLIENT_ID,
             client_secret=SPOTIFY_CLIENT_SECRET,
             user_auth=False,
            )

# ------------------------------------ -------------------------------------------------------------------------


def evalUrl_source(url):
    youtube_pattern = re.compile(r'(https?://)?(www\.)?(youtube\.com|youtu\.be)/((watch\?v=[\w-]+(&list=[\w-]+)?)|(playlist\?list=[\w-]+)|([\w-]+))')
    spotify_pattern = re.compile(r'(https?://)?(open\.)?spotify\.com/(playlist|track)/[a-zA-Z0-9]+')

    if youtube_pattern.search(url):
        return 1
    if spotify_pattern.search(url):
        return 2
    else:
        return 0


# nts: this implementation is really shitty as it calls to spotify API fucking Twice, one to get and rennder each song of the playlist and then another for each downloaded song
def getYTurl(spot_url):
    query_result = parse_query(spot_url)
    print("query result: ",query_result)
    if not query_result or not isinstance(query_result, list) or len(query_result) == 0:
        raise Exception("Failed to parse Spotify URL.")
    
    song = query_result[0] 
    print("Song metadata: ",song)
    artist = song.artist.lower()
    search_query = f"{song.name} {song.artist} audio"

    ydl_opts = {
        'quiet': True,
        'skip_download': True,
        'format': 'bestaudio/best',
        'noplaylist': True,
        'default_search': 'ytsearch',
        'cachedir': False
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch5:{search_query}", download=False)
            if 'entries' not in info or not info['entries']:
                raise Exception("No search results found on YouTube.")

            target_duration = song.duration.total_seconds() if hasattr(song.duration, 'total_seconds') else song.duration
            best_match = None
            best_diff = float("inf")

            for entry in info['entries']:
                if not entry or not entry.get("duration"):
                    continue

                title = entry.get("title", "").lower()
                duration = entry["duration"]
                uploader = entry.get("uploader", "").lower()
                diff = abs(duration - target_duration)

                print(f"Checking: {entry['title']} by {uploader} ({duration}s)")

                # Highest priority: from official artist channel
                if (artist in uploader or f"{artist} - topic" in uploader) and diff <= 7:
                    return entry["webpage_url"]

                # Second priority: good duration + official-looking
                if diff <= 7 and any(tag in uploader for tag in ["vevo", "- topic"]) and artist in uploader:
                    return entry["webpage_url"]

                # Third: best match by duration and title content
                if diff < best_diff:
                    if not any(term in title for term in ["live", "cover", "remix", "instrumental"]):
                        best_match = entry
                        best_diff = diff

            return best_match['webpage_url'] if best_match else info['entries'][0]['webpage_url']

    except Exception as e:
        raise Exception(f"YouTube search failed: {e}")


# temporary server download: Downloads to song to RAM,processes it with ffmpeg to mp3 then 
# returns three values: 
#               - Boolean indicading operation success
#               - the file loaded in memory or the error on failure
#               - a string with the filename in format = "name.mp3"
# prefered method
def tempserver_downloader(url,source):

    if source == 1:
        try:
            ydl_opts = {
                'format': 'bestaudio/best',
                'quiet': True,
                'verbose': True,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                audio_url = info["url"]
                title = info.get("title", "audio")

            ffmpeg_cmd = [
                ffmpeg_path,
                "-i", audio_url,
                "-vn", "-f", "mp3",
                "-ab", "192k",
                "-ar", "44100",
                "-hide_banner",
                "-loglevel", "error",
                "pipe:1"
            ]

            process = subprocess.Popen(
                ffmpeg_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            mp3_data, error = process.communicate()

            if process.returncode != 0:
                return False, error.decode("utf-8"), None

            memory_file = BytesIO(mp3_data)
            memory_file.seek(0)

            return True, memory_file, f"{title}.mp3"

        except Exception as e:
            return False, str(e), None
    elif source == 2:
        try:
            
           

            
            return False,None,None
        except Exception as e:
            return False, str(e), None
    else:
        return False,None,None



# secondary method
def downloader(url,title):
    # clasic downloader, just downloads a single song to server 
    ydl_opts = {
            'format': 'bestaudio/best',
            'verbose': True,
            'ffmpeg_location': ffmpeg_path,
            'postprocessors': [{
               'key': 'FFmpegExtractAudio',
               'preferredcodec': 'mp3',
               'preferredquality': '192',
            }],
            'outtmpl': f"{DOWNLOAD_FOLDER}/%(title)s.%(ext)s",
            'cookiefile': cookies_path,
            'progress_hooks': [progress_hook]
    }

    try:
        shutil.copy(source_path, cookies_path)

        # ytlp_opts defined globally in line 20
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info).replace(info['ext'], 'mp3')
            progress_updates[title] = "Completed"
        return True,filename
    except Exception as e:
        print("Error in downloader: "+str(e))
        return False,"error: "+str(e)

def normalize_youtube_url(url):
    standard_pattern = r"(?:https?:\/\/)?(?:www\.)?youtube\.com\/watch\?v=([^&#]+)(?:&list=([^&#]+))?"
    short_pattern = r"(?:https?:\/\/)?youtu\.be\/([^?&#]+)(?:\?list=([^&#]+))?"
    
    match = re.match(standard_pattern, url) or re.match(short_pattern, url)
    
    if match:
        video_id = match.group(1)
        playlist_id = match.group(2)
        new_url = f"https://www.youtube.com/watch?v={video_id}"
        if playlist_id:
            new_url += f"&list={playlist_id}"
        return new_url
    
    # Return the original if it doesn't match any pattern
    return url

# -------------- Queue Implementations -----------------------------------------------------------------------------------------------------------

def process_queue():
    global is_downloading
    with queue_lock:
        if is_downloading:
            return
        is_downloading = True

    while not download_queue.empty():
        video = download_queue.get()
        url = video.get("url")
        title = video.get("title", "Queued Video")

        progress_updates[title] = "0%"
        success, status = downloader(url, title)
        if success:
            print(f"Downloaded: {title} -> {status}")
        else:
            print(f"Failed to download: {title} -> {status}")

        download_queue.task_done()
        progress_updates[title] = "Completed" if success else f"Failed: {status}"

    with queue_lock:
        is_downloading = False


def progress_hook(d):
    title = d.get('info_dict', {}).get('title', 'Unknown Video')
    if d['status'] == 'downloading':
        percentage = d['_percent_str'].strip()
        progress_updates[title] = percentage
    elif d['status'] == 'finished':
        progress_updates[title] = "Completed"
    print(progress_updates)


