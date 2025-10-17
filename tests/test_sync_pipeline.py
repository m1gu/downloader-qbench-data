from __future__ import annotations

import pytest

from downloader_qbench_data.ingestion import pipeline


@pytest.fixture
def sentinel_settings():
    return object()


def test_sync_all_entities_runs_in_order(monkeypatch, sentinel_settings):
    calls: list[tuple[str, bool, int | None]] = []
    progress_events: list[tuple[str, int, int | None]] = []

    def progress_callback(entity: str, processed: int, total: int | None) -> None:
        progress_events.append((entity, processed, total))

    for entity in pipeline.DEFAULT_SYNC_SEQUENCE:
        def make_stub(name: str):
            def _stub(settings, *, full_refresh, page_size, progress_callback=None):
                assert settings is sentinel_settings
                calls.append((name, full_refresh, page_size))
                if progress_callback:
                    progress_callback(1, 5)
                return f"{name}-summary"
            return _stub

        stub = make_stub(entity)
        monkeypatch.setitem(pipeline._SYNC_HANDLERS, entity, stub)

    monkeypatch.setattr(pipeline, "get_settings", lambda: sentinel_settings)

    summary = pipeline.sync_all_entities(
        entities=None,
        full_refresh=False,
        page_size=25,
        progress_callback=progress_callback,
        raise_on_error=False,
    )

    assert [call[0] for call in calls] == list(pipeline.DEFAULT_SYNC_SEQUENCE)
    for _, full_refresh, page_size in calls:
        assert full_refresh is False
        assert page_size == 25
    assert summary.succeeded is True
    assert len(summary.results) == len(pipeline.DEFAULT_SYNC_SEQUENCE)
    assert progress_events == [(entity, 1, 5) for entity in pipeline.DEFAULT_SYNC_SEQUENCE]


def test_sync_all_entities_stops_on_failure(monkeypatch, sentinel_settings):
    sequence = pipeline.DEFAULT_SYNC_SEQUENCE
    calls: list[str] = []

    def make_success_stub(name: str):
        def _stub(settings, *, full_refresh, page_size, progress_callback=None):
            calls.append(name)
            return f"{name}-summary"
        return _stub

    for entity in sequence:
        monkeypatch.setitem(pipeline._SYNC_HANDLERS, entity, make_success_stub(entity))

    def failing_stub(settings, *, full_refresh, page_size, progress_callback=None):
        calls.append("samples")
        raise RuntimeError("simulated failure")

    monkeypatch.setitem(pipeline._SYNC_HANDLERS, "samples", failing_stub)
    monkeypatch.setattr(pipeline, "get_settings", lambda: sentinel_settings)

    summary = pipeline.sync_all_entities(
        entities=None,
        raise_on_error=False,
    )

    assert summary.succeeded is False
    assert summary.failed_entity == "samples"
    assert summary.error_message == "simulated failure"
    assert [result.entity for result in summary.results] == ["customers", "orders", "samples"]
    assert all(result.succeeded for result in summary.results[:2])
    assert summary.results[-1].succeeded is False

    with pytest.raises(pipeline.SyncOrchestrationError):
        pipeline.sync_all_entities(entities=None, raise_on_error=True)
