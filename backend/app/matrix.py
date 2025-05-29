import pandas as pd
from scipy.sparse import csr_matrix
import numpy as np
import faiss
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')

def load_sparse_matrix(ratings_path=None, books_path=None,
                       min_user_ratings=5, min_book_ratings=10):
    """
    Builds a CSR matrix from Ratings.csv and Books.csv after filtering.
    Returns:
        matrix, user_map, book_map, rev_user_map, rev_book_map, isbn_to_details
    """
    print("[MATRIX DEBUG] load_sparse_matrix called.")
    effective_ratings_path = ratings_path or os.path.join(DATA_DIR, 'Ratings.csv')
    effective_books_path = books_path or os.path.join(DATA_DIR, 'Books.csv')
    print(f"[MATRIX DEBUG] Effective ratings_path: {effective_ratings_path}")
    print(f"[MATRIX DEBUG] Effective books_path: {effective_books_path}")

    # Check if files exist
    if not os.path.exists(effective_ratings_path):
        print(f"[MATRIX DEBUG] ERROR: Ratings CSV not found at {effective_ratings_path}")
        # Consider how to handle this: raise error, return Nones, etc.
        # For now, returning None for all expected values to signal failure
        return None, None, None, None, None, None 
    if not os.path.exists(effective_books_path):
        print(f"[MATRIX DEBUG] ERROR: Books CSV not found at {effective_books_path}")
        return None, None, None, None, None, None

    try:
        # Load and filter ratings
        print(f"[MATRIX DEBUG] Loading ratings from {effective_ratings_path}")
        ratings = pd.read_csv(effective_ratings_path, delimiter=';', encoding='latin-1', engine='python')
        print(f"[MATRIX DEBUG] Initial ratings loaded. Shape: {ratings.shape}")
        ratings = ratings[ratings['Rating'] > 0]
        print(f"[MATRIX DEBUG] Ratings after filtering for Rating > 0. Shape: {ratings.shape}")

        user_counts = ratings['User-ID'].value_counts()
        book_counts = ratings['ISBN'].value_counts()
        print(f"[MATRIX DEBUG] Raw user_counts: {len(user_counts)}, Raw book_counts: {len(book_counts)}")

        ratings = ratings[ratings['User-ID'].isin(user_counts[user_counts >= min_user_ratings].index)]
        print(f"[MATRIX DEBUG] Ratings after min_user_ratings ({min_user_ratings}). Shape: {ratings.shape}")
        ratings = ratings[ratings['ISBN'].isin(book_counts[book_counts >= min_book_ratings].index)]
        print(f"[MATRIX DEBUG] Ratings after min_book_ratings ({min_book_ratings}). Shape: {ratings.shape}")

        if ratings.empty:
            print("[MATRIX DEBUG] Ratings dataframe is empty after filtering. Cannot build matrix.")
            return None, None, None, None, None, None


        # Build mappings
        user_ids = ratings['User-ID'].unique()
        isbn_list = ratings['ISBN'].unique()
        print(f"[MATRIX DEBUG] Unique user IDs after filtering: {len(user_ids)}")
        print(f"[MATRIX DEBUG] Unique ISBNs after filtering: {len(isbn_list)}")

        user_map = {uid: idx for idx, uid in enumerate(user_ids)}
        book_map = {isbn: idx for idx, isbn in enumerate(isbn_list)}
        rev_user_map = {idx: uid for uid, idx in user_map.items()}
        rev_book_map = {idx: isbn for isbn, idx in book_map.items()}

        ratings['user_idx'] = ratings['User-ID'].map(user_map)
        ratings['book_idx'] = ratings['ISBN'].map(book_map)
        
        # Check for NaNs in mapped indices which can cause errors in csr_matrix
        if ratings['user_idx'].isnull().any() or ratings['book_idx'].isnull().any():
            print("[MATRIX DEBUG] ERROR: NaN values found in user_idx or book_idx after mapping. This indicates an issue with filtering or mapping logic.")
            print(f"[MATRIX DEBUG] user_idx NaNs: {ratings['user_idx'].isnull().sum()}")
            print(f"[MATRIX DEBUG] book_idx NaNs: {ratings['book_idx'].isnull().sum()}")
            # Potentially drop rows with NaN indices or handle error
            ratings.dropna(subset=['user_idx', 'book_idx'], inplace=True)
            print(f"[MATRIX DEBUG] Ratings shape after dropping NaN indices: {ratings.shape}")
            # Re-ensure user_map and book_map lengths are correct for matrix shape
            # This might be complex if NaNs caused users/books to be effectively removed
            # For now, we'll proceed, but this is a critical debug point if errors occur

        matrix = csr_matrix(
            (ratings['Rating'], (ratings['user_idx'], ratings['book_idx'])),
            shape=(len(user_map), len(book_map))
        )
        print(f"[MATRIX DEBUG] CSR matrix created. Shape: {matrix.shape}, NNZ: {matrix.nnz}")

        # Load book details (title and author)
        print(f"[MATRIX DEBUG] Loading book details from {effective_books_path}")
        books = pd.read_csv(effective_books_path, delimiter=';', encoding='latin-1', on_bad_lines='skip', engine='python')
        print(f"[MATRIX DEBUG] Books CSV loaded for details. Shape: {books.shape}")
        
        isbn_to_details = {}
        # Ensure 'ISBN', 'Title', 'Author' columns exist or handle gracefully
        required_cols = ['ISBN', 'Title', 'Author']
        missing_cols = [col for col in required_cols if col not in books.columns]
        if missing_cols:
            print(f"[MATRIX DEBUG] WARNING: Missing expected columns in Books.csv for details: {missing_cols}")
            # Adjust row.get() to handle these missing columns if needed, though .get already provides defaults

        for _, row in books.iterrows():
            isbn = row.get('ISBN') # Use .get for safety if ISBN column might be missing
            if isbn: # Only process if ISBN is present
                isbn_to_details[isbn] = {
                    'Title': row.get('Title', 'Unknown Title'), # Original was good
                    'Author': row.get('Author', 'Unknown Author') # Original was good
                }
        print(f"[MATRIX DEBUG] isbn_to_details map created with {len(isbn_to_details)} entries.")

    except FileNotFoundError as e:
        print(f"[MATRIX DEBUG] ERROR (FileNotFoundError) during matrix/details loading: {e}")
        return None, None, None, None, None, None
    except pd.errors.EmptyDataError as e:
        print(f"[MATRIX DEBUG] ERROR (EmptyDataError) - CSV file is empty or unreadable: {e}")
        return None, None, None, None, None, None
    except Exception as e:
        print(f"[MATRIX DEBUG] UNEXPECTED ERROR in load_sparse_matrix: {e}")
        # Optionally re-raise e or return None values
        import traceback
        print(traceback.format_exc())
        return None, None, None, None, None, None


    return matrix, user_map, book_map, rev_user_map, rev_book_map, isbn_to_details


def build_faiss_index(matrix):
    """
    Builds a FAISS index from the user-book rating matrix (row-wise user vectors).
    Uses cosine similarity (via inner product on normalized vectors).
    """
    print(f"[MATRIX DEBUG] build_faiss_index called. Input matrix type: {type(matrix)}")
    if matrix is None:
        print("[MATRIX DEBUG] ERROR: Cannot build FAISS index, input matrix is None.")
        return None
    if matrix.shape[0] == 0 or matrix.shape[1] == 0:
        print(f"[MATRIX DEBUG] ERROR: Cannot build FAISS index from empty matrix. Shape: {matrix.shape}")
        return None

    try:
        dense_matrix = matrix.astype(np.float32).toarray()
        print(f"[MATRIX DEBUG] Converted matrix to dense for FAISS. Shape: {dense_matrix.shape}")
        faiss.normalize_L2(dense_matrix)
        print("[MATRIX DEBUG] Dense matrix normalized for FAISS.")
        index = faiss.IndexFlatIP(dense_matrix.shape[1])  # Inner product index
        index.add(dense_matrix)
        print(f"[MATRIX DEBUG] FAISS index built and data added. Index total entries: {index.ntotal}")
        return index
    except Exception as e:
        print(f"[MATRIX DEBUG] ERROR building FAISS index: {e}")
        import traceback
        print(traceback.format_exc())
        return None
