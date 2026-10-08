import pytest

from cache_service.payload import interleave, payload_fingerprint


def test_interleave_alternates_items() -> None:
    assert interleave(["A", "B"], ["x", "y"]) == "A, x, B, y"


def test_fingerprint_keeps_item_boundaries() -> None:
    assert payload_fingerprint(["a b"], ["c"]) != payload_fingerprint(["a", "b"], ["c"])


def test_fingerprint_depends_on_list_order() -> None:
    assert payload_fingerprint(["a"], ["b"]) != payload_fingerprint(["b"], ["a"])


def test_interleave_rejects_lists_of_different_length() -> None:
    with pytest.raises(ValueError, match="zip"):
        interleave(["A"], ["x", "y"])
