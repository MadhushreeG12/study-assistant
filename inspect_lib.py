from youtube_transcript_api import YouTubeTranscriptApi
import youtube_transcript_api

print(f"Version: {youtube_transcript_api.__file__}")
print(dir(YouTubeTranscriptApi))
try:
    print("Calling list method...")
    result = YouTubeTranscriptApi.list('Hu4Yvq-g7_Y')
    print(f"Result type: {type(result)}")
    print(f"Result: {result}")
except Exception as e:
    print(f"Error calling list: {e}")
