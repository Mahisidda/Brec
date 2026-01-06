import os
import sys
import random
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
    """Fetches books from the Supabase 'books' table with randomization for variety."""
    if not supabase: return []
    try:
        # Query more books than needed, then randomly select from them
        # This ensures variety instead of always returning the same top N books
        pool_size = max(limit * 5, 100)  # Query 5x the limit, minimum 100 books
        
        res = supabase.table("books").select("isbn, title, author, year, publisher").limit(pool_size).execute()
        
        if not res.data:
            return []
        
        # Map to frontend-expected field names
        all_books = [
            {
                "Book_ID": book.get("isbn", ""),
                "Book_Title": book.get("title", "Unknown Title"),
                "author": book.get("author", "Unknown Author"),
                "year": book.get("year"),
                "publisher": book.get("publisher")
            }
            for book in res.data
        ]
        
        # Shuffle and return the requested limit
        random.shuffle(all_books)
        return all_books[:limit]
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
        # Get a larger pool and randomly select one
        res = supabase.table("user_vectors").select("user_id").limit(100).execute()
        if not res.data:
            return 0
        user_ids = [row['user_id'] for row in res.data]
        return random.choice(user_ids)
    except Exception as e:
        print(f"Error getting random user: {e}")
        return 0

def get_user_rated_books(user_id, context=None):
    """Placeholder: Returns books a user has already rated."""
    # Since we didn't upload the full ratings table to Supabase yet,
    # we return an empty list or a placeholder.
    return []

def recommend_by_books(liked_books, context=None):
    """Recommends books based on a list of liked book ISBNs."""
    if not supabase or not liked_books:
        # Fallback to popular books if no liked books provided
        return get_popular_books(limit=20)
    
    try:
        # Strategy: Find users who liked similar books, then get their other favorites
        # Step 1: Find users who rated these books highly
        user_res = supabase.table("ratings").select("user_id").in_("isbn", liked_books).eq("rating", 5).limit(50).execute()
        
        if not user_res.data:
            # No users found who liked these books, return diverse popular books
            return get_popular_books(limit=20)
        
        # Get unique user IDs
        user_ids = list(set([r['user_id'] for r in user_res.data]))
        
        # Step 2: Get books highly rated by these users (excluding the ones already liked)
        recs_res = supabase.table("ratings").select("isbn").in_("user_id", user_ids[:20]).eq("rating", 5).not_.in_("isbn", liked_books).limit(100).execute()
        
        if not recs_res.data:
            # Fallback: return popular books excluding liked ones
            return get_popular_books(limit=20)
        
        # Get unique ISBNs
        recommended_isbns = list(set([r['isbn'] for r in recs_res.data]))
        
        # Step 3: Fetch book details for recommended ISBNs
        if not recommended_isbns:
            return get_popular_books(limit=20)
        
        # Get book details from books table
        books_res = supabase.table("books").select("isbn, title, author, year, publisher").in_("isbn", recommended_isbns[:50]).execute()
        
        recommendations = []
        seen_isbns = set()
        
        for book in (books_res.data or []):
            isbn = book.get("isbn", "")
            if isbn and isbn not in seen_isbns and isbn not in liked_books:
                recommendations.append({
                    "Book_ID": isbn,
                    "Book_Title": book.get("title", "Unknown Title"),
                    "author": book.get("author", "Unknown Author"),
                    "year": book.get("year"),
                    "publisher": book.get("publisher")
                })
                seen_isbns.add(isbn)
        
        # If we don't have enough recommendations, add popular books (excluding liked ones)
        if len(recommendations) < 20:
            popular = get_popular_books(limit=50)
            for book in popular:
                if book.get("Book_ID") not in seen_isbns and book.get("Book_ID") not in liked_books:
                    recommendations.append(book)
                    seen_isbns.add(book.get("Book_ID"))
                if len(recommendations) >= 20:
                    break
        
        # Shuffle and return top 20
        random.shuffle(recommendations)
        return recommendations[:20]
        
    except Exception as e:
        print(f"Error in recommend_by_books: {e}")
        import traceback
        print(traceback.format_exc())
        # Fallback to popular books
        return get_popular_books(limit=20)