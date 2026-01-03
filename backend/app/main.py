from flask import Flask
from flask_cors import CORS
from app.api import api_blueprint
from app.engine import load_all_data
from app.matrix import build_faiss_index  # ✅ import this
import os

app = Flask(__name__)

# configure origins via env for dev vs. prod
allowed = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000,http://192.168.0.202:3001,https://brec.mahisidda.com").split(",")

# Use the environment variable instead of hardcoded localhost
CORS(
    app,
    origins=allowed,  # <-- Changed from hardcoded list to use environment variable
    supports_credentials=True,
    methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"]
)

# Load data once at startup
print("[MAIN] Starting data loading...")
matrix, user_map, book_map, rev_user_map, rev_book_map, isbn_to_details = load_all_data()

if matrix is None or user_map is None:
    print("[MAIN] ERROR: Failed to load data files. Check that Books.csv and Ratings.csv exist in /app/data/")
    print("[MAIN] Current working directory:", os.getcwd())
    print("[MAIN] Listing /app directory:", os.listdir("/app") if os.path.exists("/app") else "N/A")
    print("[MAIN] Listing /app/data directory:", os.listdir("/app/data") if os.path.exists("/app/data") else "N/A")
    raise RuntimeError("Failed to load required data files. Application cannot start without Books.csv and Ratings.csv")

faiss_index = build_faiss_index(matrix)  # ✅ FAISS step

if faiss_index is None:
    print("[MAIN] WARNING: Failed to build FAISS index, but continuing without it")

# Store everything in context
app.config['MODEL_CONTEXT'] = {
    'matrix': matrix,
    'user_map': user_map,
    'book_map': book_map,
    'rev_user_map': rev_user_map,
    'rev_book_map': rev_book_map,
    'isbn_to_details': isbn_to_details,
    'faiss_index': faiss_index  # ✅ FAISS index now available in context
}
print("[MAIN] Data loaded successfully. Application ready.")

# Register API routes
app.register_blueprint(api_blueprint, url_prefix='/api')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
