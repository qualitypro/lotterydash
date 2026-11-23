"""Sprint 04F: global selection completeness and safe review gates."""
import pytest
from lotterydash.global_options import GLOBAL_FIELDS, mapping_summary, validate_global_fields


def test_global_ids_are_unique():
    assert len(GLOBAL_FIELDS) == len(set(GLOBAL_FIELDS)) == 3


def test_incomplete_global_mapping_rejected():
    with pytest.raises(ValueError, match="global.quick-picks.5-dollar"):
        validate_global_fields(dict.fromkeys(GLOBAL_FIELDS[:2]))


def test_all_global_fields_accepted():
    assert validate_global_fields(dict.fromkeys(GLOBAL_FIELDS))


def test_complete_mapping_requires_218():
    fields = {
        f"{panel}.num.{i}": None
        for panel in "abcde" for i in range(43)
    }
    assert not mapping_summary(fields)["complete"]
    fields.update(dict.fromkeys(GLOBAL_FIELDS))
    summary = mapping_summary(fields)
    assert summary["complete"]
    assert summary["mapped_fields"] == 218
    assert summary["global_missing"] == []
