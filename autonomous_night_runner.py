"""
AUTONOMOUS NIGHT RUNNER - AINHANDIENCA
Đồ án tốt nghiệp: Lê Quốc Trí (DH52201621) & Phạm Minh Thân (DH52201428)

Kịch bản tự động chạy liên tục từ sáng đến tối:
1. Quét toàn bộ 20 lớp cá trong dataset_ca.
2. Tự động thu thập và lọc thông minh 5 tầng (ảnh cá trong bể kính, loại bỏ người/tay/thú, YOLO >= 60%).
3. Bổ sung tuần tự cho đến khi TẤT CẢ 20 LỚP đều đạt mốc 500 ảnh/loài (= 10,000 ảnh chuẩn hóa).
4. Tự động kích hoạt huấn luyện và đánh giá mô hình khi hoàn tất.
5. Ghi nhật ký tiến trình thời gian thực vào autonomous_collection.log.
"""

import os
import sys
import time
import signal
from pathlib import Path
from datetime import datetime

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)

BASE_DIR = Path(__file__).resolve().parent
DATASET_DIR = BASE_DIR / "dataset_ca"
LOG_FILE = BASE_DIR / "autonomous_collection.log"
TARGET_PER_CLASS = 500
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

running = True

def handle_sig(sig, frame):
    global running
    print(f"\n[DAEMON] Nhận tín hiệu dừng ({sig}). Đang đóng tiến trình an toàn...")
    running = False

signal.signal(signal.SIGINT, handle_sig)
signal.signal(signal.SIGTERM, handle_sig)


def log(msg: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{timestamp}] {msg}"
    print(formatted, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(formatted + "\n")
    except Exception:
        pass


def get_dataset_stats() -> dict[str, int]:
    from codex_fish_collector import count_species_images, SPECIES_QUERIES
    counts = count_species_images(DATASET_DIR)
    return counts


def run_collection_cycle(collector, batch_limit: int = 20) -> tuple[int, bool]:
    """Chạy 1 chu kỳ bổ sung cho các loài thiếu nhiều nhất."""
    from codex_fish_collector import PRIORITY_SPECIES, SPECIES_QUERIES

    counts = get_dataset_stats()
    priority_order = {sp: i for i, sp in enumerate(PRIORITY_SPECIES)}

    deficient = [(sp, TARGET_PER_CLASS - cnt) for sp, cnt in counts.items() if cnt < TARGET_PER_CLASS]
    if not deficient:
        return 0, True  # Đã hoàn thành 100%

    # Sắp xếp theo số ảnh thiếu giảm dần
    deficient.sort(key=lambda x: (-x[1], priority_order.get(x[0], len(priority_order))))

    log(f"--- BẮT ĐẦU VÒNG BỔ SUNG MỚI (Còn {len(deficient)}/20 loài chưa đạt 500 ảnh) ---")
    for sp, def_count in deficient[:5]:
        log(f"  • {sp:18s}: hiện có {counts[sp]}/500 (còn thiếu {def_count})")

    sources = {"ddg", "commons", "inat"}
    total_added_this_cycle = 0

    for sp, def_count in deficient:
        if not running:
            break

        to_collect = min(def_count, batch_limit)
        log(f"🚀 [{sp}] Đang thu thập và lọc {to_collect} ảnh cá bể kính...")

        try:
            added = collector.collect(sp, to_collect, sources)
            total_added_this_cycle += added
            new_count = counts[sp] + added
            log(f"✅ [{sp}] Đã thêm thành công {added} ảnh. Tổng hiện tại: {new_count}/{TARGET_PER_CLASS}")
        except Exception as exc:
            log(f"⚠️ [{sp}] Lỗi trong lượt thu thập: {exc}")

        # Nghỉ nhẹ 3 giây giữa các loài để giữ vệ sinh mạng và tránh rate-limit
        for _ in range(3):
            if not running:
                break
            time.sleep(1)

    return total_added_this_cycle, False


def main():
    log("================================================================================")
    log("KHỞI ĐỘNG HỆ THỐNG TỰ ĐỘNG HÓA TỚI TỐI NAY (AUTONOMOUS NIGHT RUNNER)")
    log(f"Mục tiêu: Đưa toàn bộ 20 lớp cá đạt chuẩn {TARGET_PER_CLASS} ảnh/loài trong bể kính.")
    log(f"Thư mục dữ liệu: {DATASET_DIR}")
    log("================================================================================")

    from codex_fish_collector import Collector
    collector = Collector(
        dataset_dir=DATASET_DIR,
        workers=8,
        allow_unlicensed=True,
        verify_yolo=True,
        confidence_min=60.0
    )

    try:
        collector.load_yolo()
        log("✅ Đã nạp thành công bộ lọc YOLOv8 Classifier & YOLOv8n Object Detector.")
    except Exception as exc:
        log(f"❌ Không thể nạp mô hình: {exc}")
        return 1

    cycle = 1
    consecutive_zero = 0

    while running:
        log(f"\n>>> [CHU KỲ #{cycle}] Bắt đầu quét và nạp ảnh cá bể kính...")
        added, completed = run_collection_cycle(collector, batch_limit=25)

        counts = get_dataset_stats()
        total_images = sum(counts.values())
        completed_classes = sum(1 for c in counts.values() if c >= TARGET_PER_CLASS)

        log(f">>> [KẾT QUẢ CHU KỲ #{cycle}] Đã thêm: +{added} ảnh. Tổng dataset: {total_images} ảnh.")
        log(f">>> Tiến độ hoàn thành các loài: {completed_classes}/20 loài đã đạt {TARGET_PER_CLASS} ảnh.")

        if completed:
            log("🎉🎉🎉 TOÀN BỘ 20 LOÀI CÁ ĐÃ ĐẠT 500 ẢNH/LOÀI (TỔNG CỘNG 10,000 ẢNH CHUẨN HOÁ)!")
            break

        if added == 0:
            consecutive_zero += 1
            if consecutive_zero >= 5:
                log("ℹ️ Đã thử 5 chu kỳ liên tiếp không còn ảnh mới phù hợp ngưỡng lọc. Tạm dừng để kích hoạt bước huấn luyện.")
                break
            log(f"Tạm nghỉ 15 giây trước chu kỳ tiếp theo (lần {consecutive_zero}/5)...")
            time.sleep(15)
        else:
            consecutive_zero = 0
            log("Nghỉ ngắn 5 giây trước chu kỳ kế tiếp...")
            time.sleep(5)

        cycle += 1

    # Bước cuối cùng: Huấn luyện và cập nhật mô hình
    if running:
        log("\n================================================================================")
        log("BẮT ĐẦU HUẤN LUYỆN VÀ ĐÁNH GIÁ MÔ HÌNH YOLOV8 TRÊN TẬP DỮ LIỆU ĐẦY ĐỦ")
        log("================================================================================")
        try:
            import subprocess
            cmd = [sys.executable, str(BASE_DIR / "train_fish_classifier.py"), "--epochs", "15", "--batch", "16", "--device", "cpu"]
            log(f"Thực thi lệnh: {' '.join(cmd)}")
            subprocess.run(cmd, check=True)
            log("✅ HUẤN LUYỆN HOÀN TẤT! File trọng số mới đã được lưu vào weights/best_fish_yolov8.pt")
        except Exception as exc:
            log(f"⚠️ Quá trình huấn luyện gặp sự cố: {exc}")

    log("🏁 Tiến trình tự động hóa đã kết thúc chuỗi nhiệm vụ hôm nay.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
