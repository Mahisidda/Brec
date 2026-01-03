from flask import Blueprint, request, jsonify, current_app
from app.engine import get_popular_books
import os

from app.engine import (
    get_random_user_id,
    get_user_rated_books,
    recommend_for_user,
    recommend_by_books,
    get_popular_books,
)


api_blueprint = Blueprint('api', __name__)

@api_blueprint.route('/random_user', methods=['GET'])
def random_user():
    user_map = current_app.config['MODEL_CONTEXT']['user_map']
    return jsonify({"user_id": get_random_user_id(user_map)})

@api_blueprint.route('/rated_books', methods=['GET'])
def rated_books():
    user_id = request.args.get('user_id', type=int)
    ctx = current_app.config['MODEL_CONTEXT']
    books = get_user_rated_books(user_id, ctx)
    if books is None:
        return jsonify({"error": "User not found"}), 404
    return jsonify(books)

@api_blueprint.route('/recommend', methods=['GET'])
def recommend_user():
    user_id = request.args.get('user_id', type=int)
    ctx = current_app.config['MODEL_CONTEXT']
    recs = recommend_for_user(user_id, ctx)
    if recs is None:
        return jsonify({"error": "User not found"}), 404
    return jsonify(recs)

@api_blueprint.route('/recommend_by_books', methods=['POST'])
def recommend_books_route():
    try:
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400
        
        if request.json is None:
            return jsonify({"error": "Request body is empty"}), 400
        
        liked = request.json.get('liked_books', [])
        if not isinstance(liked, list):
            return jsonify({"error": "liked_books must be a list"}), 400
        
        ctx = current_app.config.get('MODEL_CONTEXT')
        if ctx is None:
            return jsonify({"error": "Server configuration error", "message": "Model context not available"}), 500
        
        recs = recommend_by_books(liked, ctx)
        print(recs)
        return jsonify(recs)
    except Exception as e:
        print(f"[API ERROR] Error in recommend_books_route: {e}")
        import traceback
        print(traceback.format_exc())
        return jsonify({"error": "Internal server error", "message": str(e)}), 500

@api_blueprint.route('/', methods=['GET'])
def home():
    return jsonify({
        "message": "Welcome to the Book Recommender API",
        "endpoints": [
            "/random_user",
            "/rated_books?user_id=<id>",
            "/recommend?user_id=<id>",
            "/recommend_by_books (POST)",
            "/popular_books?limit=<n>"
        ]
    })



@api_blueprint.route('/popular_books', methods=['GET'])
def popular_books():
    print("[API DEBUG] /popular_books route hit!")
    limit = int(request.args.get('limit', 20))
    print(f"[API DEBUG] Requested limit: {limit}")
    
    ctx = current_app.config.get('MODEL_CONTEXT')
    if ctx is None:
        print("[API DEBUG] ERROR: MODEL_CONTEXT not found in app.config!")
        return jsonify({"error": "Server configuration error", "message": "Model context not available"}), 500
    
    print(f"[API DEBUG] Calling get_popular_books with limit: {limit}")
    books = get_popular_books(limit=limit, context=ctx)
    print(f"[API DEBUG] get_popular_books returned: {len(books)} books.")
    return jsonify(books)

@api_blueprint.route("/debug_env")
def env():
    return {
        "files": os.listdir("/app/data"),
        "exists_books": os.path.exists("/app/data/Books.csv")
    }
