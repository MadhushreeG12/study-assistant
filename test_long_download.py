import sys
import subprocess
import os
import time

VIDEO_URL = "https://www.youtube.com/watch?v=xuCn8ux2gbs" # ~19.5 mins

def test_long_download():
    print(f"Testing download for {VIDEO_URL}")
    outname = "test_long_video.m4a"
    
    # Use the EXACT same flags as main.py
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
    start_time = time.time()
    
    try:
        # main.py does NOT use timeout, but let's see if it hangs.
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        print(f"Finished in {time.time() - start_time:.2f}s")
        print("Standard Output:\n", result.stdout[-500:]) # Show tail
        print("Standard Error:\n", result.stderr[-500:])
        
        if result.returncode == 0 and os.path.exists(outname):
            size = os.path.getsize(outname)
            print(f"SUCCESS: Downloaded file. Size: {size/1024/1024:.2f} MB")
            os.remove(outname)
        else:
            print(f"FAILURE: Return code {result.returncode}")
    except Exception as e:
        print(f"EXCEPTION: {e}")

if __name__ == "__main__":
    if os.path.exists("test_long_video.m4a"):
        os.remove("test_long_video.m4a")
    test_long_download()
