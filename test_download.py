import subprocess
import os

VIDEO_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ" # Rick Roll (Safe, short)

import sys

def test_download():
    print(f"Testing download for {VIDEO_URL}")
    outname = "test_download_video.m4a"
    
    # Construct command line for yt-dlp
    # Using the same options as intended in main.py
    cmd = [
        sys.executable, "-m", "yt_dlp",
        "-f", "bestaudio[abr<=64]/bestaudio/best",
        "-o", outname,
        "--no-check-certificate",
        "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "--verbose",
        VIDEO_URL
    ]
    
    print(f"Command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        print("STDOUT:", result.stdout)

        print("STDERR:", result.stderr)
        
        if result.returncode == 0 and os.path.exists(outname):
            print("SUCCESS: Downloaded file.")
            os.remove(outname)
        else:
            print("FAILURE: Return code", result.returncode)
    except Exception as e:
        print(f"EXCEPTION: {e}")

if __name__ == "__main__":
    test_download()
