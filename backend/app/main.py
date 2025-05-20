# app/main.py

from flask import Flask
from flask_cors import CORS
from app.api import api_blueprint
from app.engine import load_all_data

app = Flask(__name__)
CORS(app)

# Load data and similarity matrix once on startup
matrix, user_map, rev_user_map, rev_book_map, isbn_to_title = load_all_data()

# Register API routes
app.register_blueprint(api_blueprint, url_prefix='/')

# Inject shared objects into app context
def get_model_context():
    return {
        'matrix': matrix,
        'user_map': user_map,
        'rev_user_map': rev_user_map,
        'rev_book_map': rev_book_map,
        'isbn_to_title': isbn_to_title
    }

app.config['MODEL_CONTEXT'] = get_model_context()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
