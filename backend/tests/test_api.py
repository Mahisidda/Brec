# backend/tests/test_api.py

import json
import pytest
from app.main import app  # your Flask app entrypoint

@pytest.fixture
def client():
    # Tell Flask we’re testing
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_home(client):
    """GET / should return a welcome JSON with 'endpoints' key."""
    res = client.get('/')
    assert res.status_code == 200
    data = res.get_json()
    assert isinstance(data, dict)
    assert 'endpoints' in data
    assert isinstance(data['endpoints'], list)

def test_popular_books_default(client):
    """GET /popular_books without limit should still return a list."""
    res = client.get('/popular_books')
    assert res.status_code == 200
    books = res.get_json()
    assert isinstance(books, list)
    assert len(books) > 0
    # Each item should have Book_ID and Book_Title
    assert 'Book_ID' in books[0] and 'Book_Title' in books[0]

def test_popular_books_with_limit(client):
    """GET /popular_books?limit=3 returns exactly 3 items."""
    res = client.get('/popular_books?limit=3')
    assert res.status_code == 200
    books = res.get_json()
    assert isinstance(books, list) and len(books) == 3

def test_recommend_by_books_missing_payload(client):
    """POST /recommend_by_books with empty JSON yields a valid (but empty) list."""
    res = client.post('/recommend_by_books', data=json.dumps({}), 
                      content_type='application/json')
    assert res.status_code == 200
    data = res.get_json()
    assert isinstance(data, list)

def test_recommend_by_books_valid(client):
    """POST /recommend_by_books with two known ISBNs returns recommendations."""
    # Fetch two popular books first
    pop = client.get('/popular_books?limit=2').get_json()
    isbns = [book['Book_ID'] for book in pop]
    payload = {'liked_books': isbns}
    res = client.post('/recommend_by_books', data=json.dumps(payload),
                      content_type='application/json')
    assert res.status_code == 200
    recs = res.get_json()
    # Should return a list (possibly empty if dataset is tiny)
    assert isinstance(recs, list)

def test_random_user_and_rated_books(client):
    """GET /random_user then /rated_books?user_id=X returns a list or 404."""
    rnd = client.get('/random_user').get_json()
    user_id = rnd.get('user_id')
    assert isinstance(user_id, int)

    res = client.get(f'/rated_books?user_id={user_id}')
    # Either we get a list of dicts or a 404 if edge-case
    if res.status_code == 200:
        rated = res.get_json()
        assert isinstance(rated, list)
        if rated:  # if non-empty, items have Book_ID, Book_Title, Rating
            item = rated[0]
            assert 'Book_ID' in item and 'Rating' in item
    else:
        assert res.status_code == 404
