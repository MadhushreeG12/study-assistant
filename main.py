# main.py (UPDATED)
import os
import re
import requests
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import pdfplumber

load_dotenv() # Load environment variables from .env file
import pytesseract
from pdf2image import convert_from_path
from groq import Groq
from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlparse, parse_qs
import yt_dlp
from flask_sqlalchemy import SQLAlchemy
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from rouge_score import rouge_scorer
import pyttsx3
import subprocess
import shutil
import uuid


# ---------------- CONFIG ----------------
UPLOAD_FOLDER = "uploads"
AUDIO_FOLDER = "static/audio"

ALLOWED_PDF = {"pdf"}
ALLOWED_VIDEO = {"mp4"}  # <-- MP4 only

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["AUDIO_FOLDER"] = AUDIO_FOLDER
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(os.getcwd(), "users.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = "explainitai"

db = SQLAlchemy(app)

# ---------------- API KEYS ----------------
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    print("WARNING: GROQ_API_KEY not set!")
client = Groq(api_key=GROQ_API_KEY)

GROQ_ASR_URL = "https://api.groq.com/openai/v1/audio/transcriptions"

GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"

# ---------------- LOGGING ----------------
def log_debug(msg):
    try:
        with open("manual_debug_log.txt", "a", encoding="utf-8") as f:
            import datetime
            ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{ts}] {msg}\n")
            f.flush()
            os.fsync(f.fileno())
    except:
        pass

log_debug("Logger initialized.")


# ---------------- DATABASE MODELS ----------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

class History(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_email = db.Column(db.String(150), db.ForeignKey('user.email'), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # pdf / youtube / video
    title = db.Column(db.String(200), nullable=False)
    summary = db.Column(db.Text, nullable=False)
    audio_filename = db.Column(db.String(200), nullable=True)
    flashcards = db.Column(db.Text, nullable=True)  # Store JSON as string
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

with app.app_context():
    try:
        import shutil
        if shutil.which("ffmpeg"):
           log_debug("FFmpeg found in path.")
        else:
           log_debug("WARNING: FFmpeg NOT found in path.")
    except:
        pass

    db.create_all()

    # Migration: Check if 'flashcards' column exists in History table
    from sqlalchemy import inspect, text
    inspector = inspect(db.engine)
    columns = [col['name'] for col in inspector.get_columns('history')]
    if 'flashcards' not in columns:
        print("Migrating DB: Adding flashcards column...")
        with db.engine.connect() as conn:
            conn.execute(text("ALTER TABLE history ADD COLUMN flashcards TEXT"))
            conn.commit()
            print("Migration complete.")

# ---------------- ROUTES ----------------
@app.route('/starter')
def starter():
    if 'user' not in session:
        return redirect(url_for('index'))
    user_name = session.get("user")
    return render_template("index.html", user_name=user_name)

# ---------------- VALIDATORS ----------------
def allowed_pdf(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_PDF

def allowed_video(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_VIDEO

# ---------------- TEXT / PDF PROCESSING ----------------
def extract_text(pdf_path):
    """Extract text from PDF, fallback to OCR."""
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                txt = page.extract_text()
                if txt:
                    text += txt + "\n"
    except Exception:
        # best-effort fallback to OCR if pdfplumber fails
        pass

    if len(text.strip()) < 50:  # probably scanned PDF
        try:
            images = convert_from_path(pdf_path)
            for img in images:
                text += pytesseract.image_to_string(img)
        except Exception:
            pass

    return text.strip()

def clean_text(raw_text):
    text = re.sub(r'\bPage \d+\b', '', raw_text)
    text = re.sub(r'Table \d+.*?\n', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# ---------------- GROQ SUMMARIZATION HELPERS ----------------
def summarize_with_groq(text, system_prompt, model="llama-3.3-70b-versatile", max_tokens=6000, retries=5):
    """
    Generic wrapper to call Groq chat completion and return content or error string.
    retries: Configurable retries. Use low retry for 70B (fail fast), high for 8B (guarantee).
    """
    import time
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    user_content = text + "\n\n(IMPORTANT: Please provide the response in English ONLY, regardless of the original language of the text above.)"
    
    data = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ],
        "temperature": 0.3,
        "max_tokens": max_tokens
    }


    for attempt in range(retries):
        try:
            # Timeout: 120s is enough for one attempt. Don't wait 6 mins per request.
            resp = requests.post(GROQ_CHAT_URL, headers=headers, json=data, timeout=120)
            
            if resp.status_code == 429:
                wait_time = (attempt + 1) * 5  # Fast backoff: 5s, 10s.
                if attempt == retries - 1:
                     # Don't wait on the last attempt
                     break
                msg = f"Rate limit hit (429). Retrying in {wait_time}s..."
                print(msg)
                time.sleep(wait_time)
                continue
            
            result = resp.json()
            if resp.status_code != 200:
                # Handle invalid API key specifically
                if resp.status_code == 401 or "invalid_api_key" in str(result):
                    return "[Error: Invalid API Key. Please make sure GROQ_API_KEY is set correctly in your Render Environment Variables.]"
                return f"[Error summarization] {result}"
            
            if "choices" not in result:
                return "[Error summarization] unexpected response"
            
            return result["choices"][0]["message"]["content"]
            
        except Exception as e:
            if attempt == retries - 1:
                return f"[Error summarization] {e}"
            time.sleep(3)
    
    return "[Error summarization] Max retries exceeded"

def summarize_long_text(text, base_system_prompt):
    """
    Splits long text into chunks and summarizes each SEQUENTIALLY.
    Strategy: Try High Quality (70B) ONCE. If fail, switch to Fast (8B).
    """
    import time
    # 25k chars is safe.
    CHUNK_SIZE = 25000 
    
    if len(text) <= CHUNK_SIZE:
        # Try 70B with 1 retry. If fail -> 8B.
        res = summarize_with_groq(text, base_system_prompt, retries=1)
        if "[Error" in res:
             print("70B failed. Switching to 8B.")
             return summarize_with_groq(text, base_system_prompt, model="llama-3.1-8b-instant", retries=5)
        return res

    chunks = [text[i:i+CHUNK_SIZE] for i in range(0, len(text), CHUNK_SIZE)]
    print(f"DEBUG: Text length {len(text)} split into {len(chunks)} chunks.")
    
    full_summary_parts = []
    
    for i, chunk in enumerate(chunks):
        print(f"Summarizing chunk {i+1}/{len(chunks)}...")
        chunk_prompt = f"{base_system_prompt}\n(Note: This is Part {i+1} of {len(chunks)} of the transcript. Summarize this section in detail.)"
        
        # PRIMARY STRATEGY: Try 70B Model (High Quality)
        # retries=1 -> FAIL FAST. Don't wait 5 mins.
        print("Attempting with 70B (High Quality)...")
        res = summarize_with_groq(chunk, chunk_prompt, max_tokens=2500, retries=1)
        
        # SECONDARY STRATEGY: Fallback to 8B Model (High Speed/Reliability)
        if "[Error" in res:
             print(f"Chunk {i+1}: 70B busy/limited. switching to Llama 3.1 8B (Guaranteed)...")
             time.sleep(2) 
             res = summarize_with_groq(chunk, chunk_prompt, model="llama-3.1-8b-instant", max_tokens=2500, retries=5)

        full_summary_parts.append(res)
        
        # Small cooldown is still good practice
        if i < len(chunks) - 1:
            time.sleep(5)

    return "\n\n".join(filter(None, full_summary_parts))

def generate_narration_script(text):
    """Generate narration-style summary using Groq LLM (safe model)."""
    if not text:
        return "No readable text found."
    
    # Use summarize_long_text to handle large PDFs (supports 100+ pages via chunking)
    prompt = (
        "You are an expert educational tutor. Create a comprehensive, clear, and accurate study guide based on the following content. "
        "Focus purely on the concepts, facts, and explanations. "
        "Do NOT mention 'the speaker', 'the creator', or 'the video'. "
        "Structure the response with clear headings and bullet points. "
        "Make it easy for a student to read and understand. "
        "Ensure high accuracy and capture all key details. "
        "IMPORTANT: OUTPUT MUST BE STRICTLY IN ENGLISH. IF THE SOURCE IS NOT ENGLISH, TRANSLATE IT."
    )
    return summarize_long_text(text, prompt)

def generate_final_summary(text):
    """Return HTML <ul> list of bullets from the summarizer."""
    raw = generate_narration_script(text)
    lines = raw.split("\n")
    lis = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith("-"):
            content = line.lstrip("- ").strip()
        else:
            content = line
        lis.append(f"<li>{content}</li>")
    return "<ul>" + "".join(lis) + "</ul>"

# ---------------- VIDEO / AUDIO PROCESSING ----------------
def video_to_audio(video_path):
    """Extract audio from MP4 using ffmpeg (fast extraction)."""
    try:
        audio_path = video_path.rsplit(".", 1)[0] + ".mp3"
        # ffmpeg -i input.mp4 -vn -acodec libmp3lame -q:a 4 -y output.mp3
        # -vn: no video
        # -acodec libmp3lame: mp3 codec
        # -q:a 4: standard quality (approx 128-160kbps), good balance
        # -y: overwrite
        # -loglevel error: quiet
        cmd = [
            "ffmpeg", "-i", video_path, 
            "-vn", "-acodec", "libmp3lame", "-q:a", "4", 
            "-y", "-loglevel", "error", 
            audio_path
        ]
        print(f"Running ffmpeg extraction: {' '.join(cmd)}")
        subprocess.run(cmd, check=True)
        return audio_path
    except Exception as e:
        print("video_to_audio error:", e)
        return None

def audio_to_text(audio_file):
    """Send audio file to Groq ASR and return text."""
    try:
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
        with open(audio_file, "rb") as f:
            response = requests.post(
                GROQ_ASR_URL,
                headers=headers,
                files={"file": f},
                data={"model": "whisper-large-v3"},
                timeout=300
            )
        result = response.json()
        if response.status_code != 200:
            print("ASR error:", result)
            logging.error(f"ASR Error: {result}")
            return ""
        return result.get("text", "")
    except Exception as e:
        print("audio_to_text error:", e)
        logging.error(f"audio_to_text exception: {e}", exc_info=True)
        return ""



def process_large_audio(audio_path, job_id=None):
    """
    Process audio file by splitting it into chunks using ffmpeg (FAST - STREAM COPY).
    Then transcribes in parallel.
    """
    import math
    import concurrent.futures
    import json
    import glob

    full_transcript = []
    
    # ---------------- DYNAMIC CONFIGURATION ----------------
    # Render Free Tier has 512MB RAM. Large parallelism = OOM Kill.
    # Localhost usually has 8GB+.
    IS_RENDER = os.environ.get("RENDER") is not None
    
    if IS_RENDER:
        print("Detected RENDER environment. Using SAFE MODE (Low Memory).")
        CHUNK_DURATION_SEC = 300  # 5 mins per chunk to reduce memory
        MAX_WORKERS = 2           # Only 2 parallel workers
    else:
        print("Detected LOCALHOST environment. Using PERFORMANCE MODE.")
        CHUNK_DURATION_SEC = 600  # 10 mins per chunk
        MAX_WORKERS = 5           # 5 parallel workers
    # -------------------------------------------------------

    try:
        print(f"Loading media file: {audio_path}")
        if job_id: JOBS[job_id]["status"] = "Checking audio duration..."
        
        # Get duration and codec using ffprobe (JSON)
        # ffprobe -v error -select_streams a:0 -show_entries stream=codec_name:format=duration -of json input
        cmd_probe = [
            "ffprobe", "-v", "error",
            "-select_streams", "a:0",
            "-show_entries", "stream=codec_name:format=duration",
            "-of", "json",
            audio_path
        ]
        
        duration = 0
        codec_name = "unknown"
        
        try:
            result = subprocess.run(cmd_probe, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            info = json.loads(result.stdout)
            
            if "streams" in info and info["streams"]:
                codec_name = info["streams"][0].get("codec_name", "unknown")
                
            if "format" in info:
                duration = float(info["format"].get("duration", 0))
                
        except Exception as e:
             print(f"ffprobe failed: {e}")
             # Fallback: try old method or just proceed with 0
             pass

        file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
        print(f"Total duration: {duration}s, Size: {file_size_mb:.2f}MB, Codec: {codec_name}")

        if duration > 0 and duration <= CHUNK_DURATION_SEC and file_size_mb < 24:
             log_debug("Duration is short and size is small, processing directly...")
             if job_id: JOBS[job_id]["status"] = "Transcribing..."
             return audio_to_text(audio_path)

        # Split using ffmpeg segment with STREAM COPY (NO RE-ENCODING)
        if job_id: JOBS[job_id]["status"] = "Splitting audio (Fast Copy)..."
        print(f"Splitting into chunks of {CHUNK_DURATION_SEC}s...")
        
        base_name = audio_path.rsplit(".", 1)[0]
        
        # Smart Extension Mapping for Stream Copy
        # Groq supports: flac, mp3, mp4, mpeg, mpga, m4a, ogg, wav, webm
        ext_map = {
            "aac": "m4a",
            "mp3": "mp3",
            "opus": "webm",
            "vorbis": "ogg",
            "flac": "flac",
            "pcm_s16le": "wav"
        }
        # Default to m4a if unknown, or maintain original ext if possible? 
        # m4a is a safe bet for most modern stuff, but let's use map.
        ext = ext_map.get(codec_name, "m4a")
        
        chunk_pattern = f"{base_name}_chunk_%03d.{ext}"
        
        # -vn: no video
        # -c:a copy: copy audio header
        # -map 0:a: map first audio stream
        cmd_split = [
            "ffmpeg", "-i", audio_path,
            "-f", "segment",
            "-segment_time", str(CHUNK_DURATION_SEC),
            "-vn", "-c:a", "copy",
            "-reset_timestamps", "1",
            "-map", "0:a",
            "-y", "-loglevel", "error",
            chunk_pattern
        ]
        
        # FALLBACK: If copy fails (e.g. incompatible container), we might need re-encode.
        res = subprocess.run(cmd_split, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if res.returncode != 0:
            print(f"Stream copy failed ({res.stderr[:200]}), falling back to re-encode...")
            log_debug(f"Stream copy failed, re-encoding. Error: {res.stderr[:200]}")
            # Fallback to re-encode (original safe method)
            ext = "mp3"
            cmd_split = [
                "ffmpeg", "-i", audio_path, 
                "-f", "segment", 
                "-segment_time", str(CHUNK_DURATION_SEC), 
                "-vn", "-acodec", "libmp3lame", "-q:a", "4",
                "-y", "-loglevel", "error", 
                f"{base_name}_chunk_%03d.{ext}"
            ]
            subprocess.run(cmd_split, check=True)
        
        pattern_glob = f"{base_name}_chunk_*.{ext}"
        
        # Check generated files
        found_chunks = sorted(glob.glob(pattern_glob))
        print(f"Generated {len(found_chunks)} chunks.")
        
        if not found_chunks:
            return "[ERROR: No chunks generated]"

        # Parallel Transcription
        if job_id: JOBS[job_id]["status"] = f"Transcribing {len(found_chunks)} chunks..."
        print(f"Starting parallel transcription (Workers: {MAX_WORKERS})...")
        
        results = [None] * len(found_chunks)

        def transcribe_chunk(index, filename):
            # print(f"Processing chunk {index+1}...") 
            text = audio_to_text(filename)
            try:
                os.remove(filename)
            except:
                pass
            return index, text

        # Dynamic max_workers
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_chunk = {executor.submit(transcribe_chunk, i, f): i for i, f in enumerate(found_chunks)}
            for future in concurrent.futures.as_completed(future_to_chunk):
                idx = future_to_chunk[future]
                try:
                    idx, text = future.result()
                    results[idx] = text
                    # Explicit GC help
                    import gc
                    gc.collect()
                except Exception as e:
                    print(f"Error transcribing chunk {idx}: {e}")

        return " ".join(filter(None, results)).strip()

    except Exception as e:
        err_msg = f"CRITICAL ERROR in process_large_audio: {e}"
        print(err_msg)
        log_debug(err_msg)
        return f"[ERROR: {str(e)}]"


# ---------------- YOUTUBE HELPERS ----------------
def extract_video_id(youtube_url):
    try:
        parsed = urlparse(youtube_url)
        if parsed.hostname in ('www.youtube.com', 'youtube.com'):
            return parse_qs(parsed.query).get('v', [None])[0]
        if parsed.hostname == 'youtu.be':
            return parsed.path.lstrip('/')
    except Exception:
        pass
    return None

def get_transcript(video_id):
    """Try official transcript via youtube_transcript_api; raises if not available."""
    transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
    return " ".join([entry['text'] for entry in transcript])

def download_audio_from_youtube(youtube_url):
    """Download best audio (m4a/aac) directly using yt_dlp and return local filename, or None on failure."""
    import sys
    
    # Use unique name
    outname = f"yt_{uuid.uuid4().hex}.m4a"
    log_debug(f"Starting download (fast mode) for {youtube_url} -> {outname}")

    cmd = [
        sys.executable, "-m", "yt_dlp",
        "-f", "bestaudio[ext=m4a]/bestaudio", # Get m4a directly if possible
        "-o", outname,
        "--extractor-args", "youtube:player_client=android_creator",
        "--no-check-certificate",
        "--no-warnings",
        "--quiet",
        youtube_url
    ]

    try:
        log_debug(f"Running command: {' '.join(cmd)}")
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        if result.returncode != 0:
            log_debug(f"yt-dlp failed with code {result.returncode}")
            log_debug(f"STDERR: {result.stderr}")
            print(f"yt-dlp stderr: {result.stderr}")
            return None, result.stderr
            
        if os.path.exists(outname):
            log_debug(f"Download success: {outname} - Size: {os.path.getsize(outname)} bytes")
            return outname, None
        else:
            log_debug("yt-dlp successfully finished but file not found.")
            return None, f"File not found after download. Stderr: {result.stderr}"

    except Exception as e:
        print("download_audio_from_youtube error:", e)
        import traceback
        traceback.print_exc()
        log_debug(f"download_audio_from_youtube error: {e}")
        return None, str(e)

# ---------------- FLASHCARDS ----------------
def generate_flashcards(summary):
    prompt = f"""
    Here is the content summary:
    "{summary}"

    Based EXCLUSIVELY on the above summary, generate 10 High-Quality MCQs in valid JSON format.
    The questions should be challenging and test understanding of concepts, not just simple recall.
    Do not use placeholders like "..." or "A) ...". Generate actual questions and answers based on the text.
    IMPORTANT: QUESTIONS AND ANSWERS MUST BE IN ENGLISH.
    
    Required JSON format:
    {{
      "mcqs": [ 
        {{ 
          "question": "Actual question text here?", 
          "options": ["A) Option 1", "B) Option 2", "C) Option 3", "D) Option 4"], 
          "correct": "A" 
        }} 
      ]
    }}
    """
    MAX_RETRIES = 2
    
    # helper to clean json
    def clean_and_parse_json(content):
        import json, re
        # Remove markdown
        content = re.sub(r"```json", "", content)
        content = re.sub(r"```", "", content)
        content = content.strip()
        # Find valid JSON object
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        return None

    # Try 70B first (High Quality)
    try:
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
            temperature=0.2
        )
        content = resp.choices[0].message.content
        data = clean_and_parse_json(content)
        if data: 
            return data
    except Exception as e:
        print(f"70B Flashcard Gen failed: {e}. Switching to 8B...")

    # Fallback to 8B (High Speed/Reliability)
    try:
        # 8B is faster and less likely to be rate limited on free/fast tiers
        resp = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
            temperature=0.2
        )
        content = resp.choices[0].message.content
        data = clean_and_parse_json(content)
        if data:
            return data
        return {"error": "Failed to parse JSON from 8B model"}
        
    except Exception as e:
        return {"error": f"All models failed: {str(e)}"}

# ---------------- METRICS ----------------
def evaluate_summary_metrics(original_text, summary_html):
    summary_text = re.sub(r"<.*?>", "", summary_html)
    scorer = rouge_scorer.RougeScorer(["rouge1", "rouge2", "rougeL"], use_stemmer=True)
    try:
        scores = scorer.score(original_text, summary_text)
        r1 = scores["rouge1"].fmeasure or 0
        r2 = scores["rouge2"].fmeasure or 0
        rl = scores["rougeL"].fmeasure or 0
    except Exception:
        r1 = r2 = rl = 0.0

    try:
        vectorizer = TfidfVectorizer(stop_words='english').fit([original_text, summary_text])
        v = vectorizer.transform([original_text, summary_text])
        cosine = cosine_similarity(v[0], v[1])[0][0]
    except Exception:
        cosine = 0.0

    # ---------------- METRICS CALIBRATION (FINAL TUNE - USER REQUESTED RANGE 8.0 - 9.9) ----------------
    # The user explicitly requested: "above 8 and below 9.9 and it should vary".
    # We use a Linear Interpolation model with a Base Score of 8.0.
    
    def calculate_norm(value, min_val, max_val):
        if value < min_val: return 0.0
        if value > max_val: return 1.0
        return (value - min_val) / (max_val - min_val)

    # Thresholds (Min, Max)
    TR_R1 = (0.15, 0.45)
    TR_R2 = (0.05, 0.20)
    TR_RL = (0.12, 0.40)
    TR_COS = (0.10, 0.55)
    
    norm_r1 = calculate_norm(r1, *TR_R1)
    norm_r2 = calculate_norm(r2, *TR_R2)
    norm_rl = calculate_norm(rl, *TR_RL)
    norm_cos = calculate_norm(cosine, *TR_COS)

    # Weighted Average of the "Quality" (0.0 to 1.0)
    avg_norm = (norm_r1 + norm_r2 + norm_rl + norm_cos) / 4.0
    
    # Formula: Base(8.0) + (Quality * 1.9)
    # Range: 8.00 to 9.90
    overall = 8.0 + (avg_norm * 1.9)
    
    return {
        "rouge1": round(r1, 3), # Keep raw for display details
        "rouge2": round(r2, 3),
        "rougeL": round(rl, 3),
        "cosine": round(cosine, 3),
        "overall": round(overall, 1) # This is what the user sees as the main score
    }

# ---------------- TTS ----------------
def generate_tts_audio(text, filename):
    """Generate TTS audio using pyttsx3 and return the filename (or None)."""
    try:
        import pythoncom
        pythoncom.CoInitialize()
        engine = pyttsx3.init()
        engine.setProperty("rate", 150)
        engine.setProperty("volume", 0.9)

        # Use absolute path to ensure we know exactly where it goes
        abs_audio_folder = os.path.join(app.root_path, app.config["AUDIO_FOLDER"])
        os.makedirs(abs_audio_folder, exist_ok=True)
        
        filepath = os.path.join(abs_audio_folder, filename)
        print(f"[TTS] Saving audio to: {filepath}")

        engine.save_to_file(text, filepath)
        engine.runAndWait()
        
        if os.path.exists(filepath):
            print(f"[TTS] File successfully created: {filepath} (Size: {os.path.getsize(filepath)} bytes)")
        else:
            print(f"[TTS] ERROR: File was NOT created at {filepath}")

        pythoncom.CoUninitialize()
        return filename
    except Exception as e:
        print("TTS error:", e)
        return None

# ---------------- FORMATTING HELPERS ----------------
def clean_for_tts(text):
    """Remove markdown symbols for clean speech."""
    # Remove bold/italic markers
    text = text.replace("**", "").replace("*", "").replace("`", "")
    # Remove headers
    text = re.sub(r'#+\s', '', text)
    # Remove list bullets
    text = re.sub(r'^\s*-\s+', '', text, flags=re.MULTILINE)
    return text

def format_summary_html(text):
    """Convert basic Markdown to HTML for display."""
    # Bold
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    # Lists (simple dash to bullet) - Just wrap in lines for now as template calls | safe
    lines = text.split('\n')
    html_lines = []
    for line in lines:
        line = line.strip()
        if not line:
            html_lines.append("<br>")
            continue
        if line.startswith("-") or line.startswith("*"):
            clean_line = line.lstrip("-* ").strip()
            # Apply bolding inside lines
            clean_line = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', clean_line)
            html_lines.append(f"<li>{clean_line}</li>")
        elif line.startswith("#"):
             # Header
             html_lines.append(f"<h4>{line.lstrip('#').strip()}</h4>")
        else:
             html_lines.append(f"{line}<br>")
    return "".join(html_lines)

# ---------------- ROUTES: index/login/pdf/youtube/video ----------------
@app.route("/", methods=["GET", "POST"])
def index():
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("user", None)
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))

@app.route("/login_validation", methods=["POST"])
def login_validation():
    email = request.form["email"]
    password = request.form["password"]

    # Server-side validation
    # 1. Lowercase Check
    if any(char.isupper() for char in email):
        flash("Please enter email in lowercase only.", "warning")
        return redirect(url_for("index"))

    # 2. Format Check
    email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    if not re.match(email_regex, email):
        flash("Invalid email format.", "danger")
        return redirect(url_for("index"))

    user = User.query.filter_by(email=email).first()
    if user and user.password == password:
        session["user"] = email
        return redirect(url_for("starter"))
    flash("Invalid email or password.", "danger")
    return redirect(url_for("index"))

@app.route("/add_users", methods=["GET", "POST"])
def add_users():
    if request.method == "POST":
        uname = request.form.get("uname")
        email = request.form.get("uemail")
        password = request.form.get("upassword")

        if not email or not password:
            flash("Email and Password are required.", "danger")
            return redirect(url_for("add_users"))

        if len(password) < 4 or len(password) > 8:
            flash("Password must be between 4 and 8 characters long.", "warning")
            return redirect(url_for("add_users"))
        
        # Validation for Registration too
        if any(char.isupper() for char in email):
             flash("Email must be lowercase.", "warning")
             return redirect(url_for("add_users"))

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("Email already registered. Please login.", "warning")
            return redirect(url_for("index"))

        new_user = User(email=email, password=password)
        db.session.add(new_user)
        db.session.commit()

        flash("Registration successful! Please login.", "success")
        return redirect(url_for("index"))

    return render_template("register.html")

@app.route("/pdf", methods=["POST"])
def pdf_upload():
    file = request.files.get("file")
    if not file or file.filename == "":
        flash("No file selected.")
        return redirect("/starter")

    if not allowed_pdf(file.filename):
        flash("Only PDF files allowed.")
        return redirect("/starter")

    filename = secure_filename(file.filename)
    path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    file.save(path)

    raw = extract_text(path)
    clean = clean_text(raw)
    if not clean:
        summary_raw = "No readable text found in PDF."
    else:
        summary_raw = generate_narration_script(clean) # Get raw bullet points

    # Process: CLEAN for TTS, FORMAT for HTML
    tts_text = clean_for_tts(summary_raw)
    display_html = format_summary_html(summary_raw)

    metrics = evaluate_summary_metrics(clean, summary_raw)
    audio_name = generate_tts_audio(tts_text, f"summary_{filename}.mp3")

    if "user" in session:
        # Generate flashcards first so we can save them
        flashcards = generate_flashcards(summary_raw)
        import json
        flashcards_str = json.dumps(flashcards) if isinstance(flashcards, dict) else None
        
        h = History(user_email=session["user"], type="pdf", title=filename, summary=display_html, audio_filename=audio_name, flashcards=flashcards_str)
        db.session.add(h)
        db.session.commit()
        # Get the ID
        history_id = h.id
    else:
        # Fallback if not logged in (though starter blocks this)
        flashcards = generate_flashcards(summary_raw)
        history_id = None

    return render_template("result.html", summary=display_html, metrics=metrics, audio=audio_name, flashcards=flashcards, history_id=history_id)

@app.route("/youtube", methods=["POST"])
def youtube_summary():
    youtube_url = request.form.get("youtube_url")
    vid = extract_video_id(youtube_url)
    if not vid:
        flash("Invalid YouTube URL.")
        return redirect("/starter")

    log_debug(f"Processing YouTube Video: {vid}")
    print(f"Processing YouTube Video: {vid}")

    transcript = ""
    try:
        # Wrap the whole logic in a try block for safety
        try:
            log_debug(f"Attempting YouTube transcript API for {vid}")
            transcript = get_transcript(vid)
            log_debug("Official transcript found.")
        except Exception as e:
            log_debug(f"Official transcript failed: {e}")
            # Fallback to downloading audio & transcribing
            log_debug("Falling back to audio download...")
            audio_file, error_msg = download_audio_from_youtube(youtube_url)
            if audio_file:
                log_debug(f"Audio downloaded: {audio_file}")
                # Use process_large_audio to handle long durations (chunking)
                transcript = process_large_audio(audio_file)
                log_debug(f"Transcript generated length: {len(transcript)}")
                try:
                    if os.path.exists(audio_file):
                        # keep file for debug if error
                        if "[ERROR:" not in transcript:
                           os.remove(audio_file)
                except Exception:
                    pass
            else:
                 # SHOW THE ACTUAL ERROR to the user
                 full_error = f"Download failed: {error_msg}"
                 log_debug(full_error)
                 flash(full_error[:200]) # Cap length to avoid massive flash messages
                 return redirect("/starter")

        if not transcript or "[ERROR:" in transcript:
            log_debug(f"Transcript error/empty: {transcript}")
            flash(f"Failed to get transcript: {transcript}")
            return redirect("/starter")

    except Exception as e:
        log_debug(f"CRITICAL ERROR in youtube_summary route: {e}")
        import traceback
        traceback.print_exc()
        flash(f"An internal error occurred: {e}")
        return redirect("/starter")


    # ---------------- NO TRUNCATION ----------------
    # We now use chunked processing in summarize_long_text to handle unlimited length.

    # -----------------------------------------------

    system_prompt = (
        "You are an expert educational tutor. Create a HIGH-VALUE, COMPREHENSIVE study guide based on this video transcript. "
        "Your goal is to extract the maximum learning value from the content. "
        "Focus on the Core Concepts, Critical Explanations, and Key Takeaways. "
        "Avoid trivial details or fluff. Prioritize information that is essential for understanding. "
        "Provide deep explanations for the major topics found. "
        "Structure the response clearly. "
        "Use strict Markdown structure: \n"
        "# Main Topic\n"
        "## Sub-topic\n"
        "- **Key Concept**: Clear, valuable explanation...\n"
        "IMPORTANT: OUTPUT MUST BE STRICTLY IN ENGLISH. IF THE TRANSCRIPT IS NOT ENGLISH, TRANSLATE IT."
    )
    summary_raw = summarize_long_text(transcript, system_prompt)
    log_debug(f"Full summary generated. Length: {len(summary_raw)}")
    
    # Process
    tts_text = clean_for_tts(summary_raw)
    display_html = format_summary_html(summary_raw)

    metrics = evaluate_summary_metrics(transcript, summary_raw)
    log_debug("Metrics evaluated.")
    
    audio_name = generate_tts_audio(tts_text, f"summary_{vid}.mp3")
    log_debug(f"TTS Audio generated: {audio_name}")

    flashcards = generate_flashcards(summary_raw)
    history_id = None

    if "user" in session:
        import json
        flashcards_str = json.dumps(flashcards) if isinstance(flashcards, dict) else None
        
        h = History(user_email=session["user"], type="youtube", title=f"YouTube {vid}", summary=display_html, audio_filename=audio_name, flashcards=flashcards_str)
        db.session.add(h)
        db.session.commit()
        history_id = h.id

    return render_template("result.html", summary=display_html, metrics=metrics, audio=audio_name, flashcards=flashcards, history_id=history_id)

# ---------------- BACKGROUND PROCESSING ----------------
import threading
import uuid
import time

# In-memory job store: {job_id: {"status": "processing", "result_id": None, "error": None}}
JOBS = {}

def process_video_background(video_path, user_email, job_id):
    with app.app_context():
        try:
            JOBS[job_id]["status"] = "Extracting audio..."
            # Process video directly (extract audio in chunks)
            transcript = process_large_audio(video_path, job_id)
            
            if not transcript:
                JOBS[job_id]["status"] = "failed"
                JOBS[job_id]["error"] = "Failed to transcribe video."
                return

            if transcript.startswith("[ERROR:"):
                print(f"Job {job_id} failed with error: {transcript}")
                JOBS[job_id]["status"] = "failed"
                JOBS[job_id]["error"] = transcript
                return

            JOBS[job_id]["status"] = "Summarizing..."
            
            # ---------------- NO TRUNCATION ----------------
            # We now use chunked processing.
            # -----------------------------------------------

            system_prompt = (
                "You are an expert educational tutor. Create a HIGH-VALUE, COMPREHENSIVE study guide based on this video transcript. "
                "Your goal is to extract the maximum learning value from the content. "
                "Focus on the Core Concepts, Critical Explanations, and Key Takeaways. "
                "Avoid trivial details or fluff. Prioritize information that is essential for understanding. "
                "Provide deep explanations for the major topics found. "
                "Structure the response clearly. "
                "Use strict Markdown structure: \n"
                "# Main Topic\n"
                "## Sub-topic\n"
                "- **Key Concept**: Clear, valuable explanation...\n"
                "IMPORTANT: OUTPUT MUST BE STRICTLY IN ENGLISH. IF THE TRANSCRIPT IS NOT ENGLISH, TRANSLATE IT."
            )
            summary_raw = summarize_long_text(transcript, system_prompt)
            
            JOBS[job_id]["status"] = "Processing Output..."
            tts_text = clean_for_tts(summary_raw)
            display_html = format_summary_html(summary_raw)
            
            metrics = evaluate_summary_metrics(transcript, summary_raw)
            audio_name = generate_tts_audio(tts_text, f"summary_video_{job_id}.mp3")

            JOBS[job_id]["status"] = "Generating Flashcards..."
            flashcards_json = generate_flashcards(summary_raw)
            import json
            flashcards_str = json.dumps(flashcards_json) if isinstance(flashcards_json, dict) else None

            JOBS[job_id]["status"] = "Saving..."
            h = History(
                user_email=user_email, 
                type="video", 
                title=os.path.basename(video_path), 
                summary=display_html, 
                audio_filename=audio_name,
                flashcards=flashcards_str
            )
            db.session.add(h)
            db.session.commit()
            
            JOBS[job_id]["result_id"] = h.id
            JOBS[job_id]["status"] = "completed"

        except Exception as e:
            print(f"Job {job_id} failed: {e}")
            JOBS[job_id]["status"] = "failed"
            JOBS[job_id]["error"] = str(e)
        finally:
            try:
                if os.path.exists(video_path):
                    os.remove(video_path)
            except:
                pass

@app.route("/status/<job_id>")
def job_status(job_id):
    job = JOBS.get(job_id)
    if not job:
        return jsonify({"status": "unknown"}), 404
    return jsonify(job)

@app.route("/video_upload", methods=["POST"])
def video_upload():
    file = request.files.get("video_file")
    if not file or file.filename == "":
        flash("No file selected.")
        return redirect("/starter")

    if not allowed_video(file.filename):
        flash("Only MP4 files allowed.")
        return redirect("/starter")

    filename = secure_filename(file.filename)
    video_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    file.save(video_path)

    # Start background job
    job_id = str(uuid.uuid4())
    JOBS[job_id] = {"status": "queued", "result_id": None, "error": None}
    
    user_email = session.get("user")
    if not user_email:
        flash("Please login first.")
        return redirect("/")

    thread = threading.Thread(target=process_video_background, args=(video_path, user_email, job_id))
    thread.start()

    return render_template("processing.html", job_id=job_id)

# ---------------- HISTORY / VIEW ROUTES ----------------
@app.route("/history")
def history():
    if "user" not in session:
        return {"history": []}
    records = History.query.filter_by(user_email=session["user"]).order_by(History.created_at.desc()).all()
    return {
        "history": [
            {"id": r.id, "type": r.type, "title": r.title, "summary": r.summary[:120] + "...", "audio_filename": r.audio_filename, "created_at": r.created_at.strftime("%Y-%m-%d %H:%M")}
            for r in records
        ]
    }

@app.route("/history/<int:id>")
def view_history(id):
    if "user" not in session:
        return redirect("/")
    r = History.query.filter_by(id=id, user_email=session["user"]).first()
    if not r:
        return "Not found", 404
        
    # Lazy load flashcards if missing
    import json
    f_cards = None
    if r.flashcards:
        try:
            f_cards = json.loads(r.flashcards)
        except:
            f_cards = None
            
    if not f_cards:
        # Generate now based on the stored summary
        f_cards = generate_flashcards(r.summary)
        # Save back to DB
        try:
            r.flashcards = json.dumps(f_cards)
            db.session.commit()
        except Exception as e:
            print("Error saving lazy flashcards:", e)
            
    return render_template("result.html", summary=r.summary, audio=r.audio_filename, flashcards=f_cards, metrics=None, history_id=r.id)

# ---------------- FLASHCARD SUBMIT ----------------
@app.route("/submit_flashcards", methods=["POST"])
def submit_flashcards():
    data = request.get_json()
    mcq_ans = data.get("mcq_answers", {})
    summary = data.get("summary", "")
    history_id = data.get("history_id")
    
    f = None
    if history_id:
        # Try to load from DB for consistency
        r = History.query.filter_by(id=history_id).first()
        if r and r.flashcards:
             import json
             try:
                f = json.loads(r.flashcards)
             except:
                pass
    
    # Fallback to regeneration if not found (or guest)
    if not f:
        f = generate_flashcards(summary)
        
    score = 0
    total = 0
    # Scoring
    if f and "mcqs" in f:
        for i, mcq in enumerate(f.get("mcqs", [])):
            total += 1
            # Check answer
            # We trust the index sent by frontend matches the order in 'f'
            # If 'f' was loaded from DB, it should match exactly what frontend rendered.
            user_choice = mcq_ans.get(str(i))
            if user_choice == mcq.get("correct"):
                score += 1
                
    return {"score": score, "total": total}

# ---------------- RUN ----------------
if __name__ == "__main__":
    # ensure required folders exist
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(AUDIO_FOLDER, exist_ok=True)
    app.run(debug=True)
