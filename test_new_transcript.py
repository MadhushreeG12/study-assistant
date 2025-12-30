from main import get_transcript
import sys

# Test with a video that definitely has auto-generated captions but might not have manual ones,
# or a foreign video to test translation.
# Video: "How to Get Your Brain to Focus" (Chris Bailey) - Standard TEDx
VIDEO_ID = "Hu4Yvq-g7_Y" 

try:
    print(f"Testing get_transcript for {VIDEO_ID}...")
    print(f"Testing get_transcript for {VIDEO_ID}...")
    # Now valid to call main.py function
    text = get_transcript(VIDEO_ID)
    
    if text:
        print("SUCCESS: Transcript retrieved!")
        print(f"Length: {len(text)} characters")
        print(f"Snippet: {text[:200]}...")
    else:
        print("FAILURE: returned None")
except Exception as e:
    print(f"FAILURE: Exception occurred: {e}")
    import traceback
    traceback.print_exc()
