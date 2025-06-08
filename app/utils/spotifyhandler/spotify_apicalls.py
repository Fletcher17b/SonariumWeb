from app.resources.credentials.spotifyapi_creds.apicreds import SPOTIFY_CLIENT_ID,SPOTIFY_CLIENT_SECRET

import requests,re,spotipy,math,itertools,time
from pprint import pprint
from spotipy.oauth2 import SpotifyClientCredentials
from urllib.parse import urlparse


SPOTIFY_TOKEN_URL = 'https://accounts.spotify.com/api/token'
SPOTIFY_API_BASE = 'https://api.spotify.com/v1'


# track = 1, album = 2. playlist = 3
# returns query and query type
def spotifyurl_parse(url:str):
    """
    Parses a Spotify URL and returns (spotify_id, url_type)

    """
    type_map = {
        'track': 1,
        'album': 2,
        'playlist': 3,
    }

    url = url.strip()
    parsed = urlparse(url)

    parts = parsed.path.strip('/').split('/')
    if len(parts) != 2:
        return None, None

    url_type_str, spotify_id = parts
    
    url_type = type_map.get(url_type_str)
    if not url_type:
        return None, None
    return spotify_id, url_type

def get_playlistLenght(response_json):
    return response_json.get("tracks", {}).get("total", 0)

def get_playlistitems(url:str):

    sp = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials(client_id=SPOTIFY_CLIENT_ID,client_secret=SPOTIFY_CLIENT_SECRET))

    formatted_url = 'spotify:playlist:'+url

    while True:
        response = sp.playlist_items(formatted_url,offset=0,fields='items.track.id,',additional_types=['track'])

        if len(response['items']) == 0:
            break

        pprint(response['items'])
        offset = offset + len(response['items'])
        print(offset, "/", response['total'])

def parse_playlist_metadata(response_json):
    """ 
        Takes a response.json object and
        parses the raw api query result into ordered dictionaries  
    """
    """
     playlist_metada = {
        "playlistName": name,
        "playlistLenght":lenght,
        "playlistAuthor":author,
        "playlistThumbnail":thumbnail,
        "tracklist": tracklist -> list of song dicts
    }

    song_dict = {
        "song_name": name,
        "artists":artists,
        "thumbnail":thumbnail,
        "duration":duration,
        "album":album,
        "url": track_url
    }
 
    """
    playlist_metadata = {
        "playlistName": response_json.get("name"),
        "playlistLenght": response_json.get("tracks", {}).get("total", 0),
        "playlistAuthor": response_json.get("owner", {}).get("display_name"),
        "playlistThumbnail": None,
        "tracklist": []
    }

    images = response_json.get("images", [])
    if images:
        playlist_metadata["playlistThumbnail"] = images[0].get("url")

    for item in response_json.get("tracks", {}).get("items", []):
        track = item.get("track")
        if not track:
            continue

        thumbnail = None
        album_images = track.get("album", {}).get("images", [])
        if album_images:
            thumbnail = album_images[1].get("url") 

        song_dict = {
            "song_name": track.get("name"),
            "artists": [artist.get("name") for artist in track.get("artists", [])],
            "thumbnail": thumbnail,
            "duration": track.get("duration_ms", 0) // 1000,  
            "album": track.get("album", {}).get("name"),
            "url":track.get("external_urls",{}).get("spotify")
        }

        playlist_metadata["tracklist"].append(song_dict)

    return playlist_metadata

def title_parse(title:str,artists:list):
    return ' , '.join(artists) + ' - ' + title

def playlistrender_parse(response_json):
    """ 
        Takes a response.json object and
        parses the raw api query result into render format foe playlist view 
    """

    tracklist = []

    items = response_json.get("items", [])
    if "tracks" in response_json:
        items = response_json["tracks"].get("items", [])

    for item in items:
        track = item.get("track")
        if not track:
            continue

        thumbnail = None
        album_images = track.get("album", {}).get("images", [])
        if album_images:
            thumbnail = album_images[1].get("url") if len(album_images) > 1 else album_images[0].get("url")

        title = title_parse(track.get("name"), [artist.get("name") for artist in track.get("artists", [])])
        song_dict = {
            "title": title,
            "thumbnail": thumbnail,
            "url": track.get("external_urls", {}).get("spotify")
        }

        tracklist.append(song_dict)

    return tracklist


def get_access_token():
    client_id = SPOTIFY_CLIENT_ID
    client_secret = SPOTIFY_CLIENT_SECRET

    response = requests.post(SPOTIFY_TOKEN_URL, {
        'grant_type': 'client_credentials',
        'client_id': client_id,
        'client_secret': client_secret,
    })

    response.raise_for_status()
    return response.json()['access_token']

def get_spotifyplaylist(url):
    token = get_access_token()  
    headers = {'Authorization': f'Bearer {token}'}

    playlist_id, url_type = spotifyurl_parse(url)

    if url_type != 3 and url_type != 2 :
        return {"error": "URL provided is not for a playlist"}, 500

    response = requests.get(f'{SPOTIFY_API_BASE}/playlists/{playlist_id}', headers=headers)
    if response.status_code != 200:
        return response.json(), response.status_code  

    if response.status_code == 200:
        data = parse_playlist_metadata(response.json())
        pprint(data)

    return data,200


def get_renderableplaylist(url):
    token = get_access_token()  
    headers = {'Authorization': f'Bearer {token}'}

    playlist_id, url_type = spotifyurl_parse(url)

    if url_type != 3 and url_type != 2 :
        return {"error": "URL provided is not for a playlist"}, 500

    response = requests.get(f'{SPOTIFY_API_BASE}/playlists/{playlist_id}', headers=headers)
    playlistlenght_query_result = response.json().get("tracks", {}).get("total", 0)
    print("leghnt: ",playlistlenght_query_result) 
    
    #nts: implement lazy loading and paginated requests 
    #offset = int(0)
    #if (playlistlenght_query_result > 100):
    #    full_lenght_renderlist = []
    #    for i in range(0,int(math.ceil(playlistlenght_query_result / 100.0)* 100) ,100):
    #        response = requests.get(f'{SPOTIFY_API_BASE}/playlists/{playlist_id}/tracks?limit=100&offset={offset}', headers=headers)
    #        print("code: ",response.status_code)
    #        if (response.status_code == 429):
    #            return None,response.status_code
    #        
    #        full_lenght_renderlist.append(playlistrender_parse(response.json()))
    #        offset= offset+100 
    #        time.sleep(1)
    #    
    #    complete_list =  [item for sublist in full_lenght_renderlist for item in sublist]
    #    print("complete_list:")
    #    pprint(complete_list)
    #    return complete_list,200

    if response.status_code != 200:
        return response.json(), response.status_code  

    if response.status_code == 200:
        data = playlistrender_parse(response.json())
        #pprint(data)

    return data,200 


#playlistlenght_query = requests.get(f'{SPOTIFY_API_BASE}/playlists/{playlist_id}', headers=headers)
    """"""

    