from pymongo import MongoClient
import os
from dotenv import load_dotenv
import certifi

def test_connection():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(base_dir, ".env")
    print(f"DEBUG: Reading .env from {env_path}")
    load_dotenv(env_path, override=True)
    
    mongo_uri = os.getenv("MONGO_URI")
    print(f"DEBUG: MONGO_URI from env: '{mongo_uri}'")
    
    if not mongo_uri:
        mongo_uri = "mongodb+srv://naman:naman@cluster0.wfqx2hc.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
        print("DEBUG: Using fallback URI")
    
    print(f"DEBUG: Final URI (masked): {mongo_uri.split('@')[-1]}")
    
    client = MongoClient(mongo_uri, tlsCAFile=certifi.where(), serverSelectionTimeoutMS=5000)
    try:
        client.admin.command('ping')
        print("✅ Ping success!")
        db = client["riasec_db"]
        print(f"✅ Collections: {db.list_collection_names()}")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    test_connection()
