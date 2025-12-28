import sys
import subprocess
import os

def test():
    # Rick Roll
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    print(f"Testing {url}")
    cmd = [sys.executable, "-m", "yt_dlp", "-f", "bestaudio[abr<=64]", "-o", "test.m4a", url]
    subprocess.run(cmd)
    if os.path.exists("test.m4a"):
        print("Success")
        os.remove("test.m4a")
    else:
        print("Fail")

test()
