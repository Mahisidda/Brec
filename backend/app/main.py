from flask import Flask
from flask_cors import CORS
from app.api import api_blueprint
from app.engine import load_all_data

app = Flask(__name__)
CORS(app)

# Load data once at startup
matrix, user_map, rev_user_map, rev_book_map, isbn_to_title = load_all_data()
app.config['MODEL_CONTEXT'] = {
    'matrix': matrix,
    'user_map': user_map,
    'book_map': {v: k for k, v in rev_book_map.items()},
    'rev_user_map': rev_user_map,
    'rev_book_map': rev_book_map,
    'isbn_to_title': isbn_to_title
}

# Register our API routes
app.register_blueprint(api_blueprint, url_prefix='/')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
