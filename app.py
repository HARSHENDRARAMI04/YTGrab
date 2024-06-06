from flask import Flask, render_template, request, send_file, after_this_request
from googleapiclient.discovery import build
from pytube import YouTube
from pytube.exceptions import AgeRestrictedError
from dotenv import load_dotenv
from google.auth.exceptions import DefaultCredentialsError
from pathlib import Path
import os
import re

app = Flask(__name__)

load_dotenv()

API_KEY = os.getenv("API_KEY")

def extract_id(url):
    match = re.search(r"list=([^&]+)", url, re.IGNORECASE)
    if match:
        return match.group(1)
    else:
        return None

def get_playlist_name(playlist_id):
    try:
        youtube = build('youtube', 'v3', developerKey=API_KEY)
        playlist_response = youtube.playlists().list(
            part='snippet',
            id=playlist_id
        ).execute()
        
        if 'items' in playlist_response and len(playlist_response['items']) > 0:
            playlist_name = playlist_response['items'][0]['snippet']['title']
            return playlist_name
        else:
            return None
    except DefaultCredentialsError:
        return None

def get_playlist_items(playlist_id):
    youtube = build('youtube', 'v3', developerKey=API_KEY)
    playlist_items = []
    next_page_token = None
    while True:
        request = youtube.playlistItems().list(
            part='snippet',
            playlistId=playlist_id,
            maxResults=50,
            pageToken=next_page_token
        )
        response = request.execute()
        
        if 'items' in response:
            playlist_items.extend(response['items'])
        
        next_page_token = response.get('nextPageToken')
        if not next_page_token:
            break
    return playlist_items

def get_video_urls(playlist_id):
    youtube = build('youtube', 'v3', developerKey=API_KEY)
    video_urls = []
    next_page_token = None
    while True:
        playlist_items_response = youtube.playlistItems().list(
            part='contentDetails',
            playlistId=playlist_id,
            maxResults=50,
            pageToken=next_page_token
        ).execute()
        
        if 'items' in playlist_items_response:
            for item in playlist_items_response['items']:
                video_id = item['contentDetails']['videoId']
                video_url = f"https://www.youtube.com/watch?v={video_id}"
                video_urls.append(video_url)
        
        next_page_token = playlist_items_response.get('nextPageToken')
        if not next_page_token:
            break
    return video_urls

def download_videos(playlist_id):
    urls = get_video_urls(playlist_id)
    video_streams = []
    for each in urls:
        try:
            yt = YouTube(each)
            stream = yt.streams.get_highest_resolution()
            video_streams.append((yt.title, stream))
        except AgeRestrictedError:
            print(f"Cannot download {yt.title} as it is age restricted.")
        except Exception as e:
            print(f"An error occurred: {e}")
    return video_streams

def get_download_path():
    home = str(Path.home())
    return os.path.join(home, "Downloads")

def sanitize_filename(name):
    return re.sub(r'[<>:"/\\|?*]', '', name)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        url = request.form['url']
        playlist_id = extract_id(url)
        if not playlist_id:
            return render_template('index.html', error="Invalid URL")
        
        playlist_name = get_playlist_name(playlist_id)
        if not playlist_name:
            return render_template('index.html', error="Invalid URL")

        playlist_items = get_playlist_items(playlist_id)
        return render_template('index.html', playlist_name=playlist_name, playlist_items=playlist_items, playlist_id=playlist_id)
    
    return render_template('index.html')

@app.route('/download', methods=['POST'])
def download():
    playlist_id = request.form['playlist_id']
    video_streams = download_videos(playlist_id)
    
    download_path = get_download_path()
    downloaded_files = []

    for title, stream in video_streams:
        sanitized_title = sanitize_filename(title)
        video_path = os.path.join(download_path, f"{sanitized_title}.mp4")
        stream.download(output_path=download_path, filename=f"{sanitized_title}.mp4")
        downloaded_files.append(video_path)
    
    if downloaded_files:
        @after_this_request
        def remove_file(response):
            try:
                for file_path in downloaded_files:
                    os.remove(file_path)
            except Exception as e:
                print(f"Error removing downloaded file: {e}")
            return response
        
        # Returning the first video for the sake of example, you might want to create a zip of all files and return that.
        return send_file(downloaded_files[0], as_attachment=True, download_name=os.path.basename(downloaded_files[0]), mimetype="video/mp4")
    else:
        return render_template('index.html', error="No videos were downloaded")

@app.route('/terms')
def terms():
    return render_template('terms.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

if __name__ == '__main__':
    app.run(debug=True)
