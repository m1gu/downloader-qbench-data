from downloader_qbench_data.ingestion.utils import ensure_int_list, safe_int


def test_safe_int_with_valid_values():
    assert safe_int(5) == 5
    assert safe_int("10") == 10


def test_safe_int_with_invalid_values(caplog):
    caplog.set_level("WARNING")
    assert safe_int(None) is None
    assert safe_int("not-a-number") is None


def test_ensure_int_list_filters_invalid(caplog):
    caplog.set_level("WARNING")
    assert ensure_int_list([1, "2", "bad", None]) == [1, 2]
    assert ensure_int_list(None) == []
