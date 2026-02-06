import sqlite3
import os

def show_db():
    db_path = "users.db"
    if not os.path.exists(db_path):
        print(f"Database not found at {os.path.abspath(db_path)}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        print("\n=== USERS TABLE ===")
        cursor.execute("SELECT * FROM user")
        users = cursor.fetchall()
        if users:
            print(f"{'ID':<5} {'Email':<30} {'Password':<20}")
            print("-" * 60)
            for u in users:
                print(f"{u[0]:<5} {u[1]:<30} {u[2]:<20}")
        else:
            print("No users found.")

        print("\n=== HISTORY TABLE (Last 5) ===")
        cursor.execute("SELECT id, user_email, type, title, created_at FROM history ORDER BY id DESC LIMIT 5")
        history = cursor.fetchall()
        if history:
            print(f"{'ID':<5} {'User':<30} {'Type':<10} {'Title':<40} {'Created'}")
            print("-" * 110)
            for h in history:
                title = h[3][:37] + "..." if len(h[3]) > 37 else h[3]
                print(f"{h[0]:<5} {h[1]:<30} {h[2]:<10} {title:<40} {h[4]}")
        else:
            print("No history found.")

    except Exception as e:
        print(f"Error querying database: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    show_db()
