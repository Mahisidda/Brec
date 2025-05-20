# app/engine.py

import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.datasets import load_svmlight_file
from scipy.sparse import csr_matrix
import random
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')

def load_all_data():
    ratings_path = os.path.join(DATA_DIR, 'Ratings.csv')
    books_path = os.path.join(DATA_DIR, 'Books.csv')
    matrix_path = os.path.join(DATA_DIR, 'user_book_matrix.libsvm')

    # Load ratings
    ratings = pd.read_csv(ratings_path, delimiter=';')
    books = pd.read_csv(books_path, delimiter=';')
    matrix, _ = load_svmlight_file(matrix_path)
    
    # Filter ratings used in matrix creation
    ratings = ratings[ratings['Book-Rating'] > 0]
    user_id_map = {uid: idx for idx, uid in enumerate(ratings['User-ID'].unique())}
    book_id_map = {isbn: idx for idx, isbn in enumerate(ratings['ISBN'].unique())}
    rev_user_id_map = {v: k for k, v in user_id_map.items()}
    rev_book_id_map = {v: k for k, v in book_id_map.items()}
    isbn_to_title = dict(zip(books['ISBN'], books['Book-Title']))

    return matrix, user_id_map, rev_user_id_map, rev_book_id_map, isbn_to_title

def get_random_user_id(user_map):
    return int(random.choice(list(user_map.keys())))

def get_user_rated_books(user_id, context):
    if user_id not in context['user_map']:
        return None
    user_idx = context['user_map'][user_id]
    user_row = context['matrix'][user_idx]
    book_indices = user_row.nonzero()[1]
    ratings = user_row.data

    results = []
    for idx, rating in zip(book_indices, ratings):
        isbn = context['rev_book_map'].get(idx, 'Unknown')
        title = context['isbn_to_title'].get(isbn, 'Unknown Title')
        results.append({
            'Book_ID': isbn,
            'Book_Title': title,
            'Rating': float(rating)
        })
    return results

def recommend_for_user(user_id, context, k=10, top_n=3):
    if user_id not in context['user_map']:
        return None
    matrix = context['matrix']
    user_idx = context['user_map'][user_id]
    sim_matrix = cosine_similarity(matrix[user_idx], matrix).flatten()

    similar_users = np.argsort(sim_matrix)[-k-1:-1][::-1]
    already_rated = set(matrix[user_idx].nonzero()[1])
    candidate_books = set()

    for sim_user in similar_users:
        candidate_books.update(matrix[sim_user].nonzero()[1])
    candidate_books -= already_rated

    predicted_scores = {}
    for book_idx in candidate_books:
        numer = 0
        denom = 0
        for sim_user in similar_users:
            rating = matrix[sim_user, book_idx]
            if rating > 0:
                numer += sim_matrix[sim_user] * rating
                denom += sim_matrix[sim_user]
        if denom > 0:
            predicted_scores[book_idx] = numer / denom

    top_books = sorted(predicted_scores.items(), key=lambda x: x[1], reverse=True)[:top_n]
    
    return [{
        'Book_ID': context['rev_book_map'].get(book_idx, 'Unknown'),
        'Book_Title': context['isbn_to_title'].get(context['rev_book_map'].get(book_idx, ''), 'Unknown Title'),
        'Recommendation_Score': float(score)
    } for book_idx, score in top_books]
