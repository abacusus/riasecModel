import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
import certifi

async def test_connection():
    # Use absolute path for .env
    base_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(base_dir, ".env")
    print(f"DEBUG: Looking for .env at: {env_path}")
    load_dotenv(env_path)
    
    mongo_uri = os.getenv("MONGO_URI")
    print(f"DEBUG: MONGO_URI from env: '{mongo_uri}'")
    
    if not mongo_uri:
        # Fallback to the one in app.py if env fails
        mongo_uri = "mongodb+srv://naman:naman@cluster0.wfqx2hc.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
        print(f"DEBUG: Using fallback URI")
    
    print(f"DEBUG: Final URI being used: {mongo_uri}")
    client = AsyncIOMotorClient(mongo_uri, tlsCAFile=certifi.where())
    try:
        # The ping command is cheap and does not require auth.
        await client.admin.command('ping')
        print("✅ Pinged your deployment. You successfully connected to MongoDB!")
        
        # Check database access
        db = client["riasec_db"]
        collections = await db.list_collection_names()
        print(f"✅ Successfully accessed 'riasec_db'. Collections: {collections}")
        
    except Exception as e:
        print(f"❌ Could not connect to MongoDB: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(test_connection())
