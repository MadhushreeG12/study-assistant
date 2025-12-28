import sys
import os
import json

# Add project root to path
sys.path.append(os.path.abspath("c:/Users/Manoj G/Downloads/updated_ai/updated_ai"))

from main import generate_flashcards

print("Testing Short Answer Removal...")

summary = "Python is a programming language."

try:
    result = generate_flashcards(summary)
    
    if isinstance(result, dict):
        if "short_questions" in result:
             print("[FAIL] 'short_questions' key still exists in response!")
             print(result.keys())
        elif "mcqs" in result:
             print("[OK] Only MCQs found.")
             print(f"Number of MCQs: {len(result['mcqs'])}")
        else:
             print("[FAIL] No MCQs found either?")
    else:
        print("[FAIL] Invalid response structure")

except Exception as e:
    print(f"[ERROR] {e}")
