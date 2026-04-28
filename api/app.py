import os, subprocess, requests, shutil, io
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
from cryptography.fernet import Fernet
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)
CORS(app)

# --- CONFIGURATION ---
# We use /tmp because it's high-speed RAM-based storage on most Linux servers
BASE_PATH = "/tmp/shieldstream"
UPLOAD_DIR = os.path.join(BASE_PATH, 'uploads')
RECEIVE_DIR = os.path.join(BASE_PATH, 'receiver_buffer')
MASTER_VIDEO = os.path.join(RECEIVE_DIR, "live_output.mp4")

# Set your Receiver URL (If same app, use localhost, else use the other app's URL)
RECEIVER_URL = "http://127.0.0.1:8000/internal_receive"

def cleanup():
    if os.path.exists(BASE_PATH):
        shutil.rmtree(BASE_PATH)
    for d in [UPLOAD_DIR, RECEIVE_DIR]:
        os.makedirs(d, exist_ok=True)

cleanup()

# --- SENDER LOGIC (Transmit) ---
@app.route('/sender_upload', methods=['POST'])
def sender():
    if 'video' not in request.files: return jsonify({"error": "No file"}), 400
    
    file = request.files['video']
    video_path = os.path.join(UPLOAD_DIR, "input_raw.mp4")
    file.save(video_path)

    # Segmenting into 5-second tiny bursts for fast transmission
    output_template = os.path.join(UPLOAD_DIR, "chunk_%03d.mp4")
    subprocess.run([
        "ffmpeg", "-i", video_path, "-f", "segment", 
        "-segment_time", "5", "-c", "copy", output_template
    ])

    chunks = sorted([f for f in os.listdir(UPLOAD_DIR) if f.startswith("chunk_")])
    
    for fname in chunks:
        # 1. Encrypt in Memory
        key = Fernet.generate_key()
        f_cipher = Fernet(key)
        with open(os.path.join(UPLOAD_DIR, fname), "rb") as f:
            encrypted_data = f_cipher.encrypt(f.read())
        
        # 2. Push directly to Receiver
        try:
            requests.post(RECEIVER_URL, files={
                'chunk': (fname, encrypted_data),
                'key': (f"{fname}.key", key)
            })
        except:
            pass # Receiver might be busy

    return jsonify({"status": "Stream Transmitted", "chunks": len(chunks)})

# --- RECEIVER LOGIC (Assemble) ---
@app.route('/internal_receive', methods=['POST'])
def internal_receive():
    chunk_file = request.files['chunk']
    key_file = request.files['key']
    
    # Decrypt in Memory
    f_cipher = Fernet(key_file.read())
    decrypted_data = f_cipher.decrypt(chunk_file.read())
    
    # Temporary TS file for merging
    ts_path = os.path.join(RECEIVE_DIR, f"{chunk_file.filename}.ts")
    
    # Convert Decrypted RAM data to TS via FFmpeg Pipe
    process = subprocess.Popen(
        ['ffmpeg', '-i', 'pipe:0', '-f', 'mpegts', '-c', 'copy', '-y', ts_path],
        stdin=subprocess.PIPE
    )
    process.communicate(input=decrypted_data)

    # Append to Master Live Stream
    if os.path.exists(MASTER_VIDEO):
        # Concatenate existing master + new chunk
        list_path = os.path.join(RECEIVE_DIR, "list.txt")
        with open(list_path, "w") as f:
            f.write(f"file 'live_output.mp4'\nfile '{chunk_file.filename}.ts'")
        
        subprocess.run([
            "ffmpeg", "-f", "concat", "-safe", "0", "-i", list_path, 
            "-c", "copy", "-y", os.path.join(RECEIVE_DIR, "temp_master.mp4")
        ])
        os.replace(os.path.join(RECEIVE_DIR, "temp_master.mp4"), MASTER_VIDEO)
    else:
        # First chunk becomes the master
        os.replace(ts_path, MASTER_VIDEO)

    return jsonify({"status": "received"})

@app.route('/stream')
def stream():
    return send_from_directory(RECEIVE_DIR, "live_output.mp4")

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
