#!/usr/bin/env python3
"""Client Raspberry Pi: chụp ảnh, đọc DS18B20, gọi API Flask và in đối chiếu.

Đồ án: Lê Quốc Trí (DH52201621) và Phạm Minh Thân (DH52201428).
Route hiện tại xử lý field `file`; field cảm biến được gửi kèm để tương thích
client, nhưng Flask chưa lưu/đọc các giá trị đó. Việc so ngưỡng được làm cục bộ.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import requests

DEFAULT_SERVER = os.environ.get("FISH_SERVER_URL", "http://192.168.1.100:5000")
DEFAULT_DEVICE_ID = os.environ.get("FISH_DEVICE_ID", "raspberry-pi-aquarium-01")
W1_ROOT = Path("/sys/bus/w1/devices")


def read_ds18b20(sensor_id: str | None = None, retries: int = 3) -> float:
    """Đọc Celsius từ DS18B20 qua w1_slave, kiểm tra CRC và trả lỗi rõ ràng."""
    if not W1_ROOT.exists():
        raise FileNotFoundError("Không thấy /sys/bus/w1/devices; bật 1-Wire trong cấu hình Raspberry Pi OS.")
    if sensor_id:
        candidates = [W1_ROOT / sensor_id / "w1_slave"]
    else:
        candidates = sorted(W1_ROOT.glob("28-*/w1_slave"))
    candidates = [path for path in candidates if path.is_file()]
    if not candidates:
        raise FileNotFoundError("Không tìm thấy DS18B20 (ID 28-*) dưới /sys/bus/w1/devices.")

    last_error = "không rõ"
    for path in candidates:
        for _ in range(max(1, retries)):
            try:
                lines = path.read_text(encoding="ascii").strip().splitlines()
                if len(lines) < 2 or not lines[0].rstrip().endswith("YES"):
                    last_error = f"CRC chưa hợp lệ: {path}"
                    time.sleep(0.2)
                    continue
                marker = lines[1].find("t=")
                if marker < 0:
                    last_error = f"Không có trường nhiệt độ t=: {path}"
                    continue
                value = int(lines[1][marker + 2:]) / 1000.0
                if not -55.0 <= value <= 125.0:
                    last_error = f"Số đo ngoài dải DS18B20: {value}°C"
                    continue
                return value
            except (OSError, ValueError) as exc:
                last_error = str(exc)
                time.sleep(0.2)
    raise RuntimeError(f"Không đọc được DS18B20: {last_error}")


def capture_image(output: Path, camera_index: int = 0) -> Path:
    """Chụp một JPEG; ưu tiên Picamera2, fallback sang OpenCV USB/camera V4L2."""
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        from picamera2 import Picamera2

        camera = Picamera2()
        camera.configure(camera.create_still_configuration(main={"size": (1280, 960)}))
        camera.start()
        time.sleep(1.0)
        camera.capture_file(str(output))
        camera.stop()
        camera.close()
        return output
    except ImportError:
        pass
    except Exception as exc:
        # Thử camera OpenCV nếu Picamera2 được cài nhưng camera CSI không sẵn sàng.
        print(f"Picamera2 không chụp được ({exc}); thử OpenCV.", file=sys.stderr)

    try:
        import cv2
    except ImportError as exc:
        raise RuntimeError("Cần Picamera2 (camera CSI) hoặc OpenCV (USB/V4L2).") from exc
    camera = cv2.VideoCapture(camera_index, cv2.CAP_V4L2)
    try:
        if not camera.isOpened():
            raise RuntimeError(f"Không mở được camera OpenCV index {camera_index}.")
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 960)
        for _ in range(5):
            ok, frame = camera.read()
        if not ok or frame is None:
            raise RuntimeError("Camera không trả về khung hình.")
        if not cv2.imwrite(str(output), frame, [int(cv2.IMWRITE_JPEG_QUALITY), 90]):
            raise RuntimeError(f"Không ghi được ảnh: {output}")
    finally:
        camera.release()
    return output


def _number(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def compare_range(value: float | None, limits: Any, unit: str) -> str:
    """Diễn giải một số đo theo range {min,max} do endpoint trả về."""
    if value is None:
        return "Chưa có số đo"
    low = _number(limits.get("min")) if isinstance(limits, dict) else None
    high = _number(limits.get("max")) if isinstance(limits, dict) else None
    if low is None or high is None:
        return f"{value:.2f} {unit} (API không trả dải số để đối chiếu)"
    if value < low:
        return f"{value:.2f} {unit} — THẤP hơn dải {low:g}–{high:g} {unit}"
    if value > high:
        return f"{value:.2f} {unit} — CAO hơn dải {low:g}–{high:g} {unit}"
    return f"{value:.2f} {unit} — trong dải {low:g}–{high:g} {unit}"


def print_report(data: dict[str, Any], temp_actual: float | None, ph_actual: float | None) -> None:
    """In bảng đọc được trong terminal, chịu được field thiếu/null."""
    detection = data.get("detection") or {}
    environment = data.get("aquatic_environment") or {}
    thresholds = data.get("iot_sensor_thresholds") or {}
    hybrid = data.get("hybrid_analysis") or {}
    print("\n" + "=" * 72)
    print("BÁO CÁO NHẬN DIỆN CÁ & ĐỐI CHIẾU MÔI TRƯỜNG")
    print("=" * 72)
    print(f"Loài nhận diện : {detection.get('species_name', 'Không rõ')}")
    print(f"Độ tin cậy     : {detection.get('confidence', 'N/A')}% ({detection.get('confidence_level', 'N/A')})")
    print(f"Nhiệt độ tối ưu: {environment.get('optimal_temperature', 'N/A')}")
    print(f"pH tối ưu      : {environment.get('optimal_ph', 'N/A')}")
    print(f"Số đo DS18B20  : {compare_range(temp_actual, environment.get('temp_range'), '°C')}")
    print(f"Cảnh báo nhiệt : {thresholds.get('temp_alert', 'N/A')}")
    print(f"Số đo pH       : {compare_range(ph_actual, environment.get('ph_range'), 'pH')}")
    print(f"Cảnh báo pH    : {thresholds.get('ph_alert', 'N/A')}")
    print(f"Cảnh báo lai tạp: {'CÓ' if hybrid.get('is_hybrid_alert') else 'Không/không có dữ liệu'}")
    print(f"Môi trường     : {environment.get('water_type', 'N/A')} | tầng {environment.get('water_layer', 'N/A')}")
    print("=" * 72)


def send_capture(server_url: str, image_path: Path, device_id: str,
                 temp_actual: float | None, ph_actual: float | None, timeout: float) -> dict[str, Any]:
    """Gửi multipart ảnh với key file và các số đo cảm biến kèm theo."""
    endpoint = server_url.rstrip("/") + "/api/iot/predict"
    fields: dict[str, str] = {"device_id": device_id}
    if temp_actual is not None:
        fields["temperature"] = f"{temp_actual:.3f}"
    if ph_actual is not None:
        fields["ph"] = f"{ph_actual:.3f}"
    try:
        with image_path.open("rb") as image_file:
            response = requests.post(endpoint, data=fields,
                                     files={"file": (image_path.name, image_file, "image/jpeg")},
                                     timeout=timeout)
    except requests.RequestException as exc:
        raise RuntimeError(f"Không kết nối được API {endpoint}: {exc}") from exc
    try:
        payload = response.json()
    except requests.JSONDecodeError as exc:
        excerpt = response.text[:500]
        raise RuntimeError(f"API trả về không phải JSON (HTTP {response.status_code}): {excerpt}") from exc
    if not response.ok or not payload.get("success"):
        raise RuntimeError(f"API HTTP {response.status_code}: {payload.get('error', json.dumps(payload, ensure_ascii=False))}")
    return payload


def run_once(args: argparse.Namespace) -> None:
    temp_actual = read_ds18b20(args.sensor_id) if not args.skip_temperature else None
    ph_actual = args.ph_actual
    if ph_actual is None and os.environ.get("FISH_PH_ACTUAL"):
        ph_actual = float(os.environ["FISH_PH_ACTUAL"])
    image_path = Path(args.output).expanduser().resolve()
    capture_image(image_path, args.camera_index)
    result = send_capture(args.server, image_path, args.device_id, temp_actual, ph_actual, args.timeout)
    print_report(result, temp_actual, ph_actual)
    if args.keep_image:
        print(f"Ảnh đã lưu tại: {image_path}")
    else:
        image_path.unlink(missing_ok=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Chụp ảnh cá, đọc DS18B20 và gửi lên Flask IoT API.")
    parser.add_argument("--server", default=DEFAULT_SERVER, help="Địa chỉ gốc Flask, ví dụ http://192.168.1.20:5000")
    parser.add_argument("--device-id", default=DEFAULT_DEVICE_ID)
    parser.add_argument("--sensor-id", default=None, help="ID DS18B20 như 28-xxxxxxxxxxxx; mặc định tự chọn cảm biến đầu tiên.")
    parser.add_argument("--ph-actual", type=float, default=None, help="Số đo pH đã hiệu chuẩn; có thể đặt biến FISH_PH_ACTUAL.")
    parser.add_argument("--skip-temperature", action="store_true", help="Chụp/gửi ảnh ngay cả khi không nối DS18B20.")
    parser.add_argument("--camera-index", type=int, default=0, help="Index camera OpenCV khi dùng fallback.")
    parser.add_argument("--output", default="/tmp/fish_iot_capture.jpg")
    parser.add_argument("--keep-image", action="store_true", help="Giữ file ảnh chụp sau khi gửi.")
    parser.add_argument("--timeout", type=float, default=45.0)
    parser.add_argument("--loop", action="store_true", help="Chạy lặp theo chu kỳ --interval giây.")
    parser.add_argument("--interval", type=float, default=60.0)
    return parser


if __name__ == "__main__":
    cli = build_parser().parse_args()
    try:
        if cli.loop:
            while True:
                try:
                    run_once(cli)
                except (RuntimeError, OSError, ValueError) as exc:
                    print(f"Lỗi lần lấy mẫu: {exc}", file=sys.stderr)
                time.sleep(max(1.0, cli.interval))
        else:
            run_once(cli)
    except (RuntimeError, OSError, ValueError) as exc:
        print(f"Lỗi: {exc}", file=sys.stderr)
        raise SystemExit(1)
