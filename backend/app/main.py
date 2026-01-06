import sys
import os
from pathlib import Path

# Add parent directory to path so we can import 'app' module
# This allows the script to be run directly: python app/main.py
parent_dir = Path(__file__).parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from flask import Flask
from flask_cors import CORS
from app.api import api_blueprint

def create_app():
    """Application factory pattern for better Gunicorn compatibility."""
    app = Flask(__name__)
    CORS(app)

    # Initialize MODEL_CONTEXT for routes that expect it
    # Since we're using Supabase, most operations don't need this,
    # but some legacy routes may still reference it
    app.config['MODEL_CONTEXT'] = {
        'user_map': {},         # Empty for now - routes using Supabase don't need this
        'item_map': {},         # Empty for now - routes using Supabase don't need this
        'model': None,          # Not needed with Supabase vector search
        'books_metadata': {}    # Not needed - books come from Supabase
    }

    # Register blueprint
    app.register_blueprint(api_blueprint, url_prefix='/api')
    
    return app

# Create the app instance
app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)