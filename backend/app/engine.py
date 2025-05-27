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
    ratings_csv = os.path.join(DATA_DIR, 'Ratings.csv')
    books_csv = os.path.join(DATA_DIR, 'Books.csv')
    return load_sparse_matrix(ratings_csv, books_csv)


def get_random_user_id(user_map):
    """Pick a random real user ID from the dataset."""
    return int(random.choice(list(user_map.keys())))


def get_user_rated_books(user_id, context):
    """Returns all books rated by a specific user."""
    user_map = context['user_map']
    rev_book_map = context['rev_book_map']
    isbn_to_title = context['isbn_to_title']
    matrix = context['matrix']

    if user_id not in user_map:
        return None

    u_idx = user_map[user_id]
    row = matrix[u_idx]
    cols = row.nonzero()[1]
    vals = row.data

    return [{
        'Book_ID': rev_book_map[col],
        'Book_Title': isbn_to_title.get(rev_book_map[col], "Unknown Title"),
        'Rating': float(val)
    } for col, val in zip(cols, vals)]


def recommend_for_user(user_id, context, k=10, top_n=3, similarity_threshold=0.1):
    """Collaborative Filtering: recommend top-N books for an existing user."""
    user_map = context['user_map']
    rev_book_map = context['rev_book_map']
    isbn_to_title = context['isbn_to_title']
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
    return [{
        'Book_ID': rev_book_map[b],
        'Book_Title': isbn_to_title.get(rev_book_map[b], "Unknown Title"),
        'Recommendation_Score': float(score)
    } for b, score in top]


#def recommend_by_books(liked_books, context, k=10, top_n=5, similarity_threshold=0.1):
    """Pseudo-user collaborative filtering using liked books."""
    cache_key = cache_key_for_recommendation(liked_books, top_n, k, similarity_threshold)
    cached = redis_client.get(cache_key)
    if cached:
        return json.loads(cached.decode("utf-8"))

    matrix = context['matrix']
    book_map = context['book_map']
    rev_book_map = context['rev_book_map']
    isbn_to_title = context['isbn_to_title']

    n_books = matrix.shape[1]
    liked_idxs = [book_map[isbn] for isbn in liked_books if isbn in book_map]
    if not liked_idxs:
        return []

    pseudo = np.zeros((1, n_books))
    for idx in liked_idxs:
        pseudo[0, idx] = 10.0

    sim_vec = cosine_similarity(pseudo, matrix).flatten()
    eligible = np.where(sim_vec > similarity_threshold)[0]
    if len(eligible) > k:
        neighbors = eligible[np.argpartition(sim_vec[eligible], -k)[-k:]]
        neighbors = neighbors[np.argsort(sim_vec[neighbors])[::-1]]
    else:
        neighbors = eligible

    if len(neighbors) == 0:
        return []

    nonzeros_cache = {n: matrix[n].nonzero()[1] for n in neighbors}
    candidate_books = set().union(*nonzeros_cache.values()) - set(liked_idxs)

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
    result = [{
        'Book_ID': rev_book_map[b],
        'Book_Title': isbn_to_title.get(rev_book_map[b], "Unknown Title"),
        'Recommendation_Score': float(score)
    } for b, score in top]

    redis_client.setex(cache_key, 600, json.dumps(result))
    return result

def recommend_by_books(liked_books, context, k=10, top_n=5, similarity_threshold=0.1):
    """FAISS-accelerated pseudo-user collaborative filtering."""
    cache_key = cache_key_for_recommendation(liked_books, top_n, k, similarity_threshold)
    cached = redis_client.get(cache_key)
    if cached:
        return json.loads(cached.decode("utf-8"))

    matrix = context['matrix']
    book_map = context['book_map']
    rev_book_map = context['rev_book_map']
    isbn_to_title = context['isbn_to_title']
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
    result = [{
        'Book_ID': rev_book_map[b],
        'Book_Title': isbn_to_title.get(rev_book_map[b], "Unknown Title"),
        'Recommendation_Score': float(score)
    } for b, score in top]

    redis_client.setex(cache_key, 600, json.dumps(result))
    return result




def get_popular_books(limit: int = 20, context=None):
    """Returns top-N popular books by rating count, with Redis caching."""
    cache_key = "popular_books_top100"
    cached = redis_client.get(cache_key)
    if cached:
        top_isbns = json.loads(cached)
    else:
        ratings_path = os.path.join(DATA_DIR, 'Ratings.csv')
        df_ratings = pd.read_csv(ratings_path, delimiter=';')
        top_isbns = df_ratings[df_ratings['Rating'] > 0]['ISBN'].value_counts().head(100).index.tolist()
        redis_client.setex(cache_key, 600, json.dumps(top_isbns))

    random.shuffle(top_isbns)
    pick_isbns = top_isbns[:limit]

    books_path = os.path.join(DATA_DIR, 'Books.csv')
    df_books = pd.read_csv(books_path, delimiter=';')
    df_books_unique = df_books.drop_duplicates(subset='ISBN', keep='first')
    books_map = df_books_unique.set_index('ISBN')[['Title', 'Author']].to_dict(orient='index')

    results = []
    for isbn in pick_isbns:
        info = books_map.get(isbn, {})
        results.append({
            'Book_ID': isbn,
            'Book_Title': info.get('Title', 'Unknown Title'),
            'Author': info.get('Author', 'Unknown Author'),
            'Goodreads_URL': f'https://www.goodreads.com/search?q={isbn}',
        })
    return results


def cache_key_for_recommendation(liked_books, top_n, k=None, threshold=None):
    books_sorted = sorted(liked_books)
    raw = f"{books_sorted}-{top_n}-{k}-{threshold}"
    return "rec:" + hashlib.sha256(raw.encode()).hexdigest()
