import os
import requests
import subprocess

# Key from main.py
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "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")
GROQ_ASR_URL = "https://api.groq.com/openai/v1/audio/transcriptions"

AUDIO_PATH = "test_asr.mp3"

def generate_test_audio():
    # Generate 2s silence mp3
    cmd = [
        "ffmpeg", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", 
        "-t", "2", "-q:a", "4", "-y", AUDIO_PATH
    ]
    subprocess.run(cmd, check=True, stderr=subprocess.PIPE)

def audio_to_text(audio_file):
    print(f"Testing ASR with key: {GROQ_API_KEY[:5]}...{GROQ_API_KEY[-5:]}")
    try:
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
        with open(audio_file, "rb") as f:
            response = requests.post(
                GROQ_ASR_URL,
                headers=headers,
                files={"file": f},
                data={"model": "whisper-large-v3"},
                timeout=30
            )
        result = response.json()
        print(f"Status Code: {response.status_code}")
        print(f"Response: {result}")
        if response.status_code != 200:
            print("ASR connection failed.")
            return ""
        return result.get("text", "")
    except Exception as e:
        print(f"ASR Exception: {e}")
        return ""

if __name__ == "__main__":
    try:
        generate_test_audio()
        text = audio_to_text(AUDIO_PATH)
        print(f"Transcribed Text: '{text}'")
        # Cleanup
        if os.path.exists(AUDIO_PATH):
            os.remove(AUDIO_PATH)
    except Exception as e:
        print(f"Top level error: {e}")
