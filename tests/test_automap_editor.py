"""Safety tests for non-destructive AutoMap editor exports."""
import json
import pytest

from lotterydash.automap_editor import safe_destination, load_review_data
from lotterydash.calibration import ScanPoint, save_mapping


def test_refuses_original_mapping(tmp_path):
    source = tmp_path / "mapping.json"
    source.write_text("original")
    with pytest.raises(ValueError, match="source mapping"):
        safe_destination(source, source)


def test_refuses_existing_output(tmp_path):
    source = tmp_path / "mapping.json"
    output = tmp_path / "draft.json"
    output.write_text("existing")
    with pytest.raises(FileExistsError):
        safe_destination(source, output)


def test_accepts_new_output(tmp_path):
    source = tmp_path / "mapping.json"
    output = tmp_path / "new.json"
    assert safe_destination(source, output) == output.resolve()


def test_reads_schema_v1_mapping(tmp_path):
    source = tmp_path / "mapping.json"
    save_mapping(source, {"a.num.col1.0": ScanPoint(.1, .2)}, 100, 200)
    points, metadata = load_review_data(source)
    assert len(points) == 1
    assert metadata["schema_version"] == 1
