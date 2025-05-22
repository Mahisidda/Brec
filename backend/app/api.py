from flask import Blueprint, request, jsonify, current_app
from app.engine import get_popular_books

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
    liked = request.json.get('liked_books', [])
    ctx = current_app.config['MODEL_CONTEXT']
    recs = recommend_by_books(liked, ctx)
    return jsonify(recs)

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
def popular_books_route():
    """
    GET /popular_books?limit=20
    Returns the top-N most-rated books for user selection.
    """
    limit = request.args.get('limit', default=10, type=int)
    ctx   = current_app.config['MODEL_CONTEXT']
    popular = get_popular_books(limit, ctx)
    return jsonify(popular)
