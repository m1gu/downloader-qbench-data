from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi.testclient import TestClient
from downloader_qbench_data.api import create_app
from downloader_qbench_data.api.dependencies import get_db_session
from downloader_qbench_data.api.schemas import (
    CustomerAlertItem,
    CustomerAlertsResponse,
    CustomerHeatmapPoint,
    DailyActivityPoint,
    DailyActivityResponse,
    DailyTATPoint,
    MetricsFiltersResponse,
    MetricsSummaryKPI,
    MetricsSummaryResponse,
    NewCustomerItem,
    NewCustomersResponse,
    OrdersFunnelResponse,
    OrdersFunnelStage,
    OrdersSlowestResponse,
    OrdersThroughputPoint,
    OrdersThroughputResponse,
    OrdersThroughputTotals,
    OverdueClientSummary,
    OverdueHeatmapCell,
    OverdueOrderItem,
    OverdueOrdersKpis,
    OverdueOrdersResponse,
    OverdueStateBreakdown,
    OverdueTimelinePoint,
    ReadyToReportSampleItem,
    QualityKpiOrders,
    QualityKpiTests,
    QualityKpisResponse,
    ReportsOverviewResponse,
    SampleDetailResponse,
    SamplesCycleMatrixItem,
    SamplesCycleTimePoint,
    SamplesCycleTimeResponse,
    SamplesCycleTimeTotals,
    SamplesDistributionItem,
    SamplesOverviewKPI,
    SamplesOverviewResponse,
    SlowOrderItem,
    TestDetailResponse,
    TestStateBucket,
    TestStatePoint,
    TestsDistributionItem,
    TestsLabelCountItem,
    TestsLabelDistributionResponse,
    TestsOverviewKPI,
    TestsOverviewResponse,
    TestsTATBreakdownItem,
    TestsTATBreakdownResponse,
    TestsTATDailyResponse,
    TestsTATDistributionBucket,
    TestsTATMetrics,
    TestsTATResponse,
    TestsStateDistributionResponse,
    TimeSeriesPoint,
    TopCustomerItem,
    TopCustomersResponse,
    SyncStatusResponse,
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
            DailyActivityPoint(date=date(2025, 10, 15), samples=20, tests=40, tests_reported=22),
            DailyActivityPoint(date=date(2025, 10, 16), samples=25, tests=50, tests_reported=28),
        ],
        previous=[
            DailyActivityPoint(date=date(2025, 10, 13), samples=10, tests=20, tests_reported=12),
            DailyActivityPoint(date=date(2025, 10, 14), samples=15, tests=30, tests_reported=18),
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
            TopCustomerItem(id=1, name="Acme", tests=50, tests_reported=32),
            TopCustomerItem(id=2, name="Globex", tests=30, tests_reported=18),
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
    assert resp.json()["customers"][0]["tests_reported"] == 32


def test_sync_status_endpoint(monkeypatch):
    response_payload = SyncStatusResponse(
        entity="tests",
        updated_at=datetime(2025, 10, 30, 11, 47, tzinfo=timezone.utc),
    )
    monkeypatch.setattr(
        "downloader_qbench_data.api.routers.metrics.get_sync_status",
        lambda *args, **kwargs: response_payload,
    )
    client = create_test_client(monkeypatch)
    resp = client.get("/api/v1/metrics/sync/status?entity=tests")
    assert resp.status_code == 200
    body = resp.json()
    assert body["entity"] == "tests"
    assert body["updated_at"] == "2025-10-30T11:47:00+00:00"


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


def test_tests_label_distribution_endpoint(monkeypatch):
    response_payload = TestsLabelDistributionResponse(
        labels=[
            TestsLabelCountItem(label="CN", count=40),
            TestsLabelCountItem(label="PS", count=25),
        ]
    )
    monkeypatch.setattr(
        "downloader_qbench_data.api.routers.metrics.get_tests_label_distribution",
        lambda *args, **kwargs: response_payload,
    )
    client = create_test_client(monkeypatch)
    resp = client.get("/api/v1/metrics/tests/label-distribution")
    assert resp.status_code == 200
    assert resp.json()["labels"][0]["label"] == "CN"


def test_orders_throughput_endpoint(monkeypatch):
    response_payload = OrdersThroughputResponse(
        interval="week",
        points=[
            OrdersThroughputPoint(
                period_start=date(2025, 10, 12),
                orders_created=8,
                orders_completed=6,
                average_completion_hours=48.0,
                median_completion_hours=36.0,
            )
        ],
        totals=OrdersThroughputTotals(
            orders_created=8,
            orders_completed=6,
            average_completion_hours=48.0,
            median_completion_hours=36.0,
        ),
    )
    monkeypatch.setattr(
        "downloader_qbench_data.api.routers.analytics.get_orders_throughput",
        lambda *args, **kwargs: response_payload,
    )
    client = create_test_client(monkeypatch)
    resp = client.get("/api/v1/analytics/orders/throughput?interval=week")
    assert resp.status_code == 200
    assert resp.json()["totals"]["orders_created"] == 8


def test_samples_cycle_time_endpoint(monkeypatch):
    response_payload = SamplesCycleTimeResponse(
        interval="day",
        points=[
            SamplesCycleTimePoint(
                period_start=date(2025, 10, 16),
                completed_samples=5,
                average_cycle_hours=30.0,
                median_cycle_hours=28.0,
            )
        ],
        totals=SamplesCycleTimeTotals(
            completed_samples=5,
            average_cycle_hours=30.0,
            median_cycle_hours=28.0,
        ),
        by_matrix_type=[
            SamplesCycleMatrixItem(
                matrix_type="Cured Flower",
                completed_samples=3,
                average_cycle_hours=32.0,
            )
        ],
    )
    monkeypatch.setattr(
        "downloader_qbench_data.api.routers.analytics.get_samples_cycle_time",
        lambda *args, **kwargs: response_payload,
    )
    client = create_test_client(monkeypatch)
    resp = client.get("/api/v1/analytics/samples/cycle-time")
    assert resp.status_code == 200
    assert resp.json()["by_matrix_type"][0]["matrix_type"] == "Cured Flower"


def test_orders_funnel_endpoint(monkeypatch):
    response_payload = OrdersFunnelResponse(
        total_orders=12,
        stages=[
            OrdersFunnelStage(stage="created", count=12),
            OrdersFunnelStage(stage="received", count=9),
            OrdersFunnelStage(stage="completed", count=7),
            OrdersFunnelStage(stage="reported", count=5),
            OrdersFunnelStage(stage="on_hold", count=2),
        ],
    )
    monkeypatch.setattr(
        "downloader_qbench_data.api.routers.analytics.get_orders_funnel",
        lambda *args, **kwargs: response_payload,
    )
    client = create_test_client(monkeypatch)
    resp = client.get("/api/v1/analytics/orders/funnel")
    assert resp.status_code == 200
    assert resp.json()["stages"][0]["stage"] == "created"


def test_orders_slowest_endpoint(monkeypatch):
    response_payload = OrdersSlowestResponse(
        items=[
            SlowOrderItem(
                order_id=101,
                order_reference="bucket-2025-10-06",
                customer_name="Aggregate",
                state="completed",
                completion_hours=114.0,
                age_hours=115.0,
                date_created=datetime(2025, 10, 6, 12, 0, 0),
                date_completed=datetime(2025, 10, 11, 10, 0, 0),
            )
        ]
    )
    monkeypatch.setattr(
        "downloader_qbench_data.api.routers.analytics.get_slowest_orders",
        lambda *args, **kwargs: response_payload,
    )
    client = create_test_client(monkeypatch)
    resp = client.get("/api/v1/analytics/orders/slowest?limit=3")
    assert resp.status_code == 200
    assert resp.json()["items"][0]["order_reference"] == "bucket-2025-10-06"


def test_orders_overdue_endpoint(monkeypatch):
    response_payload = OverdueOrdersResponse(
        interval="week",
        minimum_days_overdue=30,
        warning_window_days=5,
        sla_hours=72.0,
        kpis=OverdueOrdersKpis(
            total_overdue=12,
            average_open_hours=850.5,
            max_open_hours=1200.0,
            percent_overdue_vs_active=0.6,
            overdue_beyond_sla=8,
            overdue_within_sla=4,
        ),
        top_orders=[
            OverdueOrderItem(
                order_id=501,
                custom_formatted_id="ORD-501",
                customer_id=42,
                customer_name="Arcanna LLC",
                state="ON HOLD",
                date_created=datetime(2025, 8, 15, 9, 30),
                open_hours=1200.0,
            )
        ],
        clients=[
            OverdueClientSummary(
                customer_id=42,
                customer_name="Arcanna LLC",
                overdue_orders=7,
                total_open_hours=4500.0,
                average_open_hours=642.8,
                max_open_hours=1200.0,
            )
        ],
        warning_orders=[
            OverdueOrderItem(
                order_id=610,
                custom_formatted_id="ORD-610",
                customer_id=77,
                customer_name="North Labs",
                state="IN PROGRESS",
                date_created=datetime(2025, 9, 25, 10, 0),
                open_hours=650.0,
            )
        ],
        timeline=[
            OverdueTimelinePoint(
                period_start=date(2025, 10, 6),
                overdue_orders=5,
            )
        ],
        heatmap=[
            OverdueHeatmapCell(
                customer_id=42,
                customer_name="Arcanna LLC",
                period_start=date(2025, 10, 6),
                overdue_orders=3,
            )
        ],
        state_breakdown=[
            OverdueStateBreakdown(state="ON HOLD", count=8, ratio=0.6667),
            OverdueStateBreakdown(state="IN PROGRESS", count=4, ratio=0.3333),
        ],
        ready_to_report_samples=[
            ReadyToReportSampleItem(
                sample_id=9001,
                sample_name="Sample R",
                sample_custom_id="S-9001",
                order_id=501,
                order_custom_id="ORD-501",
                customer_id=42,
                customer_name="Arcanna LLC",
                date_created=datetime(2025, 10, 1, 8, 0),
                completed_date=datetime(2025, 10, 5, 12, 0),
                tests_ready_count=3,
                tests_total_count=3,
            )
        ],
    )
    monkeypatch.setattr(
        "downloader_qbench_data.api.routers.analytics.get_overdue_orders",
        lambda *args, **kwargs: response_payload,
    )
    client = create_test_client(monkeypatch)
    resp = client.get("/api/v1/analytics/orders/overdue?min_days_overdue=30")
    assert resp.status_code == 200
    body = resp.json()
    assert body["kpis"]["total_overdue"] == 12
    assert body["top_orders"][0]["order_id"] == 501
    assert body["ready_to_report_samples"][0]["sample_custom_id"] == "S-9001"


def test_customers_alerts_endpoint(monkeypatch):
    response_payload = CustomerAlertsResponse(
        interval="week",
        sla_hours=48.0,
        min_alert_percentage=0.1,
        heatmap=[
            CustomerHeatmapPoint(
                customer_id=1,
                customer_name="Acme Labs",
                period_start=date(2025, 10, 6),
                total_tests=10,
                on_hold_tests=2,
                not_reportable_tests=1,
                sla_breach_tests=3,
                on_hold_ratio=0.2,
                not_reportable_ratio=0.1,
                sla_breach_ratio=0.3,
            )
        ],
        alerts=[
            CustomerAlertItem(
                customer_id=1,
                customer_name="Acme Labs",
                orders_total=5,
                orders_on_hold=1,
                orders_beyond_sla=1,
                tests_total=10,
                tests_on_hold=2,
                tests_not_reportable=1,
                tests_beyond_sla=3,
                primary_reason="tests_beyond_sla",
                primary_ratio=0.3,
                latest_activity_at=datetime(2025, 10, 6, 12, 0, 0),
            )
        ],
    )
    monkeypatch.setattr(
        "downloader_qbench_data.api.routers.analytics.get_customer_alerts",
        lambda *args, **kwargs: response_payload,
    )
    client = create_test_client(monkeypatch)
    resp = client.get("/api/v1/analytics/customers/alerts")
    assert resp.status_code == 200
    data = resp.json()
    assert data["alerts"][0]["customer_name"] == "Acme Labs"
    assert data["heatmap"][0]["on_hold_tests"] == 2


def test_tests_state_distribution_endpoint(monkeypatch):
    response_payload = TestsStateDistributionResponse(
        interval="week",
        states=["ON HOLD", "REPORTED"],
        series=[
            TestStatePoint(
                period_start=date(2025, 10, 6),
                total_tests=6,
                buckets=[
                    TestStateBucket(state="ON HOLD", count=2, ratio=0.3333),
                    TestStateBucket(state="REPORTED", count=4, ratio=0.6667),
                ],
            )
        ],
        totals=[
            TestStateBucket(state="ON HOLD", count=2, ratio=0.3333),
            TestStateBucket(state="REPORTED", count=4, ratio=0.6667),
        ],
    )
    monkeypatch.setattr(
        "downloader_qbench_data.api.routers.analytics.get_tests_state_distribution",
        lambda *args, **kwargs: response_payload,
    )
    client = create_test_client(monkeypatch)
    resp = client.get("/api/v1/analytics/tests/state-distribution")
    assert resp.status_code == 200
    assert resp.json()["states"] == ["ON HOLD", "REPORTED"]


def test_quality_kpis_endpoint(monkeypatch):
    response_payload = QualityKpisResponse(
        sla_hours=48.0,
        tests=QualityKpiTests(
            total_tests=20,
            on_hold_tests=3,
            not_reportable_tests=1,
            cancelled_tests=2,
            reported_tests=10,
            within_sla_tests=12,
            beyond_sla_tests=8,
            on_hold_ratio=0.15,
            not_reportable_ratio=0.05,
            beyond_sla_ratio=0.4,
        ),
        orders=QualityKpiOrders(
            total_orders=8,
            on_hold_orders=1,
            completed_orders=6,
            within_sla_orders=5,
            beyond_sla_orders=3,
            on_hold_ratio=0.125,
            beyond_sla_ratio=0.375,
        ),
    )
    monkeypatch.setattr(
        "downloader_qbench_data.api.routers.analytics.get_quality_kpis",
        lambda *args, **kwargs: response_payload,
    )
    client = create_test_client(monkeypatch)
    resp = client.get("/api/v1/analytics/kpis/quality")
    assert resp.status_code == 200
    assert resp.json()["tests"]["total_tests"] == 20
    assert resp.json()["orders"]["beyond_sla_ratio"] == 0.375


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
