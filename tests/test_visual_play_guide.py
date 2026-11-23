"""Regression checks for the compact visual Pick 3 guide."""
import pytest

pytest.importorskip("PySide6")
from lotterydash.five_panel_editor import visual_example


def test_box_unique_digits():
    text = visual_example("123", "box")
    assert "6 possible orders" in text
    assert all(item in text for item in ("123", "132", "213", "231", "312", "321"))


def test_box_repeated_digits():
    text = visual_example("112", "box")
    assert "3 possible orders" in text
    assert all(item in text for item in ("112", "121", "211"))


def test_box_all_equal():
    assert "not applicable" in visual_example("777", "box")


def test_straight_preserves_leading_zero():
    assert "007" in visual_example("007", "straight")


def test_pair_examples():
    assert "12" in visual_example("123", "front_pair")
    assert "23" in visual_example("123", "back_pair")


def test_invalid_input_uses_demo_digits():
    assert "123" in visual_example("", "straight")
