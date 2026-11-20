from app.schema.general import ApiResponse, Meta, list_response


def test_api_response_defaults():
    r = ApiResponse[str](data="hi")
    assert r.model_dump() == {"data": "hi", "meta": {"count": None}}


def test_list_response_sets_count():
    r = list_response([1, 2, 3])
    assert r.data == [1, 2, 3]
    assert r.meta == Meta(count=3)
