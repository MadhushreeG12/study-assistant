import os
import subprocess
import glob
import uuid

# Mock config
AUDIO_PATH = "test_audio.mp3"
CHUNK_DURATION_SEC = 10 # Short chunk for testing

def test_ffmpeg_logic():
    print("--- GENERATING TEST AUDIO ---")
    # Generate 30s silence mp3 using ffmpeg
    cmd_gen = [
        "ffmpeg", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", 
        "-t", "30", "-q:a", "4", "-y", AUDIO_PATH
    ]
    try:
        subprocess.run(cmd_gen, check=True)
        print(f"Generated {AUDIO_PATH}")
    except Exception as e:
        print(f"Failed to generate test audio: {e}")
        return

    print("\n--- TESTING FFPROBE ---")
    cmd_dur = [
        "ffprobe", "-v", "error", 
        "-show_entries", "format=duration", 
        "-of", "default=noprint_wrappers=1:nokey=1", 
        AUDIO_PATH
    ]
    try:
        result = subprocess.run(cmd_dur, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        print(f"STDOUT: {result.stdout.strip()}")
        print(f"STDERR: {result.stderr.strip()}")
        duration = float(result.stdout.strip())
        print(f"Duration detected: {duration}")
    except Exception as e:
        print(f"FFPROBE FAILED: {e}")
        duration = 0

    print("\n--- TESTING SPLIT LOGIC ---")
    base_name = AUDIO_PATH.rsplit(".", 1)[0]
    chunk_pattern = f"{base_name}_chunk_%03d.mp3"
    
    cmd_split = [
        "ffmpeg", "-i", AUDIO_PATH, 
        "-f", "segment", 
        "-segment_time", str(CHUNK_DURATION_SEC), 
        "-c:a", "libmp3lame", "-b:a", "64k", 
        "-y", "-loglevel", "error", 
        chunk_pattern
    ]
    
    try:
        print(f"Command: {' '.join(cmd_split)}")
        subprocess.run(cmd_split, check=True)
        print("Split command success.")
    except Exception as e:
        print(f"SPLIT FAILED: {e}")

    print("\n--- CHECKING FILES ---")
    pattern_glob = f"{base_name}_chunk_*.mp3"
    found_chunks = sorted(glob.glob(pattern_glob))
    print(f"Found chunks: {found_chunks}")
    
    if len(found_chunks) == 0:
        print("FAILURE: No chunks found.")
    else:
        print("SUCCESS: Chunks found.")

    # Cleanup
    try:
        os.remove(AUDIO_PATH)
        for f in found_chunks:
            os.remove(f)
    except:
        pass

if __name__ == "__main__":
    test_ffmpeg_logic()
