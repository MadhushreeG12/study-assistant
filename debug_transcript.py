try:
    from youtube_transcript_api import YouTubeTranscriptApi
    print("Import successful")
    print("Attributes:", dir(YouTubeTranscriptApi))
    try:
        t = YouTubeTranscriptApi.get_transcript("kqtD5dpn9C8", languages=['en'])
        print("Transcript fetch successful, length:", len(t))
    except Exception as e:
        print("Transcript fetch failed:", e)
except ImportError:
    print("Import failed")
