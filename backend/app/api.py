# app/api.py

from flask import Blueprint, request, jsonify, current_app
from app.engine import recommend_for_user, get_user_rated_books, get_random_user_id

api_blueprint = Blueprint('api', __name__)

@api_blueprint.route('/random_user', methods=['GET'])
def random_user():
    context = current_app.config['MODEL_CONTEXT']
    user_id = get_random_user_id(context['user_map'])
    return jsonify({"user_id": user_id})

@api_blueprint.route('/rated_books', methods=['GET'])
def rated_books():
    user_id = request.args.get('user_id', type=int)
    context = current_app.config['MODEL_CONTEXT']
    result = get_user_rated_books(user_id, context)
    if result is None:
        return jsonify({"error": "User not found"}), 404
    return jsonify(result)

@api_blueprint.route('/recommend', methods=['GET'])
def recommend():
    user_id = request.args.get('user_id', type=int)
    context = current_app.config['MODEL_CONTEXT']
    recommendations = recommend_for_user(user_id, context)
    if recommendations is None:
        return jsonify({"error": "User not found"}), 404
    return jsonify(recommendations)
