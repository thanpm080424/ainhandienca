"""SQLite logger cho telemetry nhận diện cá và chất lượng nước.

Tác giả đồ án: Lê Quốc Trí (DH52201621) và Phạm Minh Thân (DH52201428).
Database mặc định ở data/history.db; có thể đổi bằng FISH_HISTORY_DB.
"""

from __future__ import annotations

import os
import math
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("FISH_HISTORY_DB", str(BASE_DIR / "data" / "history.db"))).expanduser()
ALERT_STATUSES = {"NORMAL", "TEMP_WARNING", "PH_WARNING", "HYBRID_ALERT"}


def _connect() -> sqlite3.Connection:
    """Mở connection ngắn hạn, an toàn giữa các request/thread Flask."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(DB_PATH), timeout=10.0)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA busy_timeout = 10000")
    return connection


def initialize_database() -> None:
    """Tạo bảng và chỉ mục nếu chưa tồn tại."""
    with _connect() as connection:
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS telemetry_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                device_id TEXT NOT NULL,
                species_key TEXT,
                species_name TEXT,
                confidence REAL,
                temp_measured REAL,
                ph_measured REAL,
                optimal_temp TEXT,
                optimal_ph TEXT,
                is_hybrid INTEGER NOT NULL DEFAULT 0 CHECK (is_hybrid IN (0, 1)),
                alert_status TEXT NOT NULL DEFAULT 'NORMAL'
                    CHECK (alert_status IN ('NORMAL', 'TEMP_WARNING', 'PH_WARNING', 'HYBRID_ALERT')),
                image_path TEXT
            )
            """
        )
        connection.execute("CREATE INDEX IF NOT EXISTS idx_telemetry_timestamp ON telemetry_logs(timestamp DESC)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_telemetry_device_time ON telemetry_logs(device_id, timestamp DESC)")


def _optional_float(value: Any, field_name: str) -> float | None:
    if value is None or value == "":
        return None
    try:
        number = float(value)
        if not math.isfinite(number):
            raise ValueError
        return number
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} phải là số thực hoặc để trống.") from exc


def log_telemetry(
    *,
    device_id: str = "unknown-device",
    species_key: str | None = None,
    species_name: str | None = None,
    confidence: float | None = None,
    temp_measured: float | None = None,
    ph_measured: float | None = None,
    optimal_temp: str | None = None,
    optimal_ph: str | None = None,
    is_hybrid: bool | int = False,
    alert_status: str = "NORMAL",
    image_path: str | None = None,
    timestamp: str | None = None,
) -> int:
    """Ghi một bản ghi và trả về khóa chính SQLite.

    Nếu không truyền timestamp, SQLite gán CURRENT_TIMESTAMP theo UTC.
    """
    initialize_database()
    status = str(alert_status or "NORMAL").upper()
    if status not in ALERT_STATUSES:
        raise ValueError(f"alert_status không hợp lệ: {status}")
    confidence_value = _optional_float(confidence, "confidence")
    temperature_value = _optional_float(temp_measured, "temp_measured")
    ph_value = _optional_float(ph_measured, "ph_measured")
    if isinstance(is_hybrid, str):
        hybrid_value = 1 if is_hybrid.strip().lower() in {"1", "true", "yes", "on"} else 0
    else:
        hybrid_value = 1 if bool(is_hybrid) else 0

    columns = ["device_id", "species_key", "species_name", "confidence", "temp_measured", "ph_measured",
               "optimal_temp", "optimal_ph", "is_hybrid", "alert_status", "image_path"]
    values: list[Any] = [str(device_id or "unknown-device"), species_key, species_name, confidence_value,
                         temperature_value, ph_value, optimal_temp, optimal_ph, hybrid_value, status, image_path]
    if timestamp is not None:
        # Hỗ trợ nhập dữ liệu lịch sử; chuẩn hóa mọi timestamp có timezone sang UTC.
        try:
            parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            if parsed.tzinfo is not None:
                parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
            timestamp = parsed.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError as exc:
            raise ValueError("timestamp cần ở dạng ISO 8601.") from exc
        columns.insert(0, "timestamp")
        values.insert(0, timestamp)

    placeholders = ", ".join("?" for _ in columns)
    sql = f"INSERT INTO telemetry_logs ({', '.join(columns)}) VALUES ({placeholders})"
    with _connect() as connection:
        cursor = connection.execute(sql, values)
        return int(cursor.lastrowid)


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    item["is_hybrid"] = bool(item["is_hybrid"])
    return item


def get_recent_logs(limit: int = 50, device_id: str | None = None) -> list[dict[str, Any]]:
    """Lấy log mới nhất; limit được giới hạn trong 1..1000."""
    initialize_database()
    try:
        safe_limit = max(1, min(1000, int(limit)))
    except (TypeError, ValueError) as exc:
        raise ValueError("limit phải là số nguyên.") from exc
    with _connect() as connection:
        if device_id:
            rows = connection.execute(
                "SELECT * FROM telemetry_logs WHERE device_id = ? ORDER BY timestamp DESC, id DESC LIMIT ?",
                (device_id, safe_limit),
            ).fetchall()
        else:
            rows = connection.execute(
                "SELECT * FROM telemetry_logs ORDER BY timestamp DESC, id DESC LIMIT ?", (safe_limit,)
            ).fetchall()
    return [_row_to_dict(row) for row in rows]


def get_statistics(days: int = 7) -> dict[str, Any]:
    """Tổng hợp lượt nhận diện, cảnh báo và trung bình cảm biến trong N ngày gần nhất."""
    initialize_database()
    try:
        safe_days = max(1, min(3660, int(days)))
    except (TypeError, ValueError) as exc:
        raise ValueError("days phải là số nguyên dương.") from exc
    since_modifier = f"-{safe_days} days"
    with _connect() as connection:
        totals_row = connection.execute(
            """SELECT COUNT(*) AS detections,
                      SUM(CASE WHEN alert_status != 'NORMAL' THEN 1 ELSE 0 END) AS alerts,
                      SUM(is_hybrid) AS hybrid_detections,
                      AVG(temp_measured) AS avg_temperature,
                      AVG(ph_measured) AS avg_ph
               FROM telemetry_logs WHERE timestamp >= datetime('now', ?)""",
            (since_modifier,),
        ).fetchone()
        species_rows = connection.execute(
            """SELECT COALESCE(species_key, 'unknown') AS species_key,
                      COALESCE(species_name, species_key, 'Không rõ') AS species_name,
                      COUNT(*) AS detections
               FROM telemetry_logs WHERE timestamp >= datetime('now', ?)
               GROUP BY species_key, species_name ORDER BY detections DESC, species_name""",
            (since_modifier,),
        ).fetchall()
        daily_rows = connection.execute(
            """SELECT date(timestamp) AS day, COUNT(*) AS detections,
                      AVG(temp_measured) AS avg_temperature, AVG(ph_measured) AS avg_ph,
                      SUM(CASE WHEN alert_status != 'NORMAL' THEN 1 ELSE 0 END) AS alerts
               FROM telemetry_logs WHERE timestamp >= datetime('now', ?)
               GROUP BY date(timestamp) ORDER BY day""",
            (since_modifier,),
        ).fetchall()
        alert_count_rows = connection.execute(
            """SELECT alert_status, COUNT(*) AS count FROM telemetry_logs
               WHERE timestamp >= datetime('now', ?) AND alert_status != 'NORMAL'
               GROUP BY alert_status ORDER BY alert_status""",
            (since_modifier,),
        ).fetchall()
        alert_rows = connection.execute(
            """SELECT * FROM telemetry_logs WHERE timestamp >= datetime('now', ?)
               AND alert_status != 'NORMAL' ORDER BY timestamp DESC, id DESC LIMIT 500""",
            (since_modifier,),
        ).fetchall()

    totals = dict(totals_row) if totals_row else {}
    for key in ("detections", "alerts", "hybrid_detections"):
        totals[key] = int(totals.get(key) or 0)
    for key in ("avg_temperature", "avg_ph"):
        value = totals.get(key)
        totals[key] = round(float(value), 2) if value is not None else None
    return {
        "days": safe_days,
        "totals": totals,
        "species_counts": [dict(row) for row in species_rows],
        "daily": [dict(row) for row in daily_rows],
        "alert_counts": {row["alert_status"]: int(row["count"]) for row in alert_count_rows},
        "alerts": [_row_to_dict(row) for row in alert_rows],
    }

