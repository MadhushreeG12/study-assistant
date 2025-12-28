import sys
import os
import json

# Add project root to path
sys.path.append(os.path.abspath("c:/Users/Manoj G/Downloads/updated_ai/updated_ai"))

from main import generate_flashcards

print("Testing MCQ Content Quality...")

summary = """
The Python programming language was created by Guido van Rossum and was first released in 1991. 
Python is designed to be highly readable, using indentation to define code blocks. 
It supports multiple programming paradigms, including structured, object-oriented, and functional programming.
"""

print(f"Input Summary: {summary.strip()}")

try:
    result = generate_flashcards(summary)
    
    if isinstance(result, dict) and "mcqs" in result:
        print("\n[OK] MCQ Generation Successful")
        # Check if content looks real (not "...")
        mcq1 = result["mcqs"][0]
        q_text = mcq1.get("question", "")
        opt_text = mcq1.get("options", [])
        
        print(f"Q1: {q_text}")
        print(f"Options: {opt_text}")
        
        if "..." in q_text or "..." in str(opt_text):
            print("[FAIL] Content contains placeholders!")
        else:
            print("[SUCCESS] Content looks valid.")
            
    else:
        print("[FAIL] MCQ Generation Failed (Invalid Structure)")
        print(result)

except Exception as e:
    print(f"[ERROR] MCQ Generation Error: {e}")
