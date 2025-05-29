import os
import random
import json
import hashlib
import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from .matrix import load_sparse_matrix
from .redis_client import redis_client
import faiss


DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')


def load_all_data():
    """Loads matrix, mappings, and title lookup once."""
    print("[DEBUG] engine.py: load_all_data() called.")
    ratings_csv = os.path.join(DATA_DIR, 'Ratings.csv')
    books_csv = os.path.join(DATA_DIR, 'Books.csv')
    print(f"[DEBUG] engine.py: load_all_data() - ratings_csv path: {ratings_csv}")
    print(f"[DEBUG] engine.py: load_all_data() - books_csv path: {books_csv}")
    return load_sparse_matrix(ratings_csv, books_csv)


def get_random_user_id(user_map):
    """Pick a random real user ID from the dataset."""
    return int(random.choice(list(user_map.keys())))


def get_user_rated_books(user_id, context):
    """Returns all books rated by a specific user."""
    user_map = context['user_map']
    rev_book_map = context['rev_book_map']
    isbn_to_details = context['isbn_to_details']
    matrix = context['matrix']

    if user_id not in user_map:
        return None

    u_idx = user_map[user_id]
    row = matrix[u_idx]
    cols = row.nonzero()[1]
    vals = row.data
    
    results = []
    for col, val in zip(cols, vals):
        isbn = rev_book_map[col]
        details = isbn_to_details.get(isbn, {})
        results.append({
            'Book_ID': isbn,
            'Book_Title': details.get('Title', 'Unknown Title'),
            'Author': details.get('Author', 'Unknown Author'),
            'Rating': float(val),
            'Goodreads_URL': f'https://www.goodreads.com/search?q={isbn}'
        })
    return results


def recommend_for_user(user_id, context, k=10, top_n=3, similarity_threshold=0.1):
    """Collaborative Filtering: recommend top-N books for an existing user."""
    user_map = context['user_map']
    rev_book_map = context['rev_book_map']
    isbn_to_details = context['isbn_to_details']
    matrix = context['matrix']

    if user_id not in user_map:
        return []

    u_idx = user_map[user_id]
    user_vector = matrix[u_idx]

    sim_vec = cosine_similarity(user_vector, matrix).flatten()
    eligible = np.where(sim_vec > similarity_threshold)[0]
    if len(eligible) > k:
        neighbors = eligible[np.argpartition(sim_vec[eligible], -k)[-k:]]
        neighbors = neighbors[np.argsort(sim_vec[neighbors])[::-1]]
    else:
        neighbors = eligible

    if len(neighbors) == 0:
        return []

    seen = set(matrix[u_idx].nonzero()[1])
    nonzeros_cache = {n: matrix[n].nonzero()[1] for n in neighbors}
    candidate_books = set().union(*nonzeros_cache.values()) - seen

    if not candidate_books:
        return []

    candidate_idxs = list(candidate_books)
    ratings_submatrix = matrix[:, candidate_idxs]
    numerators = sim_vec @ ratings_submatrix
    denominators = np.array([
        np.dot(sim_vec, (ratings_submatrix[:, i] > 0).astype(float))
        for i in range(ratings_submatrix.shape[1])
    ])

    preds = {}
    for i, b in enumerate(candidate_idxs):
        if denominators[i] > 0:
            preds[b] = numerators[i] / denominators[i]

    top = sorted(preds.items(), key=lambda x: x[1], reverse=True)[:top_n]
    
    results = []
    for b_idx, score in top:
        isbn = rev_book_map[b_idx]
        details = isbn_to_details.get(isbn, {})
        results.append({
            'Book_ID': isbn,
            'Book_Title': details.get('Title', 'Unknown Title'),
            'Author': details.get('Author', 'Unknown Author'),
            'Recommendation_Score': float(score),
            'Goodreads_URL': f'https://www.goodreads.com/search?q={isbn}'
        })
    return results



def recommend_by_books(liked_books, context, k=10, top_n=5, similarity_threshold=0.1):
    """FAISS-accelerated pseudo-user collaborative filtering."""
    cache_key = cache_key_for_recommendation(liked_books, top_n, k, similarity_threshold)
    cached = redis_client.get(cache_key)
    if cached:
        return json.loads(cached.decode("utf-8"))

    matrix = context['matrix']
    book_map = context['book_map']
    rev_book_map = context['rev_book_map']
    isbn_to_details = context['isbn_to_details']
    faiss_index = context['faiss_index']

    n_books = matrix.shape[1]
    liked_idxs = [book_map[isbn] for isbn in liked_books if isbn in book_map]
    if not liked_idxs:
        return []

    # Build normalized pseudo-user vector
    pseudo = np.zeros((1, n_books), dtype=np.float32)
    for idx in liked_idxs:
        pseudo[0, idx] = 10.0
    faiss.normalize_L2(pseudo)

    # Query FAISS for top-k similar users
    # D are distances (lower is better), I are indices of neighbors
    distances, neighbor_indices = faiss_index.search(pseudo, k + len(liked_idxs)) # search for more to account for self/already liked

    # Convert distances to similarities (e.g., 1 / (1 + distance) or exp(-distance))
    # Ensure sim_vec aligns with the actual neighbors used.
    # Filter out the pseudo-user itself if it appears in neighbors, and any invalid indices like -1
    
    valid_neighbor_indices = []
    similarities_to_valid_neighbors = []

    temp_sim_vec = 1.0 / (1.0 + distances.flatten()) # Example similarity conversion

    for i, neighbor_idx in enumerate(neighbor_indices.flatten()):
        if neighbor_idx != -1: # FAISS can return -1 if not enough neighbors found
            # Potentially, also check if neighbor_idx corresponds to the pseudo-user's own items if matrix stores users directly
            valid_neighbor_indices.append(neighbor_idx)
            similarities_to_valid_neighbors.append(temp_sim_vec[i])
    
    if not valid_neighbor_indices:
        return []

    neighbors = np.array(valid_neighbor_indices)
    sim_vec = np.array(similarities_to_valid_neighbors)

    # Refine k if we found fewer valid neighbors
    current_k = len(neighbors)
    if current_k == 0:
        return []

    # Get books rated by neighbors, excluding liked books
    nonzeros_cache = {n: matrix[n].nonzero()[1] for n in neighbors}
    candidate_books = set().union(*nonzeros_cache.values()) - set(liked_idxs)
    if not candidate_books:
        return []

    candidate_idxs = list(candidate_books)
    
    # Create submatrix of ratings from THE K NEIGHBORS for the candidate books
    # Shape: (current_k, num_candidate_books)
    ratings_submatrix_k_neighbors = matrix[neighbors, :][:, candidate_idxs]

    # Calculate weighted sum of ratings from neighbors
    # sim_vec is (current_k,), ratings_submatrix_k_neighbors is (current_k, num_candidate_books)
    # Resulting numerators shape: (num_candidate_books,)
    numerators = sim_vec @ ratings_submatrix_k_neighbors.toarray() # Ensure dense for matmul if sim_vec is dense

    # Calculate denominators: sum of similarities of neighbors who rated each candidate book
    denominators = np.zeros(len(candidate_idxs), dtype=np.float32)
    for i in range(len(candidate_idxs)):
        # For candidate book `i` (which is candidate_idxs[i]), find which of the k neighbors rated it
        rated_this_book_mask = ratings_submatrix_k_neighbors[:, i].toarray().flatten() > 0
        denominators[i] = np.sum(sim_vec[rated_this_book_mask])

    preds = {}
    for i, book_original_idx in enumerate(candidate_idxs):
        if denominators[i] > 0:
            preds[book_original_idx] = numerators[i] / denominators[i]

    top = sorted(preds.items(), key=lambda x: x[1], reverse=True)[:top_n]
    result = []
    for book_original_idx, score in top:
        isbn = rev_book_map[book_original_idx]
        details = isbn_to_details.get(isbn, {})
        result.append({
            'Book_ID': isbn,
            'Book_Title': details.get('Title', 'Unknown Title'),
            'Author': details.get('Author', 'Unknown Author'),
            'Recommendation_Score': float(score),
            'Goodreads_URL': f'https://www.goodreads.com/search?q={isbn}'
        })

    if redis_client:
        redis_client.setex(cache_key, 600, json.dumps(result))
    return result




def get_popular_books(limit: int = 20, context=None):
    """Returns top-N popular books by rating count, with Redis caching."""
    cache_key = "popular_books_top100"
    print(f"[POPULAR DEBUG] get_popular_books called with limit: {limit}. Cache key: {cache_key}")
    
    # Ensure redis_client is available
    if not redis_client:
        print("[POPULAR DEBUG] Redis client is not available/configured!")
        # Decide handling: proceed without cache or return error
        # For now, let's assume it should error or be handled if critical
        # This might indicate an issue with redis_client initialization
        # return [] # Or handle as an error

    cached_data = None
    if redis_client: # ADDED check before using redis_client
        try:
            cached_data = redis_client.get(cache_key)
        except Exception as e:
            print(f"[POPULAR DEBUG] ERROR accessing Redis for get operation: {e}")
            cached_data = None # Ensure it's None on error

    top_isbns = [] # Initialize top_isbns

    if cached_data:
        try:
            top_isbns = json.loads(cached_data)
            print(f"[POPULAR DEBUG] Found and loaded cached popular_books_top100. Count: {len(top_isbns)}. First 5: {top_isbns[:5]}")
        except json.JSONDecodeError as e:
            print(f"[POPULAR DEBUG] ERROR decoding JSON from Redis cache: {e}. Cache content: {cached_data}")
            top_isbns = [] # Reset on error
    else:
        print(f"[POPULAR DEBUG] No cache for popular_books_top100 or Redis error. Calculating...")
        ratings_path = os.path.join(DATA_DIR, 'Ratings.csv')
        print(f"[POPULAR DEBUG] Reading ratings from: {ratings_path}")
        if not os.path.exists(ratings_path): # ADDED file existence check
            print(f"[POPULAR DEBUG] ERROR: Ratings.csv does not exist at {ratings_path}")
            return []

        try:
            df_ratings = pd.read_csv(ratings_path, delimiter=';')
            print(f"[POPULAR DEBUG] df_ratings loaded. Shape: {df_ratings.shape}. Head:\n{df_ratings.head()}")
            
            df_positive_ratings = df_ratings[df_ratings['Rating'] > 0]
            print(f"[POPULAR DEBUG] df_positive_ratings shape: {df_positive_ratings.shape}. Head:\n{df_positive_ratings.head()}")

            if df_positive_ratings.empty:
                print("[POPULAR DEBUG] No positive ratings found in Ratings.csv!")
                top_isbns = []
            else:
                value_counts_series = df_positive_ratings['ISBN'].value_counts()
                print(f"[POPULAR DEBUG] ISBN value counts (top 5): {value_counts_series.head().to_dict()}")
                top_isbns = value_counts_series.head(100).index.tolist()
            
            print(f"[POPULAR DEBUG] Calculated top_isbns from Ratings.csv (count: {len(top_isbns)}, first 5): {top_isbns[:5]}")
            if redis_client: # ADDED check
                try:
                    redis_client.setex(cache_key, 600, json.dumps(top_isbns))
                    print(f"[POPULAR DEBUG] Set '{cache_key}' in Redis with {len(top_isbns)} ISBNs.")
                except Exception as e:
                    print(f"[POPULAR DEBUG] ERROR setting cache in Redis: {e}")
        except Exception as e:
            print(f"[POPULAR DEBUG] ERROR calculating popular books from Ratings.csv: {e}")
            top_isbns = [] 

    if not top_isbns:
        print("[POPULAR DEBUG] top_isbns list is empty after cache check and Ratings.csv processing. Returning empty list.")
        return []

    books_path = os.path.join(DATA_DIR, 'Books.csv')
    print(f"[POPULAR DEBUG] Reading books from: {books_path}")
    if not os.path.exists(books_path): # ADDED file existence check
        print(f"[POPULAR DEBUG] ERROR: Books.csv does not exist at {books_path}")
        return []

    results = []
    try:
        df_books = pd.read_csv(books_path, delimiter=';', encoding='latin-1', on_bad_lines='skip')
        print(f"[POPULAR DEBUG] df_books loaded. Shape: {df_books.shape}. Head:\n{df_books.head()}")
        
        df_books_unique = df_books.drop_duplicates(subset='ISBN', keep='first')
        print(f"[POPULAR DEBUG] df_books_unique shape after dropping duplicates on ISBN: {df_books_unique.shape}")

        # Create a direct mapping from ISBN to its details for faster lookup
        books_details_map = {}
        for _, row in df_books_unique.iterrows(): # Create a more robust map
            books_details_map[row['ISBN']] = {
                'Title': row.get('Title', 'Unknown Title'),
                'Author': row.get('Author', 'Unknown Author')
            }
        print(f"[POPULAR DEBUG] Created books_details_map with {len(books_details_map)} entries.")

        pick_isbns = []
        if top_isbns: # Ensure top_isbns is not empty
            # Shuffle a copy if you intend to keep original top_isbns order for caching
            shuffled_top_isbns = random.sample(top_isbns, len(top_isbns))
            pick_isbns = shuffled_top_isbns[:limit]
        print(f"[POPULAR DEBUG] Picked {len(pick_isbns)} ISBNs for results (limit was {limit}). First 5: {pick_isbns[:5]}")

        for isbn in pick_isbns:
            info = books_details_map.get(isbn) # Use the new map
            if info:
                results.append({
                    'Book_ID': isbn,
                    'Book_Title': info.get('Title', 'Unknown Title'),
                    'Author': info.get('Author', 'Unknown Author'), 
                    'Goodreads_URL': f'https://www.goodreads.com/search?q={isbn}', 
                })
            else:
                print(f"[POPULAR DEBUG] ISBN {isbn} from pick_isbns not found in books_details_map.")
    
    except FileNotFoundErrorError as e: # Specific error for file not found
        print(f"[POPULAR DEBUG] ERROR (FileNotFoundError) reading or processing Books.csv: {e}")
        return []
    except pd.errors.EmptyDataError as e: # Specific error for empty CSV
        print(f"[POPULAR DEBUG] ERROR (EmptyDataError) reading Books.csv - file is empty or all lines are bad: {e}")
        return []
    except Exception as e:
        print(f"[POPULAR DEBUG] ERROR reading or processing Books.csv: {e}")
        return [] 
    
    print(f"[POPULAR DEBUG] Returning {len(results)} popular books. First 3: {results[:3]}")
    return results


def cache_key_for_recommendation(liked_books, top_n, k=None, threshold=None):
    books_sorted = sorted(liked_books)
    raw = f"{books_sorted}-{top_n}-{k}-{threshold}"
    return "rec:" + hashlib.sha256(raw.encode()).hexdigest()
