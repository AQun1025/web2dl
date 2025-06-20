from flask import Flask, render_template, request, send_file
import yt_dlp
import os
import uuid
import subprocess
import shutil
import re

app = Flask(__name__)
DOWNLOAD_DIR = os.path.join(os.getcwd(), 'downloads')
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def clean_download_folder():
    if os.path.exists(DOWNLOAD_DIR):
        for f in os.listdir(DOWNLOAD_DIR):
            try:
                os.remove(os.path.join(DOWNLOAD_DIR, f))
            except:
                pass

def convert_to_safe_mp4(input_file):
    output_file = input_file.rsplit('.', 1)[0] + '_converted.mp4'
    command = [
        'ffmpeg', '-y',
        '-i', input_file,
        '-c:v', 'libx264',
        '-c:a', 'aac',
        '-strict', 'experimental',
        output_file
    ]
    try:
        subprocess.run(command, check=True)
        os.remove(input_file)
        return output_file
    except Exception as e:
        print("轉檔失敗：", str(e))
        return input_file

def process_one_url(video_url, format_choice):
    uid = str(uuid.uuid4())[:8]
    temp_template = os.path.join(DOWNLOAD_DIR, f'{uid}_%(title).80s.%(ext)s')

    ydl_opts = {
        'outtmpl': temp_template,
        'quiet': False,
        'merge_output_format': 'mp4',
        'progress_hooks': [lambda d: print(f"進度：{d.get('status')} {d.get('filename', '')}")]
    }

    if format_choice == 'mp3':
        ydl_opts['format'] = 'bestaudio/best'
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]
    elif format_choice == 'wav':
        ydl_opts['format'] = 'bestaudio/best'
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'wav',
        }]
    elif format_choice == 'video720':
        ydl_opts['format'] = 'bestvideo[height<=720]+bestaudio/best'
    elif format_choice == 'video1080':
        ydl_opts['format'] = 'bestvideo[height<=1080]+bestaudio/best'
    else:
        ydl_opts['format'] = 'bestvideo+bestaudio/best'

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            downloaded_path = ydl.prepare_filename(info)

            # 音訊處理後副檔名
            if format_choice in ['mp3', 'wav']:
                downloaded_path = re.sub(r'\.[^.]+$', f'.{format_choice}', downloaded_path)
                return {
                    'title': info.get('title'),
                    'thumbnail': info.get('thumbnail'),
                    'filename': os.path.basename(downloaded_path),
                    'filepath': downloaded_path
                }

            # 影片轉檔邏輯：只要不是 mp4+H.264 就強制轉
            probe_cmd = [
                'ffprobe', '-v', 'error',
                '-select_streams', 'v:0',
                '-show_entries', 'stream=codec_name',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                downloaded_path
            ]
            result = subprocess.run(probe_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            video_codec = result.stdout.strip()

            if not downloaded_path.endswith('.mp4') or video_codec != 'h264':
                downloaded_path = convert_to_safe_mp4(downloaded_path)

            return {
                'title': info.get('title'),
                'thumbnail': info.get('thumbnail'),
                'filename': os.path.basename(downloaded_path),
                'filepath': downloaded_path
            }

    except Exception as e:
        print("錯誤：", str(e))
        return {'error': str(e)}

@app.route('/', methods=['GET', 'POST'])
def index():
    video_infos = []
    if request.method == 'POST':
        clean_download_folder()

        url_input = request.form.get('url')
        format_choice = request.form.get('format')

        if not url_input:
            return render_template('index.html', error="請輸入影片連結")

        urls = [u.strip() for u in url_input.replace('\n', ',').split(',') if u.strip()]

        for url in urls:
            info = process_one_url(url, format_choice)
            if 'error' in info:
                return render_template('index.html', error=f"下載失敗：{info['error']}")
            video_infos.append(info)

        if len(video_infos) == 1:
            filepath = video_infos[0]['filepath']
            return send_file(filepath, as_attachment=True)

    return render_template('index.html', video_info=video_infos[0] if video_infos else None)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
