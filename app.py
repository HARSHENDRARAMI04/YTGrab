import re
import os
from flask import Flask, render_template, request, redirect, url_for
from googleapiclient.discovery import build
from pytube import YouTube
from dotenv import load_dotenv
from google.auth.exceptions import DefaultCredentialsError
from pathlib import Path







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
    dir = make_folder(playlist_id)
    urls = get_video_urls(playlist_id)
    for each in urls:
        yt = YouTube(each)
        stream = yt.streams.get_highest_resolution()
        stream.download(output_path=dir)

def make_folder(playlist_id):
    home = str(Path.home())
    downloads_path = os.path.join(home, "Downloads")
    if not os.path.exists(downloads_path):
        os.makedirs(downloads_path)
    name = get_playlist_name(playlist_id)
    folder_path = os.path.join(downloads_path, name)
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    return folder_path

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
    download_videos(playlist_id)
    return redirect(url_for('index'))

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
