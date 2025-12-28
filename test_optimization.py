import time
import main

def test_optimization():
    print("Testing summarization speed...")
    # Simulate a long text (~60k chars)
    long_text = "This is a sentence to simulate video transcript content. " * 1000
    
    start = time.time()
    
    # We'll mock the actual API call to avoid cost/time for this test, 
    # OR we can let it fail gracefully if no API key, but we want to test the threading logic.
    # ideally we mock summarization to just sleep for 2s (simulating network)
    
    original_summarize = main.summarize_with_groq
    
    def mock_summarize(text, system_prompt, model=None, max_tokens=None):
        time.sleep(2) # simulate 2s API call
        return "Summary chunk"
        
    main.summarize_with_groq = mock_summarize
    
    try:
        # Base system prompt
        prompt = "Summarize this."
        summary = main.summarize_long_text(long_text, prompt)
        
        end = time.time()
        duration = end - start
        
        print(f"Total time: {duration:.2f} seconds")
        print(f"Summary length: {len(summary)}")
        
        # We expect duration to be close to 2s if parallelized perfectly with unlimited workers,
        # or slightly more with limited workers.
        # With 60k chars and chunk size 12k, we have ~5 chunks. 
        # 3 workers: 
        # Batch 1: 3 chunks run (2s)
        # Batch 2: 2 chunks run (2s)
        # Total approx 4s + overhead.
        
        # If sequential with 20s sleep: (2s + 20s) * 5 = 110s.
        
        if duration < 10:
            print("PASS: Speed optimization verified (Fast execution).")
        else:
            print("FAIL: Too slow, optimization might not be working.")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        main.summarize_with_groq = original_summarize

if __name__ == "__main__":
    test_optimization()
