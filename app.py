from flask import Flask, render_template, request, send_file
import yt_dlp
import os
import uuid
import re

app = Flask(__name__)
DOWNLOAD_DIR = os.path.join(os.getcwd(), 'downloads')
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# 清除下載資料夾
def clean_download_folder():
    for f in os.listdir(DOWNLOAD_DIR):
        try:
            os.remove(os.path.join(DOWNLOAD_DIR, f))
        except:
            pass

# 下載一筆連結並轉成 mp3 或 wav
def download_audio(video_url, format_choice):
    uid = str(uuid.uuid4())[:8]
    output_template = os.path.join(DOWNLOAD_DIR, f'{uid}_%(title).80s.%(ext)s')

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_template,
        'quiet': False,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': format_choice,
            'preferredquality': '192' if format_choice == 'mp3' else None,
        }]
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            downloaded_path = ydl.prepare_filename(info)
            downloaded_path = re.sub(r'\.[^.]+$', f'.{format_choice}', downloaded_path)

            return {
                'title': info.get('title'),
                'filename': os.path.basename(downloaded_path),
                'filepath': downloaded_path
            }
    except Exception as e:
        return {'error': str(e)}

# 首頁與處理表單
@app.route('/', methods=['GET', 'POST'])
def index():
    audio_infos = []
    if request.method == 'POST':
        clean_download_folder()
        url_input = request.form.get('url')
        format_choice = request.form.get('format')

        if not url_input or format_choice not in ['mp3', 'wav']:
            return render_template('index.html', error="請輸入影片連結並選擇格式")

        urls = [u.strip() for u in url_input.replace('\n', ',').split(',') if u.strip()]
        for url in urls:
            info = download_audio(url, format_choice)
            if 'error' in info:
                return render_template('index.html', error=f"下載失敗：{info['error']}")
            audio_infos.append(info)

        if len(audio_infos) == 1:
            return send_file(audio_infos[0]['filepath'], as_attachment=True)

    return render_template('index.html', audio_info=audio_infos[0] if audio_infos else None)

# 正確處理埠口，支援本地與 Render 雲端
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))  # Render 指定 PORT
    app.run(debug=True, host="0.0.0.0", port=port)
