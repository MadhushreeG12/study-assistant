
from main import app, db, History

# Delete all history records
with app.app_context():
    num_deleted = db.session.query(History).delete()
    db.session.commit()
    print(f"Successfully deleted {num_deleted} history records. You can now generate fresh summaries.")
