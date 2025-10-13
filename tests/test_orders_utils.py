from downloader_qbench_data.ingestion.orders import _safe_int


def test_safe_int_with_valid_values():
    assert _safe_int(5) == 5
    assert _safe_int("10") == 10


def test_safe_int_with_invalid_values(caplog):
    caplog.set_level("WARNING")
    assert _safe_int(None) is None
    assert _safe_int("not-a-number") is None
