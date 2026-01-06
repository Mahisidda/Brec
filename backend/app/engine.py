import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

# This forces Python to find the .env file in the backend folder
# no matter where you run the script from.
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(os.path.join(BASE_DIR, ".env"))

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print(f"❌ CRITICAL ERROR: Env vars not loaded from {os.path.join(BASE_DIR, '.env')}")
    sys.exit(1) # Stop the app immediately with a clear error

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
print("✅ Connected to Supabase successfully.")

# --- API REQUIRED FUNCTIONS ---

def get_popular_books(limit=20, context=None):
    """Fetches books from the Supabase 'books' table."""
    if not supabase: return []
    try:
        # We use the column names we verified in your Books.csv
        res = supabase.table("books").select("isbn, title, author, year, publisher").limit(limit).execute()
        # Map to frontend-expected field names
        return [
            {
                "Book_ID": book.get("isbn", ""),
                "Book_Title": book.get("title", "Unknown Title"),
                "author": book.get("author", "Unknown Author"),
                "year": book.get("year"),
                "publisher": book.get("publisher")
            }
            for book in (res.data or [])
        ]
    except Exception as e:
        print(f"Error in get_popular_books: {e}")
        return []

def recommend_for_user(user_id, context=None):
    """Finds similar users via vector search and returns recommendations."""
    if not supabase: return []
    try:
        # 1. Get the target user's embedding
        res = supabase.table("user_vectors").select("embedding").eq("user_id", user_id).single().execute()
        if not res.data:
            return get_popular_books(limit=5) # Fallback to popular if user not found

        # 2. Search for similar users using the RPC function we created
        # match_users is the SQL function you ran in the Supabase Editor
        similar_users = supabase.rpc('match_users', {
            'query_embedding': res.data['embedding'],
            'match_threshold': 0.5,
            'match_count': 5
        }).execute()

        # 3. For now, return popular books as a placeholder 
        # (In a full version, you'd query what those similar users liked)
        return get_popular_books(limit=10)
    except Exception as e:
        print(f"Error in recommend_for_user: {e}")
        return []

def get_random_user_id(context=None):
    """Returns a random user_id from the database."""
    if not supabase: return 0
    try:
        res = supabase.table("user_vectors").select("user_id").limit(1).execute()
        return res.data[0]['user_id'] if res.data else 0
    except Exception as e:
        print(f"Error getting random user: {e}")
        return 0

def get_user_rated_books(user_id, context=None):
    """Placeholder: Returns books a user has already rated."""
    # Since we didn't upload the full ratings table to Supabase yet,
    # we return an empty list or a placeholder.
    return []

def recommend_by_books(liked_books, context=None):
    """Placeholder: Recommends books based on a list of ISBNs."""
    return get_popular_books(limit=10)