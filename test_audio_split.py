
import os
import time
import main
import glob

def test_audio_split():
    print("Testing audio splitting optimization...")
    
    # Find a suitable m4a file
    m4a_files = glob.glob("*.m4a")
    if not m4a_files:
        print("No .m4a files found for testing.")
        # Create a dummy one or exit?
        # Try finding mp3
        mp3_files = glob.glob("*.mp3")
        if mp3_files:
            test_file = mp3_files[0]
        else:
            print("No audio files found. Skipping.")
            return
    else:
        test_file = m4a_files[0]
        
    print(f"Using file: {test_file} ({os.path.getsize(test_file)/1024/1024:.2f} MB)")
    
    # Mock audio_to_text
    def mock_asr(filename):
        print(f"[MOCK ASR] Processing {filename}")
        if not os.path.exists(filename):
            print(f"ERROR: Chunk {filename} does not exist!")
            return ""
        return " Mock Text "
        
    main.audio_to_text = mock_asr
    
    # Determine job id
    job_id = "test_job_1"
    main.JOBS[job_id] = {"status": "init"}
    
    start = time.time()
    
    transcript = main.process_large_audio(test_file, job_id)
    
    end = time.time()
    duration = end - start
    
    print(f"Total time: {duration:.2f}s")
    print(f"Result: {transcript[:100]}...")
    
    if "Mock Text" in transcript:
        print("PASS: Splitting and transcription flow worked.")
    else:
        print("FAIL: Transcript empty or error.")
        
    print(f"Job Status: {main.JOBS[job_id]}")

if __name__ == "__main__":
    test_audio_split()
