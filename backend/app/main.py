from flask import Flask
from flask_cors import CORS
from app.api import api_blueprint
from app.engine import load_all_data
from app.matrix import build_faiss_index  # ✅ import this
import os

app = Flask(__name__)

# configure origins via env for dev vs. prod
allowed = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000,http://192.168.0.202:3000").split(",")

# Use the environment variable instead of hardcoded localhost
CORS(
    app,
    origins=allowed,  # <-- Changed from hardcoded list to use environment variable
    supports_credentials=True,
    methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"]
)

# Load data once at startup
matrix, user_map, book_map, rev_user_map, rev_book_map, isbn_to_details = load_all_data()
faiss_index = build_faiss_index(matrix)  # ✅ FAISS step

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

# Register API routes
app.register_blueprint(api_blueprint, url_prefix='/api')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
