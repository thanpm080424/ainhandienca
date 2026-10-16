"""
KỊCH BẢN HUẤN LUYỆN MÔ HÌNH YOLOV8 NHẬN DIỆN 20 LOÀI CÁ CẢNH IOT
Đồ án tốt nghiệp: Lê Quốc Trí (DH52201621) & Phạm Minh Thân (DH52201428)

Kiến trúc: YOLOv8 Classification (yolov8n-cls / yolov8s-cls)
Dữ liệu: dataset_yolo (4,948 train | 615 val | 628 test)
Xuất mô hình: PyTorch (.pt) và ONNX (.onnx) để nhúng vào Gateway IoT / Web App
"""

import os
import sys
import argparse
import json
import torch
from ultralytics import YOLO

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(BASE_DIR, 'dataset_yolo')
OUTPUT_DIR = os.path.join(BASE_DIR, 'runs')
WEIGHTS_DIR = os.path.join(BASE_DIR, 'weights')


def train_fish_model(model_size='n', epochs=20, batch_size=16, imgsz=224):
    device = '0' if torch.cuda.is_available() else 'cpu'
    model_name = f'yolov8{model_size}-cls.pt'

    print("=" * 70)
    print("🎯 KHỞI ĐỘNG HUẤN LUYỆN YOLOV8 CLASSIFICATION (20 LOÀI CÁ CẢNH)")
    print("=" * 70)
    print(f"📦 Mô hình gốc:     {model_name}")
    print(f"⚙️ Thiết bị:        {device.upper()} ({torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU Processor'})")
    print(f"📊 Số Epochs:       {epochs}")
    print(f"📏 Kích thước ảnh:  {imgsz}x{imgsz}")
    print(f"📦 Batch size:      {batch_size}")
    print(f"📁 Thư mục dữ liệu: {DATASET_DIR}")
    print("=" * 70)

    if not os.path.exists(DATASET_DIR):
        print(f"❌ Lỗi: Không tìm thấy thư mục '{DATASET_DIR}'! Vui lòng chạy 'prepare_dataset_yolo.py' trước.")
        return

    # Khởi tạo mô hình YOLOv8 Classification
    model = YOLO(model_name)

    # Tiến hành Huấn luyện
    results = model.train(
        data=DATASET_DIR,
        epochs=epochs,
        batch=batch_size,
        imgsz=imgsz,
        device=device,
        project=os.path.join(OUTPUT_DIR, 'classify'),
        name='fish_yolov8_model',
        exist_ok=True,
        workers=2,
        verbose=True
    )

    print("\n" + "=" * 70)
    print("🎉 HOÀN THÀNH HUẤN LUYỆN YOLOV8!")
    print("=" * 70)

    # Đánh giá trên tập Validation
    print("📊 Đang đánh giá độ chính xác (Validation)...")
    val_results = model.val()
    print(f"✅ Top-1 Accuracy: {val_results.top1:.4f} ({val_results.top1*100:.2f}%)")
    print(f"✅ Top-5 Accuracy: {val_results.top5:.4f} ({val_results.top5*100:.2f}%)")

    # Lưu trọng số mô hình tốt nhất vào thư mục weights/
    os.makedirs(WEIGHTS_DIR, exist_ok=True)
    best_pt_path = os.path.join(OUTPUT_DIR, 'classify', 'fish_yolov8_model', 'weights', 'best.pt')
    target_pt = os.path.join(WEIGHTS_DIR, 'best_fish_yolov8.pt')

    if os.path.exists(best_pt_path):
        import shutil
        shutil.copy2(best_pt_path, target_pt)
        print(f"💾 Trọng số tốt nhất đã lưu: {target_pt}")

    # Xuất sang định dạng ONNX cho thiết bị IoT
    try:
        print("⚡ Đang xuất mô hình sang ONNX cho thiết bị IoT (Raspberry Pi/Jetson/ESP32 Gateway)...")
        onnx_file = model.export(format='onnx')
        target_onnx = os.path.join(WEIGHTS_DIR, 'best_fish_yolov8.onnx')
        if os.path.exists(onnx_file):
            shutil.copy2(onnx_file, target_onnx)
            print(f"💾 File ONNX IoT đã lưu: {target_onnx}")
    except Exception as e:
        print(f"⚠️ Chưa xuất ONNX được: {e}")

    print("\n✨ Bạn có thể kiểm tra thử bằng lệnh:")
    print("   python predict_fish.py path/to/image.jpg")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Train YOLOv8 Fish Classifier")
    parser.add_argument('--size', type=str, default='n', choices=['n', 's', 'm'], help="Model size: n (nano), s (small), m (medium)")
    parser.add_argument('--epochs', type=int, default=15, help="Number of training epochs")
    parser.add_argument('--batch', type=int, default=16, help="Batch size")
    parser.add_argument('--imgsz', type=int, default=224, help="Image size")
    args = parser.parse_args()

    train_fish_model(model_size=args.size, epochs=args.epochs, batch_size=args.batch, imgsz=args.imgsz)
