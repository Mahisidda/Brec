import pandas as pd
from scipy.sparse import csr_matrix
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')

def load_sparse_matrix(ratings_path=None, books_path=None,
                       min_user_ratings=5, min_book_ratings=10):
    """
    Reads Ratings.csv and Books.csv, filters infrequent users/books,
    and builds a CSR sparse matrix of shape (num_users, num_books).
    Returns: matrix, user_map, rev_user_map, rev_book_map, isbn_to_title
    """
    ratings_path = ratings_path or os.path.join(DATA_DIR, 'Ratings.csv')
    books_path = books_path or os.path.join(DATA_DIR, 'Books.csv')

    # Load and filter ratings
    ratings = pd.read_csv(ratings_path, delimiter=';')
    ratings = ratings[ratings['Rating'] > 0]  # drop zeros

    user_counts = ratings['User-ID'].value_counts()
    book_counts = ratings['ISBN'].value_counts()
    ratings = ratings[ratings['User-ID'].isin(user_counts[user_counts >= min_user_ratings].index)]
    ratings = ratings[ratings['ISBN'].isin(book_counts[book_counts >= min_book_ratings].index)]

    # Build mappings
    user_ids = ratings['User-ID'].unique()
    isbn_list = ratings['ISBN'].unique()
    user_map = {uid: idx for idx, uid in enumerate(user_ids)}
    book_map = {isbn: idx for idx, isbn in enumerate(isbn_list)}
    rev_user_map = {idx: uid for uid, idx in user_map.items()}
    rev_book_map = {idx: isbn for isbn, idx in book_map.items()}

    # Build sparse matrix
    ratings['user_idx'] = ratings['User-ID'].map(user_map)
    ratings['book_idx'] = ratings['ISBN'].map(book_map)
    matrix = csr_matrix(
        (ratings['Rating'], (ratings['user_idx'], ratings['book_idx'])),
        shape=(len(user_map), len(book_map))
    )

    # Load book titles
    books = pd.read_csv(books_path, delimiter=';')
    isbn_to_title = dict(zip(books['ISBN'], books['Title']))

    return matrix, user_map, rev_user_map, rev_book_map, isbn_to_title
