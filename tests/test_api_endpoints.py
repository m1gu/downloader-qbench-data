from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient
from downloader_qbench_data.api import create_app
from downloader_qbench_data.api.dependencies import get_db_session
from downloader_qbench_data.api.schemas import (
    MetricsFiltersResponse,
    SampleDetailResponse,
    SamplesDistributionItem,
    SamplesOverviewKPI,
    SamplesOverviewResponse,
    TestDetailResponse,
    TestsDistributionItem,
    TestsOverviewKPI,
    TestsOverviewResponse,
    TestsTATBreakdownItem,
    TestsTATBreakdownResponse,
    TestsTATDistributionBucket,
    TestsTATMetrics,
    TestsTATResponse,
    TimeSeriesPoint,
)


def create_test_client(monkeypatch):
    app = create_app()
    def _dummy_session():
        yield object()
    app.dependency_overrides[get_db_session] = _dummy_session
    client = TestClient(app)
    return client
    response_payload = SamplesOverviewResponse(
        kpis=SamplesOverviewKPI(total_samples=10, completed_samples=6, pending_samples=4),
        by_state=[SamplesDistributionItem(key="completed", count=6)],
        by_matrix_type=[SamplesDistributionItem(key="Saliva", count=4)],
        created_vs_completed=[
            SamplesDistributionItem(key="created", count=10),
            SamplesDistributionItem(key="completed", count=6),
        ],
    )
    monkeypatch.setattr(
        "downloader_qbench_data.api.routers.metrics.get_samples_overview",
        lambda *args, **kwargs: response_payload,
    )
    client = create_test_client(monkeypatch)
    resp = client.get("/api/v1/metrics/samples/overview")
    assert resp.status_code == 200
    assert resp.json()["kpis"]["total_samples"] == 10


def test_tests_overview_endpoint(monkeypatch):
    response_payload = TestsOverviewResponse(
        kpis=TestsOverviewKPI(total_tests=5, completed_tests=3, pending_tests=2),
        by_state=[TestsDistributionItem(key="reported", count=3)],
        by_label=[TestsDistributionItem(key="PCR", count=2)],
    )
    monkeypatch.setattr(
        "downloader_qbench_data.api.routers.metrics.get_tests_overview",
        lambda *args, **kwargs: response_payload,
    )
    client = create_test_client(monkeypatch)
    resp = client.get("/api/v1/metrics/tests/overview")
    assert resp.status_code == 200
    assert resp.json()["kpis"]["completed_tests"] == 3


def test_tests_tat_endpoint(monkeypatch):
    response_payload = TestsTATResponse(
        metrics=TestsTATMetrics(
            average_hours=42,
            median_hours=40,
            p95_hours=60,
            completed_within_sla=8,
            completed_beyond_sla=2,
        ),
        distribution=[
            TestsTATDistributionBucket(label="0-24h", count=3),
            TestsTATDistributionBucket(label="24-48h", count=4),
        ],
        series=[TimeSeriesPoint(period_start=date(2025, 10, 12), value=36.5)],
    )
    monkeypatch.setattr(
        "downloader_qbench_data.api.routers.metrics.get_tests_tat",
        lambda *args, **kwargs: response_payload,
    )
    client = create_test_client(monkeypatch)
    resp = client.get("/api/v1/metrics/tests/tat?group_by=day")
    assert resp.status_code == 200
    assert resp.json()["metrics"]["average_hours"] == 42


def test_tests_tat_breakdown_endpoint(monkeypatch):
    response_payload = TestsTATBreakdownResponse(
        breakdown=[
            TestsTATBreakdownItem(
                label="PCR",
                average_hours=36,
                median_hours=34,
                p95_hours=55,
                total_tests=10,
            )
        ]
    )
    monkeypatch.setattr(
        "downloader_qbench_data.api.routers.metrics.get_tests_tat_breakdown",
        lambda *args, **kwargs: response_payload,
    )
    client = create_test_client(monkeypatch)
    resp = client.get("/api/v1/metrics/tests/tat-breakdown")
    assert resp.status_code == 200
    assert resp.json()["breakdown"][0]["label"] == "PCR"


def test_metrics_filters_endpoint(monkeypatch):
    response_payload = MetricsFiltersResponse(
        customers=[{"id": 1, "name": "Acme"}],
        sample_states=["received"],
        test_states=["complete"],
        last_updated_at=None,
    )
    monkeypatch.setattr(
        "downloader_qbench_data.api.routers.metrics.get_metrics_filters",
        lambda *args, **kwargs: response_payload,
    )
    client = create_test_client(monkeypatch)
    resp = client.get("/api/v1/metrics/common/filters")
    assert resp.status_code == 200
    assert resp.json()["customers"][0]["name"] == "Acme"


def test_get_sample_detail(monkeypatch):
    response_payload = SampleDetailResponse(
        id=1,
        sample_name="Sample A",
        custom_formatted_id="S-001",
        order_id=10,
        has_report=True,
        batch_ids=[5],
        completed_date=None,
        date_created=None,
        start_date=None,
        matrix_type="Blood",
        state="completed",
        test_count=3,
        raw_payload={"id": 1},
        order={"id": 10, "custom_formatted_id": "O-10", "state": "completed"},
        batches=[{"id": 5, "display_name": "Batch 1"}],
    )
    monkeypatch.setattr(
        "downloader_qbench_data.api.routers.entities.entities_service.get_sample_detail",
        lambda *args, **kwargs: response_payload,
    )
    client = create_test_client(monkeypatch)
    resp = client.get("/api/v1/entities/samples/1")
    assert resp.status_code == 200
    assert resp.json()["sample_name"] == "Sample A"


def test_get_sample_detail_not_found(monkeypatch):
    monkeypatch.setattr(
        "downloader_qbench_data.api.routers.entities.entities_service.get_sample_detail",
        lambda *args, **kwargs: None,
    )
    client = create_test_client(monkeypatch)
    resp = client.get("/api/v1/entities/samples/999")
    assert resp.status_code == 404


def test_get_test_detail(monkeypatch):
    response_payload = TestDetailResponse(
        id=1,
        sample_id=1,
        batch_ids=[5],
        date_created=None,
        state="complete",
        has_report=True,
        report_completed_date=None,
        label_abbr="PCR",
        title="PCR Test",
        worksheet_raw={},
        raw_payload={"id": 1},
        sample={"id": 1, "sample_name": "Sample A", "state": "complete"},
        batches=[{"id": 5, "display_name": "Batch 1"}],
    )
    monkeypatch.setattr(
        "downloader_qbench_data.api.routers.entities.entities_service.get_test_detail",
        lambda *args, **kwargs: response_payload,
    )
    client = create_test_client(monkeypatch)
    resp = client.get("/api/v1/entities/tests/1")
    assert resp.status_code == 200
    assert resp.json()["label_abbr"] == "PCR"


def test_get_test_detail_not_found(monkeypatch):
    monkeypatch.setattr(
        "downloader_qbench_data.api.routers.entities.entities_service.get_test_detail",
        lambda *args, **kwargs: None,
    )
    client = create_test_client(monkeypatch)
    resp = client.get("/api/v1/entities/tests/999")
    assert resp.status_code == 404
