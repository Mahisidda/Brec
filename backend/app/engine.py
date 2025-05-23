import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from .matrix import load_sparse_matrix
import random
import os
import pandas as pd            # <— you need this for pd.read_csv


DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')

def load_all_data():
    """
    Loads matrix, mappings, and title lookup once.
    """
    ratings_csv = os.path.join(DATA_DIR, 'Ratings.csv')
    books_csv   = os.path.join(DATA_DIR, 'Books.csv')
    return load_sparse_matrix(ratings_csv, books_csv)

def get_random_user_id(user_map):
    """Pick a random real user ID from the dataset."""
    return int(random.choice(list(user_map.keys())))

def get_user_rated_books(user_id, context):
    """
    For a given real user_id, return a list of books they've rated:
    [ {Book_ID, Book_Title, Rating}, ... ]
    """
    user_map      = context['user_map']
    rev_book_map  = context['rev_book_map']
    isbn_to_title = context['isbn_to_title']
    matrix        = context['matrix']

    if user_id not in user_map:
        return None

    u_idx = user_map[user_id]
    row = matrix[u_idx]
    cols = row.nonzero()[1]
    vals = row.data

    results = []
    for col, val in zip(cols, vals):
        isbn = rev_book_map[col]
        title = isbn_to_title.get(isbn, "Unknown Title")
        results.append({
            'Book_ID': isbn,
            'Book_Title': title,
            'Rating': float(val)
        })
    return results

def recommend_for_user(user_id, context, k=10, top_n=3):
    """
    The existing user-ID-based CF:
    Returns top_n recommendations for a real user.
    """
    user_map      = context['user_map']
    rev_book_map  = context['rev_book_map']
    isbn_to_title = context['isbn_to_title']
    matrix        = context['matrix']

    if user_id not in user_map:
        return None

    u_idx = user_map[user_id]
    # Compute similarity of this user to all users
    sim_vec = cosine_similarity(matrix[u_idx], matrix).flatten()
    # Sort all users by descending similarity, then exclude the user itself
    sorted_indices = np.argsort(sim_vec)[::-1]
    neighbors = sorted_indices
    # Books this user has already rated
    seen = set(matrix[u_idx].nonzero()[1])

    # Predict ratings with a fallback to simple average if similarity sum is zero
    preds = {}
    # collect all candidate books
    candidate_books = set().union(*(matrix[n].nonzero()[1] for n in neighbors)) - seen

    for b in candidate_books:
        weighted_num = 0.0
        weighted_den = 0.0
        neighbor_ratings = []

        for n in neighbors:
            r = matrix[n, b]
            if r > 0:
                neighbor_ratings.append(r)
                weighted_num += sim_vec[n] * r
                weighted_den += sim_vec[n]

        if weighted_den > 0:
            # weighted average
            preds[b] = weighted_num / weighted_den
        elif neighbor_ratings:
            # fallback: simple (unweighted) average
            preds[b] = sum(neighbor_ratings) / len(neighbor_ratings)
        # else: nobody rated it, skip

    # Top-n by predicted score
    top = sorted(preds.items(), key=lambda x: x[1], reverse=True)[:top_n]

    return [{
        'Book_ID': rev_book_map[b],
        'Book_Title': isbn_to_title.get(rev_book_map[b], "Unknown Title"),
        'Recommendation_Score': float(score)
    } for b, score in top]



# def recommend_by_books(liked_books, context, k=10, top_n=5):
    """
    Pseudo-user approach:
    Build a 1×num_books vector from liked_books,
    compute similarity on the fly,
    then recommend as above.
    """
    matrix        = context['matrix']
    book_map      = context['book_map']
    rev_book_map  = context['rev_book_map']
    isbn_to_title = context['isbn_to_title']

    n_books = matrix.shape[1]
    # Map liked ISBNs to indices, ignore missing
    liked_idxs = [book_map[isbn] for isbn in liked_books if isbn in book_map]
    # Build pseudo-user vector
    pseudo = np.zeros((1, n_books))
    for idx in liked_idxs:
        pseudo[0, idx] = 10.0

    # Compute similarity
    sim_vec = cosine_similarity(pseudo, matrix).flatten()
    neighbors = np.argsort(sim_vec)[-k:][::-1]

    seen = set().union(*(matrix[n].nonzero()[1] for n in neighbors)) - set(liked_idxs)

    preds = {}
    for b in seen:
        num = den = 0
        for n in neighbors:
            r = matrix[n, b]
            if r > 0:
                num += sim_vec[n] * r
                den += sim_vec[n]
        if den > 0:
            preds[b] = num / den

    top = sorted(preds.items(), key=lambda x: x[1], reverse=True)[:top_n]
    return [{
        'Book_ID': rev_book_map[b],
        'Book_Title': isbn_to_title.get(rev_book_map[b], "Unknown Title"),
        'Recommendation_Score': float(score)
    } for b, score in top]

def recommend_by_books(liked_books, context, k=10, top_n=5):
    """
    Pseudo-user CF:
    Build a 1×num_books vector from liked_books,
    compute similarity on the fly,
    then recommend as above (with fallback).
    """
    matrix        = context['matrix']
    book_map      = context['book_map']
    rev_book_map  = context['rev_book_map']
    isbn_to_title = context['isbn_to_title']

    # 1) Build the pseudo‐user vector
    n_books = matrix.shape[1]
    liked_idxs = [book_map[isbn] for isbn in liked_books if isbn in book_map]
    pseudo = np.zeros((1, n_books))
    for idx in liked_idxs:
        pseudo[0, idx] = 10.0

    # 2) Compute similarities
    sim_vec = cosine_similarity(pseudo, matrix).flatten()

    # 3) Use *all* users sorted by similarity (descending)
    sorted_idxs = np.argsort(sim_vec)[::-1]
    neighbors = sorted_idxs  # do NOT slice by k here

    # 4) Determine which books to predict
    seen = set()
    for n in neighbors:
        seen |= set(matrix[n].nonzero()[1])
    seen -= set(liked_idxs)
    candidate_books = seen

    # 5) Predict with weighted avg, fallback to simple avg
    preds = {}
    for b in candidate_books:
        weighted_num = 0.0
        weighted_den = 0.0
        neighbor_ratings = []
        for n in neighbors:
            r = matrix[n, b]
            if r > 0:
                neighbor_ratings.append(r)
                weighted_num += sim_vec[n] * r
                weighted_den += sim_vec[n]

        if weighted_den > 0:
            preds[b] = weighted_num / weighted_den
        elif neighbor_ratings:
            preds[b] = sum(neighbor_ratings) / len(neighbor_ratings)
        # else: nobody rated b, skip it

    # 6) Take the top_n books
    top = sorted(preds.items(), key=lambda x: x[1], reverse=True)[:top_n]
    return [{
        'Book_ID': rev_book_map[b],
        'Book_Title': isbn_to_title.get(rev_book_map[b], "Unknown Title"),
        'Recommendation_Score': float(score)
    } for b, score in top]


import pandas as pd
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')

def get_popular_books(limit: int = 20, context=None):
    """
    Returns the top-N most frequently rated books (by count of ratings > 0).
    """
    ratings_path = os.path.join(DATA_DIR, 'Ratings.csv')
    # Read and filter
    df = pd.read_csv(ratings_path, delimiter=';')
    df = df[df['Rating'] > 0]
    # Count ratings per ISBN
    top_isbns = df['ISBN'].value_counts().head(limit).index.tolist()

    # Map to titles
    isbn_to_title = context['isbn_to_title'] if context else {}
    results = []
    for isbn in top_isbns:
        title = isbn_to_title.get(isbn, "Unknown Title")
        results.append({
            'Book_ID': isbn,
            'Book_Title': title
        })
    return results
