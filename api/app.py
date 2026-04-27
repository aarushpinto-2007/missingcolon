import os
import subprocess
import shutil
import logging
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
from cryptography.fernet import Fernet
from concurrent.futures import ThreadPoolExecutor
import os
from flask import Flask

# Point to the root directory where templates/ and static/ reside
template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'templates'))
static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'static'))

app = Flask(__name__, 
            template_folder=template_dir, 
            static_folder=static_dir)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder='../templates', static_folder='../static')
CORS(app)

BASE_PATH = "/tmp/shieldstream"
UPLOAD_DIR = os.path.join(BASE_PATH, 'uploads')
VAULT_DIR  = os.path.join(BASE_PATH, 'vault')
KEY_DIR    = os.path.join(BASE_PATH, 'secure_keys')
MASTER_DIR = os.path.join(BASE_PATH, 'final_stream')
MASTER_VIDEO = os.path.join(MASTER_DIR, "ShieldStream_LIVE_Master.mp4")

metadata = {"filename": "ShieldStream_Broadcast"}


def initialize_folders():
    for d in [UPLOAD_DIR, VAULT_DIR, KEY_DIR, MASTER_DIR]:
        os.makedirs(d, exist_ok=True)


def ffmpeg_available():
    return shutil.which("ffmpeg") is not None


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/sender_upload', methods=['POST'])
def sender():
    if 'video' not in request.files:
        return jsonify({"error": "No file provided"}), 400

    if not ffmpeg_available():
        return jsonify({"error": "FFmpeg not found on server"}), 500

    initialize_folders()

    file = request.files['video']
    base_name = os.path.splitext(file.filename)[0]
    metadata["filename"] = base_name

    video_path = os.path.join(UPLOAD_DIR, file.filename)
    file.save(video_path)
    logger.info(f"Saved uploaded file: {video_path}")

    output_template = os.path.join(UPLOAD_DIR, "part_%03d.mp4")

    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-vf", "drawtext=text='SHIELD-ID':x=w-tw-20:y=h-th-20:fontcolor=white@0.4:fontsize=24",
        "-f", "segment", "-segment_time", "30",
        "-reset_timestamps", "1",
        output_template
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(f"FFmpeg error: {result.stderr}")
        return jsonify({"error": "FFmpeg processing failed", "detail": result.stderr}), 500

    filenames = sorted([f for f in os.listdir(UPLOAD_DIR) if f.startswith("part_")])
    if not filenames:
        return jsonify({"error": "No segments produced by FFmpeg"}), 500

    logger.info(f"Produced {len(filenames)} segments")

    def encrypt_work(fname):
        key = Fernet.generate_key()
        key_file = os.path.join(KEY_DIR, f"{fname}.key")
        enc_file  = os.path.join(VAULT_DIR, f"{fname}.dat")

        with open(key_file, "wb") as kf:
            kf.write(key)

        src_path = os.path.join(UPLOAD_DIR, fname)
        with open(src_path, "rb") as f:
            encrypted = Fernet(key).encrypt(f.read())

        with open(enc_file, "wb") as f:
            f.write(encrypted)

        logger.info(f"Encrypted: {fname}")

    with ThreadPoolExecutor(max_workers=4) as exe:
        exe.map(encrypt_work, filenames)

    return jsonify({"status": "Success", "parts": len(filenames)})


@app.route('/run_receiver_task', methods=['POST'])
def run_receiver_task():
    initialize_folders()

    if not ffmpeg_available():
        return jsonify({"error": "FFmpeg not found on server"}), 500

    vault_files = sorted([f for f in os.listdir(VAULT_DIR) if f.endswith('.dat')])
    if not vault_files:
        return jsonify({"status": "Empty", "message": "Nothing in vault yet."})

    current_segments = []

    for filename in vault_files:
        chunk_id = filename.replace(".dat", "")
        enc_path  = os.path.join(VAULT_DIR, filename)
        key_path  = os.path.join(KEY_DIR, f"{chunk_id}.key")

        if not os.path.exists(key_path):
            logger.warning(f"Key not found for {chunk_id}, skipping.")
            continue

        with open(enc_path, "rb") as f:
            enc_data = f.read()
        with open(key_path, "rb") as f:
            key_data = f.read()

        try:
            decrypted = Fernet(key_data).decrypt(enc_data)
        except Exception as e:
            logger.error(f"Decryption failed for {chunk_id}: {e}")
            continue

        tmp_mp4 = os.path.join(MASTER_DIR, f"dec_{chunk_id}")
        tmp_ts  = os.path.join(MASTER_DIR, f"{chunk_id}.ts")

        with open(tmp_mp4, "wb") as f:
            f.write(decrypted)

        ts_result = subprocess.run(
            ["ffmpeg", "-y", "-i", tmp_mp4, "-c", "copy", "-f", "mpegts", tmp_ts],
            capture_output=True, text=True
        )

        if ts_result.returncode == 0 and os.path.exists(tmp_ts):
            current_segments.append(tmp_ts)
        else:
            logger.error(f"TS conversion failed for {chunk_id}: {ts_result.stderr}")

        if os.path.exists(tmp_mp4):
            os.remove(tmp_mp4)

    if not current_segments:
        return jsonify({"status": "Error", "message": "No segments could be decrypted."})

    concat_file = os.path.join(MASTER_DIR, "join_list.txt")
    with open(concat_file, "w") as f:
        for ts in current_segments:
            f.write(f"file '{ts}'\n")

    concat_result = subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_file,
         "-c", "copy", MASTER_VIDEO],
        capture_output=True, text=True
    )

    if concat_result.returncode != 0:
        logger.error(f"Concat failed: {concat_result.stderr}")
        return jsonify({"status": "Error", "message": "Failed to assemble final video"}), 500

    logger.info("Final video assembled successfully.")
    return jsonify({"status": "Success", "decrypted_count": len(current_segments)})


@app.route('/stream_video')
def stream_video():
    if not os.path.exists(MASTER_VIDEO):
        return jsonify({"error": "No video ready yet. Run receiver task first."}), 404
    return send_from_directory(MASTER_DIR, "ShieldStream_LIVE_Master.mp4")


@app.route('/scan_link', methods=['POST'])
def scan_link():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400
    url = data.get('url', '')
    is_piracy = any(word in url.lower() for word in ['stream', 'live', 'tv', 'watch'])
    return jsonify({"found": is_piracy, "url": url})


@app.route('/health')
def health():
    return jsonify({"status": "ok", "ffmpeg": ffmpeg_available()})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
