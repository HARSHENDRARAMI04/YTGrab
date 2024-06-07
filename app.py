from flask import Flask, render_template, request, send_file, after_this_request
from googleapiclient.discovery import build
from pytube import YouTube
from pytube.exceptions import AgeRestrictedError
from dotenv import load_dotenv
from google.auth.exceptions import DefaultCredentialsError
from pathlib import Path
import os
import re
import tempfile
import zipfile

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

    # Debugging: Log extracted video URLs
    print("Extracted video URLs:", video_urls)
    
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

    # Debugging: Log video streams to be downloaded
    print("Video streams to be downloaded:", [(title, stream.url) for title, stream in video_streams])

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
    playlist_name = get_playlist_name(playlist_id)
    video_streams = download_videos(playlist_id)
    
    download_path = get_download_path()
    downloaded_files = []

    for title, stream in video_streams:
        sanitized_title = sanitize_filename(title)
        video_path = os.path.join(download_path, f"{sanitized_title}.mp4")
        
        # Check if file already exists
        if os.path.exists(video_path):
            print(f"File already exists: {video_path}")
            continue
        
        stream.download(output_path=download_path, filename=f"{sanitized_title}.mp4")
        downloaded_files.append(video_path)
    
    # Debugging: Log downloaded files
    print("Downloaded files:", downloaded_files)

    if downloaded_files:
        @after_this_request
        def remove_file(response):
            try:
                for file_path in downloaded_files:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                if os.path.exists(zip_path):
                    os.remove(zip_path)
            except Exception as e:
                print(f"Error removing downloaded file: {e}")
            return response
        
        # Create a unique temporary directory
        tmpdirname = tempfile.mkdtemp()
        sanitized_playlist_name = sanitize_filename(playlist_name)
        zip_path = os.path.join(tmpdirname, f"{sanitized_playlist_name}.zip")
        
        # Create ZIP file
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for file in downloaded_files:
                zipf.write(file, os.path.basename(file))

        return send_file(zip_path, as_attachment=True, download_name=f"{sanitized_playlist_name}.zip")
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
    app.run(host='0.0.0.0', port=5000)

