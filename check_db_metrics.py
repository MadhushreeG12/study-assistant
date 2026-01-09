
import sys
import os
import sqlite3
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from rouge_score import rouge_scorer
import re

# Add project root to path
sys.path.append(os.path.abspath("c:/Users/Manoj G/Downloads/updated_ai/updated_ai"))

def clean_html(raw_html):
    cleanr = re.compile('<.*?>')
    cleantext = re.sub(cleanr, '', raw_html)
    return cleantext

def calculate_raw_metrics(original_text, summary_text):
    scorer = rouge_scorer.RougeScorer(["rouge1", "rouge2", "rougeL"], use_stemmer=True)
    scores = scorer.score(original_text, summary_text)
    
    r1 = scores["rouge1"].fmeasure
    r2 = scores["rouge2"].fmeasure
    rl = scores["rougeL"].fmeasure
    
    try:
        vectorizer = TfidfVectorizer(stop_words='english').fit([original_text, summary_text])
        v = vectorizer.transform([original_text, summary_text])
        cosine = cosine_similarity(v[0], v[1])[0][0]
    except:
        cosine = 0.0
        
    return r1, r2, rl, cosine

def main():
    db_path = "c:/Users/Manoj G/Downloads/updated_ai/updated_ai/users.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get last 3 history items
    cursor.execute("SELECT id, type, title, summary FROM history ORDER BY id DESC LIMIT 3")
    rows = cursor.fetchall()
    
    print(f"{'ID':<5} {'Type':<10} {'R1':<8} {'R2':<8} {'RL':<8} {'Cos':<8}")
    print("-" * 60)

    # For accurate recalculation we ideally need the ORIGINAL text.
    # But we don't store original text in DB, only summary. 
    # Wait, we can't calculate ROUGE without the reference/original text.
    # The 'History' table doesn't have the original text.
    
    # Checking if we can re-download or if there's a cached way.
    # If we can't get original text, we can't reproduce the exact numbers 
    # that produced the 9.9.
    
    # However, we can use a dummy "Original" vs "Summary" test 
    # using the summary itself split in half vs full? No, that's cheating.
    
    # HACK: If we can't get original, we'll generate a dummy sample 
    # to see typical values for general text summarization.
    # OR better: The user might have a file we can process.
    
    # Let's check if there are files in 'uploads/' we can read.
    pass

if __name__ == "__main__":
    # Since we realized we might not have original text stored, 
    # we'll do a synthetic test with a known text/summary pair 
    # to calibrate our formula.
    
    article_text = """
    The Python programming language was created by Guido van Rossum and was first released in 1991. 
    Python is designed to be highly readable, using indentation to define code blocks. 
    It supports multiple programming paradigms, including structured, object-oriented, and functional programming.
    Python is dynamically typed and garbage-collected. It supports modules and packages, 
    which encourages program modularity and code reuse.
    """
    
    summary_text = """
    Python is a readable, high-level programming language created by Guido van Rossum in 1991.
    It supports structured, object-oriented, and functional paradigms.
    Features include dynamic typing, garbage collection, and modularity.
    """
    
    print("Testing with Sample Text...")
    r1, r2, rl, cosine = calculate_raw_metrics(article_text, summary_text)
    
    print(f"Sample R1:  {r1:.4f}")
    print(f"Sample R2:  {r2:.4f}")
    print(f"Sample RL:  {rl:.4f}")
    print(f"Sample Cos: {cosine:.4f}")
    
    # Test strictness scenarios
    # Scenario: Good Summary (The one above is decent)
    

    print("\n--- NEW Linear Interpolation Formula Test ---")
    
    def calculate_norm(value, min_val, max_val):
        if value < min_val: return 0.0
        if value > max_val: return 1.0
        return (value - min_val) / (max_val - min_val)

    def simulate_new_score(r1, r2, rl, cos):
        # THRESHOLDS (Min, Max)
        # These define the window where the quality actually matters.
        # Below min = 0 points contributed
        # Above max = Max points contributed
        TR_R1 = (0.15, 0.45)
        TR_R2 = (0.05, 0.20)
        TR_RL = (0.12, 0.40)
        TR_COS = (0.10, 0.55)
        
        n_r1 = calculate_norm(r1, *TR_R1)
        n_r2 = calculate_norm(r2, *TR_R2)
        n_rl = calculate_norm(rl, *TR_RL)
        n_cos = calculate_norm(cos, *TR_COS)
        
        avg_norm = (n_r1 + n_r2 + n_rl + n_cos) / 4.0
        
        # Base 8.0, Max Variance 1.9
        # Result: 8.0 to 9.9
        final_score = 8.0 + (avg_norm * 1.9)
        return final_score, avg_norm

    score, norm = simulate_new_score(r1, r2, rl, cosine)
    print(f"Score for Sample (Decent): {score:.2f} (Norm Avg: {norm:.2f})")
    
    # Scenario: Perfect
    s_perf, n_perf = simulate_new_score(1.0, 1.0, 1.0, 1.0)
    print(f"Score for Perfect:         {s_perf:.2f} (Norm Avg: {n_perf:.2f})")
    
    # Scenario: Weak (half stats)
    # r1~0.29, r2~0.15, rl~0.25, cos~0.22
    s_weak, n_weak = simulate_new_score(r1/2, r2/2, rl/2, cosine/2)
    print(f"Score for Weak:            {s_weak:.2f} (Norm Avg: {n_weak:.2f})")
    
    # Scenario: Very Bad (Almost nonsense)
    s_bad, n_bad = simulate_new_score(0.1, 0.02, 0.1, 0.05)
    print(f"Score for Very Bad:        {s_bad:.2f} (Norm Avg: {n_bad:.2f})")

if __name__ == "__main__":
    main()
