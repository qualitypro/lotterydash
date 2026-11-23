"""Element Guide content integrity checks."""
import pytest
pytest.importorskip("PySide6")
from lotterydash.element_guide import ENTRIES, CATEGORIES


def test_guide_has_unique_nonempty_entries():
    names = [name for name, _, _ in ENTRIES]
    assert len(names) == len(set(names))
    assert all(name and category and meaning for name, category, meaning in ENTRIES)


def test_every_entry_has_category():
    assert all(category in CATEGORIES for _, category, _ in ENTRIES)


def test_essential_pick3_and_app_terms():
    names = {name for name, _, _ in ENTRIES}
    assert {"Straight", "Box", "Fireball", "Panel A–E",
            "Mapping draft", "Printer calibration", "Save"} <= names
