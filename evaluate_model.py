"""
ĐÁNH GIÁ MÔ HÌNH YOLOV8 NHẬN DIỆN 20 LOÀI CÁ CẢNH TRÊN TẬP TEST (ĐỘC LẬP)
Đồ án tốt nghiệp: Lê Quốc Trí (DH52201621) & Phạm Minh Thân (DH52201428)

Kịch bản:
- Nạp mô hình YOLOv8n-cls đã huấn luyện (weights/best_fish_yolov8.pt)
- Đánh giá trên tập dataset_yolo/test (628 ảnh hoàn toàn mới chưa qua huấn luyện)
- Tính toán Top-1 Accuracy, Top-5 Accuracy, Ma trận nhầm lẫn (Confusion Matrix), Độ trễ suy luận (ms/ảnh)
- Xuất báo cáo đánh giá phục vụ thuyết minh đồ án tốt nghiệp
"""

import os
import sys
import time
import json
import torch
from ultralytics import YOLO

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEST_DIR = os.path.join(BASE_DIR, 'dataset_yolo', 'test')
MODEL_PATH = os.path.join(BASE_DIR, 'weights', 'best_fish_yolov8.pt')
REPORT_PATH = os.path.join(BASE_DIR, 'evaluation_report.json')


def evaluate_on_test():
    print("=" * 70)
    print("🐟 ĐÁNH GIÁ MÔ HÌNH YOLOV8 CLASSIFICATION TRÊN TẬP TEST ĐỘC LẬP")
    print("   Sinh viên thực hiện: Lê Quốc Trí (DH52201621) & Phạm Minh Thân (DH52201428)")
    print("=" * 70)

    if not os.path.exists(MODEL_PATH):
        print(f"❌ Không tìm thấy file trọng số: {MODEL_PATH}")
        return

    if not os.path.exists(TEST_DIR):
        print(f"❌ Không tìm thấy thư mục test: {TEST_DIR}")
        return

    print(f"📦 Mô hình: {MODEL_PATH}")
    print(f"📁 Dữ liệu test: {TEST_DIR}")

    model = YOLO(MODEL_PATH)

    # Đánh giá bằng ultralytics val() trên split='test'
    print("\n⏳ Đang tiến hành kiểm thử trên tập test...")
    start_time = time.time()
    metrics = model.val(data=os.path.join(BASE_DIR, 'dataset_yolo'), split='test', imgsz=224, verbose=True)
    elapsed = time.time() - start_time

    top1 = metrics.top1
    top5 = metrics.top5

    print("\n" + "=" * 70)
    print("📊 KẾT QUẢ ĐÁNH GIÁ TRÊN TẬP TEST (628 ẢNH)")
    print("=" * 70)
    print(f"🎯 Top-1 Accuracy: {top1:.4f} ({top1 * 100:.2f}%)")
    print(f"🎯 Top-5 Accuracy: {top5:.4f} ({top5 * 100:.2f}%)")
    print(f"⏱️ Tổng thời gian kiểm thử: {elapsed:.2f}s")
    if metrics.speed:
        infer_speed = metrics.speed.get('inference', 0.0)
        print(f"⚡ Tốc độ suy luận (Inference latency): {infer_speed:.2f} ms/ảnh")
        fps = 1000.0 / infer_speed if infer_speed > 0 else 0
        print(f"🚀 Tốc độ xử lý tương đương: ~{fps:.1f} FPS (Rất phù hợp cho IoT Edge Gateway)")

    report_data = {
        'project': 'He thong nhan dien 20 loai ca canh IoT & Web',
        'authors': ['Le Quoc Tri (DH52201621)', 'Pham Minh Than (DH52201428)'],
        'model': 'YOLOv8n-cls',
        'top1_accuracy': round(top1 * 100, 2),
        'top5_accuracy': round(top5 * 100, 2),
        'speed_ms_per_image': metrics.speed.get('inference', 0.0) if metrics.speed else 0.0,
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
    }

    with open(REPORT_PATH, 'w', encoding='utf-8') as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)

    print(f"\n💾 Đã lưu báo cáo kết quả: {REPORT_PATH}")
    print("=" * 70)


if __name__ == '__main__':
    evaluate_on_test()
