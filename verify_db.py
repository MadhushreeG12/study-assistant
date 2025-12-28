import sys
import os

# Add project root to path
sys.path.append(os.path.abspath("c:/Users/Manoj G/Downloads/updated_ai/updated_ai"))

from main import app, db, History, User

print("Checking DB Schema...")
with app.app_context():
    # Trigger the migration check in main.py by just importing (which runs the body code)
    # But specifically, we want to inspect the table to see if 'flashcards' is there.
    from sqlalchemy import inspect
    inspector = inspect(db.engine)
    columns = [col['name'] for col in inspector.get_columns('history')]
    
    if 'flashcards' in columns:
        print("✅ 'flashcards' column exists in 'history' table.")
    else:
        print("❌ 'flashcards' column MISSING.")

    # Optional: Test lazy load logic if we have any history
    # This requires a real user in session, which is hard to mock in a simple script without login
    # So we'll trust the unit test for column existence.
