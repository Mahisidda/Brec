import pytest
import numpy as np
from scipy.sparse import csr_matrix
from app.engine import recommend_for_user, recommend_by_books

@pytest.fixture
def tiny_ctx():
    # 2 users × 3 books: user 1 rates book0=5, user2 rates book1=4, book2=3
    data = [5,4,3]; rows=[0,1,1]; cols=[0,1,2]
    matrix = csr_matrix((data,(rows,cols)), shape=(2,3))
    ctx = {
      "matrix": matrix,
      "user_map": {1:0, 2:1},
      "rev_book_map": {0:"X",1:"Y",2:"Z"},
      "isbn_to_title": {"X":"Ex","Y":"Why","Z":"Zed"},
      "book_map": {"X":0,"Y":1,"Z":2}
    }
    return ctx

def test_recommend_for_user_excludes_seen(tiny_ctx):
    recs = recommend_for_user(1, tiny_ctx, k=1, top_n=2)
    # user1 has seen only "X"
    assert all(r["Book_ID"]!="X" for r in recs)
    assert {r["Book_ID"] for r in recs} == {"Y","Z"}

def test_recommend_by_books_scores(tiny_ctx):
    # pretend user likes "Y"
    recs = recommend_by_books(["Y"], tiny_ctx, k=1, top_n=2)
    # only Z and X remain; X has rating 5 by user1, Z has 3 by user2
    assert recs[0]["Book_ID"]=="X"
    assert pytest.approx(recs[0]["Recommendation_Score"]) == 5
