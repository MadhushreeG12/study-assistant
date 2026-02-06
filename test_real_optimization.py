import time
import main

def test_logic():
    print("--- Testing Logic for Optimization ---")
    
    # Mock the actual API call
    original_api = main.summarize_with_groq
    
    call_log = []
    
    def mock_api(text, *args, **kwargs):
        call_log.append(len(text))
        return "Summary"
        
    main.summarize_with_groq = mock_api
    
    try:
        # Case 1: Short text (50k chars) -> Should be Single Shot
        print("\nTest 1: 50,000 chars (Should be Single Shot)...")
        call_log.clear()
        text_short = "a" * 50000
        main.summarize_long_text(text_short, "prompt")
        
        if len(call_log) == 1 and call_log[0] == 50000:
            print("PASS: Single shot used.")
        else:
            print(f"FAIL: Expected 1 call of size 50000, got {call_log}")

        # Case 2: Long text (350k chars) -> Should be Chunked (Chunk size 50k)
        print("\nTest 2: 350,000 chars (Should be Chunked)...")
        call_log.clear()
        text_long = "a" * 350000
        main.summarize_long_text(text_long, "prompt")
        
        expected_chunks = 350000 // 50000
        if len(call_log) == expected_chunks:
            print(f"PASS: Chunked correctly into {len(call_log)} calls.")
        else:
            print(f"FAIL: Expected {expected_chunks} chunks, got {len(call_log)}")
            
    finally:
        main.summarize_with_groq = original_api

if __name__ == "__main__":
    test_logic()
