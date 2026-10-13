from __future__ import annotations

import json

import numpy as np
import pytest

from madkhal.core import determinism, jsonio


@pytest.mark.req("MK-X-004")
def test_substream_same_seed_same_numbers() -> None:
    a = determinism.substream(7, "estimator.draws").random(5)
    b = determinism.substream(7, "estimator.draws").random(5)
    assert np.array_equal(a, b)


@pytest.mark.req("MK-X-004")
def test_substream_labels_are_independent() -> None:
    a = determinism.substream(7, "a").random(5)
    b = determinism.substream(7, "b").random(5)
    assert not np.array_equal(a, b)


@pytest.mark.req("MK-X-004")
def test_seed_bounds() -> None:
    with pytest.raises(ValueError):
        determinism.check_seed(-1)
    with pytest.raises(ValueError):
        determinism.check_seed(determinism.MAX_SEED + 1)


@pytest.mark.req("MK-X-005")
def test_json_keeps_arabic_and_sorts_keys(tmp_path) -> None:  # type: ignore[no-untyped-def]
    obj = {"b": "مدخل", "a": 1.5, "nan": float("nan")}
    path = tmp_path / "x.json"
    jsonio.write_json(path, obj)
    raw = path.read_bytes()
    assert "مدخل".encode() in raw
    assert b"\r\n" not in raw
    text = raw.decode("utf-8")
    assert text.index('"a"') < text.index('"b"')
    assert json.loads(text)["nan"] is None


@pytest.mark.req("MK-X-005")
def test_inputs_hash_is_order_independent() -> None:
    assert jsonio.inputs_hash({"a": 1, "b": [1, 2]}) == jsonio.inputs_hash({"b": [1, 2], "a": 1})
    assert jsonio.inputs_hash({"a": 1}) != jsonio.inputs_hash({"a": 2})
