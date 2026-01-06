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

app = Flask(__name__)
CORS(app)

# NO load_all_data() here! 
# The app starts instantly.

app.register_blueprint(api_blueprint, url_prefix='/api')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)