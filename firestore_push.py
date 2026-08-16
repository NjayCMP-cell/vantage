import firebase_admin
from firebase_admin import credentials, firestore
from datetime import date

_db = None

def _init():
    global _db
    if not firebase_admin._apps:
        cred = credentials.Certificate("serviceAccountKey_vantage.json")
        firebase_admin.initialize_app(cred)
    _db = firestore.client()

def push_results(results: list):
    _init()
    today = date.today().isoformat()
    doc_ref = _db.collection("daily_matches").document(today)
    doc_ref.set({
        "date": today,
        "matches": results,
        "updated_at": firestore.SERVER_TIMESTAMP,
    })
    print(f"[Firestore] Pushed {len(results)} matches for {today}")
