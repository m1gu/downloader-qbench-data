#!/usr/bin/env python3
"""Script to fetch and save a single entity by ID from QBench."""

import argparse
import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from downloader_qbench_data.clients.qbench import QBenchClient
from downloader_qbench_data.config import get_settings
from downloader_qbench_data.ingestion.utils import (
    ensure_int_list,
    parse_qbench_datetime,
    safe_decimal,
    safe_int,
)
from downloader_qbench_data.storage import (
    Batch,
    Customer,
    Order,
    Sample,
    Test,
    session_scope,
)

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
LOGGER = logging.getLogger(__name__)

# Entity types and their corresponding fetch methods and models
ENTITY_CONFIG = {
    "customer": {
        "fetch_method": lambda client, entity_id: client.list_customers(page_num=1, page_size=1),  # Note: list doesn't support ID filter
        "model": Customer,
        "id_field": "id",
    },
    "order": {
        "fetch_method": lambda client, entity_id: client.fetch_order(entity_id),
        "model": Order,
        "id_field": "id",
    },
    "batch": {
        "fetch_method": lambda client, entity_id: client.list_batches(page_num=1, page_size=1),  # Note: list doesn't support ID filter
        "model": Batch,
        "id_field": "id",
    },
    "sample": {
        "fetch_method": lambda client, entity_id: client.fetch_sample(entity_id),
        "model": Sample,
        "id_field": "id",
    },
    "test": {
        "fetch_method": lambda client, entity_id: client.fetch_test(entity_id, include_raw_worksheet_data=True),
        "model": Test,
        "id_field": "id",
    },
}


def fetch_entity(client: QBenchClient, entity_type: str, entity_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a single entity by ID from QBench API."""
    config = ENTITY_CONFIG[entity_type]
    fetch_method = config["fetch_method"]

    try:
        if entity_type in ["customer", "batch"]:
            # For entities without direct fetch by ID, we need to list and find
            # This is a limitation - ideally QBench would have individual fetch endpoints
            LOGGER.warning(f"Entity type '{entity_type}' does not support direct fetch by ID. "
                         f"Fetching first page and searching for ID {entity_id}.")
            data = fetch_method(client, entity_id)
            items = data.get("data", [])
            for item in items:
                if str(item.get("id")) == str(entity_id):
                    return item
            LOGGER.error(f"Entity {entity_type} with ID {entity_id} not found in first page.")
            return None
        else:
            # Direct fetch for sample and test
            return fetch_method(client, entity_id)
    except Exception as exc:
        LOGGER.error(f"Failed to fetch {entity_type} {entity_id}: {exc}")
        return None


def transform_entity_data(entity_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Transform raw QBench data into database record format."""
    if entity_type == "customer":
        return {
            "id": data["id"],
            "name": data.get("customer_name") or data.get("name"),
            "date_created": parse_qbench_datetime(data.get("date_created")),
            "raw_payload": data,
        }
    elif entity_type == "order":
        return {
            "id": data["id"],
            "custom_formatted_id": data.get("custom_formatted_id"),
            "customer_account_id": data.get("customer_account_id"),
            "date_created": parse_qbench_datetime(data.get("date_created")),
            "date_completed": parse_qbench_datetime(data.get("date_completed")),
            "date_order_reported": parse_qbench_datetime(data.get("date_order_reported")),
            "date_received": parse_qbench_datetime(data.get("date_received")),
            "sample_count": safe_int(data.get("sample_count")),
            "test_count": safe_int(data.get("test_count")),
            "state": data.get("state"),
            "raw_payload": data,
        }
    elif entity_type == "batch":
        return {
            "id": data["id"],
            "assay_id": data.get("assay_id"),
            "display_name": data.get("display_name"),
            "date_created": parse_qbench_datetime(data.get("date_created")),
            "date_prepared": parse_qbench_datetime(data.get("date_prepared")),
            "last_updated": parse_qbench_datetime(data.get("last_updated")),
            "sample_ids": ensure_int_list(data.get("sample_ids")),
            "test_ids": ensure_int_list(data.get("test_ids")),
            "raw_payload": data,
        }
    elif entity_type == "sample":
        return {
            "id": data["id"],
            "sample_name": data.get("sample_name") or data.get("description"),
            "custom_formatted_id": data.get("custom_formatted_id"),
            "order_id": data.get("order_id"),
            "has_report": bool(data.get("has_report")),
            "batch_ids": ensure_int_list(data.get("batches")),
            "completed_date": parse_qbench_datetime(data.get("completed_date") or data.get("complete_date")),
            "date_created": parse_qbench_datetime(data.get("date_created")),
            "start_date": parse_qbench_datetime(data.get("start_date")),
            "matrix_type": data.get("matrix_type"),
            "state": data.get("state"),
            "test_count": safe_int(data.get("test_count")),
            "sample_weight": safe_decimal(data.get("sample_weight")),
            "raw_payload": data,
        }
    elif entity_type == "test":
        assay = data.get("assay") or {}
        return {
            "id": data["id"],
            "sample_id": data.get("sample_id"),
            "batch_ids": ensure_int_list(data.get("batches")),
            "date_created": parse_qbench_datetime(data.get("date_created")),
            "state": data.get("state"),
            "has_report": bool(data.get("has_report", False)),
            "report_completed_date": parse_qbench_datetime(data.get("report_completed_date")),
            "label_abbr": data.get("label_abbr") or assay.get("label_abbr"),
            "title": data.get("title") or assay.get("title"),
            "worksheet_raw": data.get("worksheet_data") or data.get("worksheet_json") or data.get("worksheet_raw"),
            "raw_payload": data,
        }
    else:
        raise ValueError(f"Unknown entity type: {entity_type}")


def save_entity(entity_type: str, record: Dict[str, Any], settings) -> bool:
    """Save the entity record to the database with upsert and update checkpoint if needed."""
    from downloader_qbench_data.storage import SyncCheckpoint

    model = ENTITY_CONFIG[entity_type]["model"]
    entity_id = record["id"]

    try:
        with session_scope(settings) as session:
            # Use upsert (INSERT ... ON CONFLICT DO UPDATE)
            from sqlalchemy.dialects.postgresql import insert
            from sqlalchemy import func

            insert_stmt = insert(model).values(record)

            # Build update statement based on entity type
            if entity_type == "customer":
                update_stmt = {
                    "name": insert_stmt.excluded.name,
                    "date_created": insert_stmt.excluded.date_created,
                    "raw_payload": insert_stmt.excluded.raw_payload,
                    "fetched_at": func.now(),
                }
            elif entity_type == "order":
                update_stmt = {
                    "custom_formatted_id": insert_stmt.excluded.custom_formatted_id,
                    "customer_account_id": insert_stmt.excluded.customer_account_id,
                    "date_created": insert_stmt.excluded.date_created,
                    "date_completed": insert_stmt.excluded.date_completed,
                    "date_order_reported": insert_stmt.excluded.date_order_reported,
                    "date_received": insert_stmt.excluded.date_received,
                    "sample_count": insert_stmt.excluded.sample_count,
                    "test_count": insert_stmt.excluded.test_count,
                    "state": insert_stmt.excluded.state,
                    "raw_payload": insert_stmt.excluded.raw_payload,
                    "fetched_at": func.now(),
                }
            elif entity_type == "batch":
                update_stmt = {
                    "assay_id": insert_stmt.excluded.assay_id,
                    "display_name": insert_stmt.excluded.display_name,
                    "date_created": insert_stmt.excluded.date_created,
                    "date_prepared": insert_stmt.excluded.date_prepared,
                    "last_updated": insert_stmt.excluded.last_updated,
                    "sample_ids": insert_stmt.excluded.sample_ids,
                    "test_ids": insert_stmt.excluded.test_ids,
                    "raw_payload": insert_stmt.excluded.raw_payload,
                    "fetched_at": func.now(),
                }
            elif entity_type == "sample":
                update_stmt = {
                    "sample_name": insert_stmt.excluded.sample_name,
                    "custom_formatted_id": insert_stmt.excluded.custom_formatted_id,
                    "order_id": insert_stmt.excluded.order_id,
                    "has_report": insert_stmt.excluded.has_report,
                    "batch_ids": insert_stmt.excluded.batch_ids,
                    "completed_date": insert_stmt.excluded.completed_date,
                    "date_created": insert_stmt.excluded.date_created,
                    "start_date": insert_stmt.excluded.start_date,
                    "matrix_type": insert_stmt.excluded.matrix_type,
                    "state": insert_stmt.excluded.state,
                    "test_count": insert_stmt.excluded.test_count,
                    "sample_weight": insert_stmt.excluded.sample_weight,
                    "raw_payload": insert_stmt.excluded.raw_payload,
                    "fetched_at": func.now(),
                }
            elif entity_type == "test":
                update_stmt = {
                    "sample_id": insert_stmt.excluded.sample_id,
                    "batch_ids": insert_stmt.excluded.batch_ids,
                    "date_created": insert_stmt.excluded.date_created,
                    "state": insert_stmt.excluded.state,
                    "has_report": insert_stmt.excluded.has_report,
                    "report_completed_date": insert_stmt.excluded.report_completed_date,
                    "label_abbr": insert_stmt.excluded.label_abbr,
                    "title": insert_stmt.excluded.title,
                    "worksheet_raw": insert_stmt.excluded.worksheet_raw,
                    "raw_payload": insert_stmt.excluded.raw_payload,
                    "fetched_at": func.now(),
                }

            session.execute(insert_stmt.on_conflict_do_update(index_elements=[model.id], set_=update_stmt))

            # Update checkpoint if this entity ID is higher than current last_id
            checkpoint = session.get(SyncCheckpoint, entity_type)
            if checkpoint and checkpoint.last_id is not None:
                if entity_id > checkpoint.last_id:
                    checkpoint.last_id = entity_id
                    checkpoint.last_synced_at = record.get("date_created") or record.get("fetched_at")
                    LOGGER.info(f"Updated checkpoint for {entity_type}: last_id={entity_id}")
            elif checkpoint and checkpoint.last_id is None:
                # Initialize last_id if not set
                checkpoint.last_id = entity_id
                checkpoint.last_synced_at = record.get("date_created") or record.get("fetched_at")
                LOGGER.info(f"Initialized checkpoint for {entity_type}: last_id={entity_id}")

            session.commit()
            LOGGER.info(f"Successfully saved {entity_type} {entity_id}")
            return True

    except Exception as exc:
        LOGGER.error(f"Failed to save {entity_type} {record.get('id', 'unknown')}: {exc}")
        return False


def check_foreign_keys(entity_type: str, record: Dict[str, Any], settings) -> bool:
    """Check if foreign key dependencies exist in the database."""
    if entity_type == "order":
        customer_id = record.get("customer_account_id")
        if customer_id:
            with session_scope(settings) as session:
                from sqlalchemy import select
                result = session.execute(select(Customer.id).where(Customer.id == customer_id))
                if not result.fetchone():
                    LOGGER.warning(f"Customer {customer_id} not found for order {record['id']}. "
                                 f"Order may not be usable without its customer.")
                    return False
    elif entity_type == "sample":
        order_id = record.get("order_id")
        if order_id:
            with session_scope(settings) as session:
                from sqlalchemy import select
                result = session.execute(select(Order.id).where(Order.id == order_id))
                if not result.fetchone():
                    LOGGER.warning(f"Order {order_id} not found for sample {record['id']}. "
                                 f"Sample will be saved but may cause issues.")
                    return False
    elif entity_type == "test":
        sample_id = record.get("sample_id")
        if sample_id:
            with session_scope(settings) as session:
                from sqlalchemy import select
                result = session.execute(select(Sample.id).where(Sample.id == sample_id))
                if not result.fetchone():
                    LOGGER.warning(f"Sample {sample_id} not found for test {record['id']}. "
                                 f"Test will be saved but may cause issues.")
                    return False
    return True


def main():
    parser = argparse.ArgumentParser(description="Fetch and save entities from QBench")
    parser.add_argument("entity_type", choices=ENTITY_CONFIG.keys(),
                       help="Type of entity to fetch")
    parser.add_argument("entity_ids", nargs="+", help="IDs of the entities to fetch (space-separated)")
    parser.add_argument("--skip-foreign-check", action="store_true",
                       help="Skip foreign key dependency checks")

    args = parser.parse_args()

    settings = get_settings()
    success_count = 0
    total_count = len(args.entity_ids)

    with QBenchClient(
        base_url=settings.qbench.base_url,
        client_id=settings.qbench.client_id,
        client_secret=settings.qbench.client_secret,
        token_url=settings.qbench.token_url,
    ) as client:
        for entity_id in args.entity_ids:
            LOGGER.info(f"Processing {args.entity_type} {entity_id} ({success_count + 1}/{total_count})")

            # Fetch the entity
            data = fetch_entity(client, args.entity_type, entity_id)
            if not data:
                LOGGER.error(f"Could not fetch {args.entity_type} {entity_id}")
                continue

            # Transform the data
            record = transform_entity_data(args.entity_type, data)

            # Check foreign keys if not skipped
            if not args.skip_foreign_check:
                if not check_foreign_keys(args.entity_type, record, settings):
                    LOGGER.warning(f"Foreign key check failed for {args.entity_type} {entity_id}. Skipping.")
                    continue

            # Save to database
            if save_entity(args.entity_type, record, settings):
                success_count += 1
                LOGGER.info(f"Successfully processed {args.entity_type} {entity_id}")
            else:
                LOGGER.error(f"Failed to save {args.entity_type} {entity_id}")

    LOGGER.info(f"Completed processing {success_count}/{total_count} entities")
    if success_count != total_count:
        sys.exit(1)


if __name__ == "__main__":
    main()
