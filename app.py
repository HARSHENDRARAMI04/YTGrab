import io
from zipfile import ZipFile
from pytube import YouTube
from flask import send_file

def download():
    playlist_id = request.form['playlist_id']
    urls = get_video_urls(playlist_id)
    
    # Create a BytesIO buffer to hold the zip file
    zip_buffer = io.BytesIO()

    # Create a ZipFile object with the buffer
    with ZipFile(zip_buffer, 'a') as zip_file:
        for each in urls:
            yt = YouTube(each)
            stream = yt.streams.get_highest_resolution()
            
            # Download the video stream to memory
            video_buffer = io.BytesIO()
            stream.stream_to_buffer(video_buffer)
            video_buffer.seek(0)
            
            # Write the video to the zip file
            zip_file.writestr(yt.title + '.' + stream.subtype, video_buffer.getvalue())
    
    zip_buffer.seek(0)
    
    # Send the zip file to the user
    return send_file(
        zip_buffer,
        mimetype='application/zip',
        as_attachment=True,
        download_name='videos.zip'
    )
