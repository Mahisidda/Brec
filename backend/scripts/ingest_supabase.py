import pandas as pd
import numpy as np
from scipy.sparse import csr_matrix
from sklearn.decomposition import TruncatedSVD
from supabase import create_client

# Configuration
SUPABASE_URL = "https://xkijojlpubgoutufbqhg.supabase.co"
SUPABASE_KEY = "sb_secret_9OFemXdlwoiq_AKR2Od3kw_VQBxvziq" 
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def ingest():
    print("🚀 Loading CSVs...")
    settings = {'delimiter': ';', 'encoding': 'latin-1', 'on_bad_lines': 'skip', 'low_memory': False}
    
    # Load Ratings
    ratings = pd.read_csv('../data/Ratings.csv', **settings)
    ratings = ratings[ratings['Rating'] > 0] # Only keep actual ratings

    # --- NEW SPARSE LOGIC TO PREVENT CRASH ---
    print("🧠 Creating Sparse Matrix (Memory Efficient)...")
    ratings['User-ID'] = ratings['User-ID'].astype('category')
    ratings['ISBN'] = ratings['ISBN'].astype('category')

    # Create the matrix without expanding it to billions of zeros
    row = ratings['User-ID'].cat.codes
    col = ratings['ISBN'].cat.codes
    data = ratings['Rating']
    
    sparse_matrix = csr_matrix((data, (row, col)))
    user_ids = ratings['User-ID'].cat.categories.tolist()

    print(f"✅ Sparse Matrix ready. Shape: {sparse_matrix.shape}")

    # --- DIMENSIONALITY REDUCTION ---
    print("📉 Reducing dimensions with SVD...")
    svd = TruncatedSVD(n_components=50, random_state=42)
    vectors = svd.fit_transform(sparse_matrix)

    # --- UPLOAD TO SUPABASE ---
    print(f"📤 Uploading {len(user_ids)} vectors to Supabase...")
    payload = []
    for idx, uid in enumerate(user_ids):
        payload.append({
            "user_id": int(uid),
            "embedding": vectors[idx].tolist()
        })
        
        # Batch upload every 100 users
        if len(payload) >= 100:
            supabase.table("user_vectors").upsert(payload).execute()
            payload = []
            if idx % 1000 == 0:
                print(f"Progress: {idx}/{len(user_ids)} users uploaded...")

    if payload:
        supabase.table("user_vectors").upsert(payload).execute()

    print("🎉 Ingestion Complete! Check your Supabase dashboard now.")

if __name__ == "__main__":
    ingest()