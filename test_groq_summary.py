
import os
import requests
import time

# Use the key from main.py or env
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "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")
GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"

def summarize_with_groq(text, system_prompt, model="llama-3.1-8b-instant", max_tokens=700):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    user_content = text + "\n\n(IMPORTANT: Please provide the response in English ONLY, regardless of the original language of the text above.)"
    
    data = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ],
        "temperature": 0.3,
        "max_tokens": max_tokens
    }

    print(f"Testing model: {model}")
    print(f"Input text length: {len(text)}")
    
    start = time.time()
    try:
        resp = requests.post(GROQ_CHAT_URL, headers=headers, json=data, timeout=60)
        print(f"Status Code: {resp.status_code}")
        print(f"Time taken: {time.time() - start:.2f}s")
        
        result = resp.json()
        if resp.status_code != 200:
            print(f"Error Response: {result}")
            return
        
        content = result["choices"][0]["message"]["content"]
        print(f"Response Length: {len(content)}")
        print(f"Response Content: {content!r}")
        
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    # Create a dummy large text (12000 chars)
    dummy_text = "This is a test sentence related to computer science and artificial intelligence. " * 200
    print(f"Generated text of length: {len(dummy_text)}")
    
    prompt = "Summarize this text."
    summarize_with_groq(dummy_text, prompt)
