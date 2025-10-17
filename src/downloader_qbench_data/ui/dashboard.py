"""Main PySide6 dashboard window."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Optional

from PySide6 import QtCore, QtGui, QtWidgets

from .api_client import ApiClient
from .styles import GLOBAL_STYLE
from .widgets import KpiCard, SamplesTestsBarChart, TableCard, TatLineChart, format_hours_to_days


@dataclass
class DashboardConfig:
    api_base_url: str = os.environ.get("DASHBOARD_API_BASE_URL", "http://localhost:8000/api/v1")
    compare_previous: bool = True
    default_days: int = 7


class ApiWorker(QtCore.QRunnable):
    """Runs API calls in a background thread."""

    def __init__(self, fn, *args, **kwargs) -> None:
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    @QtCore.Slot()
    def run(self) -> None:
        try:
            result = self.fn(*self.args, **self.kwargs)
        except Exception as exc:  # pragma: no cover - propagation
            self.signals.error.emit(exc)
        else:
            self.signals.result.emit(result)


class WorkerSignals(QtCore.QObject):
    """Signals shared by ApiWorker."""

    result = QtCore.Signal(object)
    error = QtCore.Signal(Exception)


class DashboardWindow(QtWidgets.QMainWindow):
    """Main dashboard window."""

    def __init__(
        self,
        *,
        api_client: Optional[ApiClient] = None,
        config: Optional[DashboardConfig] = None,
        parent: Optional[QtWidgets.QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("QBench Dashboard")
        self.resize(1280, 900)
        self.setStyleSheet(GLOBAL_STYLE)

        self.config = config or DashboardConfig()
        self.api_client = api_client or ApiClient(self.config.api_base_url)
        self.thread_pool = QtCore.QThreadPool.globalInstance()

        # Date range controls -------------------------------------------------
        self.date_from_edit = QtWidgets.QDateEdit(self)
        self.date_from_edit.setCalendarPopup(True)
        self.date_from_edit.setDisplayFormat("yyyy-MM-dd")

        self.date_to_edit = QtWidgets.QDateEdit(self)
        self.date_to_edit.setCalendarPopup(True)
        self.date_to_edit.setDisplayFormat("yyyy-MM-dd")

        self.refresh_button = QtWidgets.QPushButton("Refresh", self)
        self.refresh_button.setObjectName("PrimaryButton")
        self.refresh_button.clicked.connect(self.reload_data)

        today = date.today()
        default_start = today - timedelta(days=self.config.default_days - 1)
        self.date_from_edit.setDate(QtCore.QDate(default_start.year, default_start.month, default_start.day))
        self.date_to_edit.setDate(QtCore.QDate(today.year, today.month, today.day))

        # KPI Cards -----------------------------------------------------------
        self.samples_card = KpiCard("Samples")
        self.tests_card = KpiCard("Tests")
        self.customers_card = KpiCard("Customers")
        self.reports_card = KpiCard("Reports")
        self.tat_card = KpiCard("Avg TAT (hrs)")

        # Charts / Tables -----------------------------------------------------
        self.bar_chart = SamplesTestsBarChart()
        self.new_customers_table = TableCard("New customers", ["ID", "Name", "Created"])
        self.top_customers_table = TableCard("Top customers with tests", ["ID", "Name", "Tests"])
        self.tat_chart = TatLineChart()

        # Summary label -------------------------------------------------------
        self.last_update_label = QtWidgets.QLabel("", self)
        self.last_update_label.setObjectName("SubtitleLabel")

        # Layout --------------------------------------------------------------
        container = QtWidgets.QWidget()
        container.setObjectName("DashboardContainer")
        main_layout = QtWidgets.QVBoxLayout(container)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(20)

        # Filters
        filter_layout = QtWidgets.QHBoxLayout()
        filter_layout.setSpacing(12)
        filter_layout.addWidget(QtWidgets.QLabel("From:", self))
        filter_layout.addWidget(self.date_from_edit)
        filter_layout.addWidget(QtWidgets.QLabel("To:", self))
        filter_layout.addWidget(self.date_to_edit)
        filter_layout.addStretch(1)
        filter_layout.addWidget(self.refresh_button)
        main_layout.addLayout(filter_layout)
        main_layout.addWidget(self.last_update_label)

        # KPI row
        kpi_layout = QtWidgets.QHBoxLayout()
        kpi_layout.setSpacing(16)
        for card in (self.samples_card, self.tests_card, self.customers_card, self.reports_card, self.tat_card):
            card.setMinimumWidth(150)
            kpi_layout.addWidget(card)
        main_layout.addLayout(kpi_layout)

        # Bar chart row
        main_layout.addWidget(self.bar_chart)

        # Tables row
        tables_layout = QtWidgets.QHBoxLayout()
        tables_layout.setSpacing(16)
        tables_layout.addWidget(self.new_customers_table)
        tables_layout.addWidget(self.top_customers_table)
        main_layout.addLayout(tables_layout)

        # TAT chart
        self.tat_chart.setMinimumHeight(320)
        main_layout.addWidget(self.tat_chart)
        main_layout.addStretch(1)

        # Scroll area setup
        scroll_area = QtWidgets.QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(container)
        self.setCentralWidget(scroll_area)

        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Loading data…")

        QtCore.QTimer.singleShot(100, self.reload_data)

    # ------------------------------------------------------------------ API --

    def _current_date_range(self) -> tuple[date, date]:
        start = self.date_from_edit.date().toPython()
        end = self.date_to_edit.date().toPython()
        return start, end

    def reload_data(self) -> None:
        start, end = self._current_date_range()
        self.status_bar.showMessage("Refreshing dashboard…", 2000)
        self._run_api(self.api_client.fetch_summary, self._handle_summary, date_from=start, date_to=end)
        self._run_api(
            self.api_client.fetch_daily_activity,
            self._handle_daily_activity,
            date_from=start,
            date_to=end,
            compare_previous=self.config.compare_previous,
        )
        self._run_api(
            self.api_client.fetch_new_customers,
            self._handle_new_customers,
            date_from=start,
            date_to=end,
            limit=10,
        )
        self._run_api(
            self.api_client.fetch_top_customers,
            self._handle_top_customers,
            date_from=start,
            date_to=end,
            limit=10,
        )
        self._run_api(
            self.api_client.fetch_reports_overview,
            self._handle_reports_overview,
            date_from=start,
            date_to=end,
        )
        self._run_api(
            self.api_client.fetch_tat_daily,
            self._handle_tat_daily,
            date_from=start,
            date_to=end,
        )

    def _run_api(self, fn, callback, *args, **kwargs) -> None:
        worker = ApiWorker(fn, *args, **kwargs)
        worker.signals.result.connect(callback)
        worker.signals.error.connect(self._handle_error)
        self.thread_pool.start(worker)

    # -------------------------------------------------------------- Handlers --
    def _handle_summary(self, payload: dict) -> None:
        kpis = payload.get("kpis") or {}
        self.samples_card.update_value(str(kpis.get("total_samples", "--")))
        self.tests_card.update_value(str(kpis.get("total_tests", "--")))
        self.customers_card.update_value(str(kpis.get("total_customers", "--")))
        self.reports_card.update_value(str(kpis.get("total_reports", "--")))
        avg_tat = kpis.get("average_tat_hours")
        self.tat_card.update_value(format_hours_to_days(avg_tat))

        last_updated = payload.get("last_updated_at")
        if isinstance(last_updated, datetime):
            self.last_update_label.setText(f"Last update: {last_updated.isoformat(sep=' ', timespec='minutes')}")
        else:
            self.last_update_label.setText("")

    def _handle_daily_activity(self, payload: dict) -> None:
        samples = payload.get("current_samples", {})
        tests = payload.get("current_tests", {})
        self.bar_chart.update_data(samples, tests)

    def _handle_new_customers(self, customers: list[dict]) -> None:
        rows = [
            (
                customer.get("id"),
                customer.get("name"),
                customer.get("created_at").strftime("%Y-%m-%d %H:%M") if customer.get("created_at") else "",
            )
            for customer in customers
        ]
        self.new_customers_table.update_rows(rows)

    def _handle_top_customers(self, customers: list[dict]) -> None:
        rows = [
            (
                customer.get("id"),
                customer.get("name"),
                customer.get("tests"),
            )
            for customer in customers
        ]
        self.top_customers_table.update_rows(rows)

    def _handle_reports_overview(self, payload: dict) -> None:
        total = payload.get("total_reports", 0)
        within = payload.get("reports_within_sla", 0)
        beyond = payload.get("reports_beyond_sla", 0)
        total_str = f"{total} total (within SLA: {within}, beyond: {beyond})"
        self.reports_card.update_value(str(total), caption=total_str)

    def _handle_tat_daily(self, payload: dict) -> None:
        points = sorted(
            (
                item["date"],
                item.get("average_hours"),
                item.get("within_sla", 0),
                item.get("beyond_sla", 0),
            )
            for item in payload.get("points", [])
            if item.get("date")
        )
        if not points:
            self.tat_chart.update_data([], [])
            return

        moving = sorted(
            (item["period_start"], item.get("value"))
            for item in payload.get("moving_average_hours", [])
            if item.get("period_start") and item.get("value") is not None
        )
        self.tat_chart.update_data(points, moving)

    def _handle_error(self, error: Exception) -> None:  # pragma: no cover - UI feedback
        self.status_bar.showMessage(f"Failed to update dashboard: {error}", 5000)

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:  # noqa: N802 - Qt signature
        try:
            self.api_client.close()
        except Exception:  # pragma: no cover
            pass
        super().closeEvent(event)


__all__ = ["DashboardWindow", "DashboardConfig"]
