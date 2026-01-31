from youtube_transcript_api import YouTubeTranscriptApi
import os

VIDEO_ID = "Hu4Yvq-g7_Y"
COOKIES_FILE = "cookies.txt"

if os.path.exists(COOKIES_FILE):
    print(f"Found {COOKIES_FILE}, testing with cookies...")
    try:
        # Note: The API accepts cookies as a file path in some versions or dict. 
        # Let's check if the installed version supports the file path argument directly.
        # Recent versions use 'cookies' argument.
        transcript = YouTubeTranscriptApi.get_transcript(VIDEO_ID, cookies=COOKIES_FILE)
        print("SUCCESS! Transcript fetched with cookies.")
        print(f"Length: {len(transcript)} entries.")
    except Exception as e:
        print(f"FAILED with cookies: {e}")
else:
    print("No cookies.txt found, skipping test.")
