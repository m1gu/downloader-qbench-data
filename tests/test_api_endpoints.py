from __future__ import annotations

from datetime import date, datetime

from fastapi.testclient import TestClient
from downloader_qbench_data.api import create_app
from downloader_qbench_data.api.dependencies import get_db_session
from downloader_qbench_data.api.schemas import (
    DailyActivityPoint,
    DailyActivityResponse,
    DailyTATPoint,
    MetricsSummaryKPI,
    MetricsSummaryResponse,
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
    TopCustomerItem,
    TopCustomersResponse,
    NewCustomerItem,
    NewCustomersResponse,
    ReportsOverviewResponse,
    TestsTATDailyResponse,
)


def create_test_client(monkeypatch):
    app = create_app()
    def _dummy_session():
        yield object()
    app.dependency_overrides[get_db_session] = _dummy_session
    client = TestClient(app)
    return client


def test_metrics_summary_endpoint(monkeypatch):
    response_payload = MetricsSummaryResponse(
        kpis=MetricsSummaryKPI(
            total_samples=205,
            total_tests=616,
            total_customers=4,
            total_reports=74,
            average_tat_hours=42.0,
        ),
        last_updated_at=None,
        range_start=datetime(2025, 10, 11),
        range_end=datetime(2025, 10, 17),
    )
    monkeypatch.setattr(
        "downloader_qbench_data.api.routers.metrics.get_metrics_summary",
        lambda *args, **kwargs: response_payload,
    )
    client = create_test_client(monkeypatch)
    resp = client.get("/api/v1/metrics/summary")
    assert resp.status_code == 200
    assert resp.json()["kpis"]["total_tests"] == 616


def test_daily_activity_endpoint(monkeypatch):
    response_payload = DailyActivityResponse(
        current=[
            DailyActivityPoint(date=date(2025, 10, 15), samples=20, tests=40),
            DailyActivityPoint(date=date(2025, 10, 16), samples=25, tests=50),
        ],
        previous=[
            DailyActivityPoint(date=date(2025, 10, 13), samples=10, tests=20),
            DailyActivityPoint(date=date(2025, 10, 14), samples=15, tests=30),
        ],
    )
    monkeypatch.setattr(
        "downloader_qbench_data.api.routers.metrics.get_daily_activity",
        lambda *args, **kwargs: response_payload,
    )
    client = create_test_client(monkeypatch)
    resp = client.get("/api/v1/metrics/activity/daily?compare_previous=true")
    assert resp.status_code == 200
    assert len(resp.json()["current"]) == 2


def test_new_customers_endpoint(monkeypatch):
    response_payload = NewCustomersResponse(
        customers=[
            NewCustomerItem(id=1, name="Acme", created_at=datetime(2025, 10, 16)),
            NewCustomerItem(id=2, name="Globex", created_at=datetime(2025, 10, 15)),
        ]
    )
    monkeypatch.setattr(
        "downloader_qbench_data.api.routers.metrics.get_new_customers",
        lambda *args, **kwargs: response_payload,
    )
    client = create_test_client(monkeypatch)
    resp = client.get("/api/v1/metrics/customers/new")
    assert resp.status_code == 200
    assert resp.json()["customers"][0]["name"] == "Acme"


def test_top_customers_endpoint(monkeypatch):
    response_payload = TopCustomersResponse(
        customers=[
            TopCustomerItem(id=1, name="Acme", tests=50),
            TopCustomerItem(id=2, name="Globex", tests=30),
        ]
    )
    monkeypatch.setattr(
        "downloader_qbench_data.api.routers.metrics.get_top_customers_by_tests",
        lambda *args, **kwargs: response_payload,
    )
    client = create_test_client(monkeypatch)
    resp = client.get("/api/v1/metrics/customers/top-tests")
    assert resp.status_code == 200
    assert resp.json()["customers"][0]["tests"] == 50


def test_reports_overview_endpoint(monkeypatch):
    response_payload = ReportsOverviewResponse(
        total_reports=74,
        reports_within_sla=60,
        reports_beyond_sla=14,
    )
    monkeypatch.setattr(
        "downloader_qbench_data.api.routers.metrics.get_reports_overview",
        lambda *args, **kwargs: response_payload,
    )
    client = create_test_client(monkeypatch)
    resp = client.get("/api/v1/metrics/reports/overview")
    assert resp.status_code == 200
    assert resp.json()["reports_within_sla"] == 60


def test_tests_tat_daily_endpoint(monkeypatch):
    response_payload = TestsTATDailyResponse(
        points=[
            DailyTATPoint(date=date(2025, 10, 15), average_hours=40, within_sla=30, beyond_sla=5),
            DailyTATPoint(date=date(2025, 10, 16), average_hours=42, within_sla=28, beyond_sla=6),
        ],
        moving_average_hours=[
            TimeSeriesPoint(period_start=date(2025, 10, 16), value=41.0),
        ],
    )
    monkeypatch.setattr(
        "downloader_qbench_data.api.routers.metrics.get_tests_tat_daily",
        lambda *args, **kwargs: response_payload,
    )
    client = create_test_client(monkeypatch)
    resp = client.get("/api/v1/metrics/tests/tat-daily")
    assert resp.status_code == 200
    assert resp.json()["points"][0]["within_sla"] == 30


def test_samples_overview_endpoint(monkeypatch):
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
