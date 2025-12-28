
from pytube import YouTube
import sys

url = "https://www.youtube.com/watch?v=Hu4Yvq-g7_Y"
print(f"Testing pytube logic for {url}")

try:
    yt = YouTube(url, use_oauth=False, allow_oauth_cache=True)
    stream = yt.streams.filter(only_audio=True).first()
    if stream:
        print("Found stream:", stream)
        out = stream.download(filename="test_pytube.mp4")
        print(f"Download success: {out}")
    else:
        print("No audio stream found")
except Exception as e:
    print(f"Pytube Error: {e}")
