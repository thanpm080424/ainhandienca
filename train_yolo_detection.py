"""
KỊCH BẢN HUẤN LUYỆN YOLOV8 OBJECT DETECTION CHO 20 LOÀI CÁ CẢNH TRONG BỂ KÍNH
Đồ án tốt nghiệp: Lê Quốc Trí (DH52201621) & Phạm Minh Thân (DH52201428)

Kiến trúc: YOLOv8 Object Detection (yolov8n.pt / yolov8s.pt)
Dữ liệu: dataset_yolo_detection (800 train | 100 val | 100 test - 2,497 Bounding Boxes)
Xuất mô hình: PyTorch (.pt) và ONNX (.onnx) phục vụ Gateway IoT & Stream Camera
"""

import os
import sys
import argparse
from pathlib import Path
import torch
from ultralytics import YOLO

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = Path(__file__).resolve().parent
DATA_YAML = BASE_DIR / "dataset_yolo_detection" / "data.yaml"
OUTPUT_DIR = BASE_DIR / "runs" / "detect"
WEIGHTS_DIR = BASE_DIR / "weights"


def train_yolo_detection(model_size='n', epochs=30, batch_size=-1, imgsz=640, device_arg=None):
    if device_arg is not None:
        device = device_arg
    else:
        device = '0' if torch.cuda.is_available() else 'cpu'

    if device == 'cpu':
        try:
            torch.set_num_threads(8)
        except Exception:
            pass

    base_model = f"yolov8{model_size}.pt"

    print("=" * 75)
    print("🎯 KHỞI ĐỘNG HUẤN LUYỆN YOLOV8 OBJECT DETECTION (20 LOÀI CÁ CẢNH)")
    print("   Sinh viên thực hiện: Lê Quốc Trí (DH52201621) & Phạm Minh Thân (DH52201428)")
    print("=" * 75)
    print(f"📦 Pretrained Model: {base_model}")
    print(f"⚙️ Thiết bị:         {device.upper()} ({torch.cuda.get_device_name(0) if torch.cuda.is_available() and device != 'cpu' else 'Multi-Core CPU'})")
    print(f"📊 Số Epochs:        {epochs}")
    print(f"📏 Image Size:       {imgsz}x{imgsz}")
    print(f"📦 Batch Size:       {'AutoBatch (-1) - Tự đo VRAM GPU tránh OOM' if batch_size == -1 else batch_size}")
    print(f"📁 Cấu hình data:    {DATA_YAML}")
    print("=" * 75)

    if not DATA_YAML.exists():
        print(f"❌ Không tìm thấy file cấu hình {DATA_YAML}!")
        return

    # Khởi tạo mô hình Detection
    model = YOLO(base_model)

    # Tiến hành Huấn luyện với AutoBatch tối ưu cho RTX 3050 Laptop 4GB
    results = model.train(
        data=str(DATA_YAML),
        epochs=epochs,
        batch=batch_size,
        imgsz=imgsz,
        device=device,
        project=str(OUTPUT_DIR),
        name="fish_detection_yolov8",
        exist_ok=True,
        workers=2 if device != 'cpu' else 4,
        verbose=True
    )

    print("\n" + "=" * 75)
    print("🎉 HUẤN LUYỆN HOÀN TẤT! ĐANG ĐÁNH GIÁ TRÊN TẬP VALIDATION & TEST...")
    print("=" * 75)

    # Đánh giá trên Validation
    val_results = model.val(data=str(DATA_YAML), split='val')
    print(f"✅ Val mAP50:    {val_results.box.map50:.4f} ({val_results.box.map50 * 100:.2f}%)")
    print(f"✅ Val mAP50-95: {val_results.box.map:.4f} ({val_results.box.map * 100:.2f}%)")

    # Đánh giá trên Test Set
    test_results = model.val(data=str(DATA_YAML), split='test')
    print(f"✅ Test mAP50:   {test_results.box.map50:.4f} ({test_results.box.map50 * 100:.2f}%)")
    print(f"✅ Test mAP50-95:{test_results.box.map:.4f} ({test_results.box.map * 100:.2f}%)")

    # Lưu trọng số
    WEIGHTS_DIR.mkdir(parents=True, exist_ok=True)
    best_pt = OUTPUT_DIR / "fish_detection_yolov8" / "weights" / "best.pt"
    dest_pt = WEIGHTS_DIR / "best_fish_detection_yolov8.pt"

    import shutil
    if best_pt.exists():
        shutil.copy2(best_pt, dest_pt)
        print(f"💾 Trọng số tốt nhất đã lưu: {dest_pt.resolve()}")

    # Xuất ONNX
    try:
        print("⚡ Đang xuất mô hình sang định dạng ONNX cho IoT / Edge AI...")
        onnx_file = model.export(format="onnx")
        dest_onnx = WEIGHTS_DIR / "best_fish_detection_yolov8.onnx"
        if Path(onnx_file).exists():
            shutil.copy2(onnx_file, dest_onnx)
            print(f"💾 File ONNX đã lưu: {dest_onnx.resolve()}")
    except Exception as exc:
        print(f"⚠️ Chưa xuất ONNX: {exc}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Huấn luyện YOLOv8 Object Detection cho 20 loài cá cảnh.")
    parser.add_argument("--model-size", choices=['n', 's', 'm', 'l'], default='n', help="Kích thước mô hình YOLOv8 (mặc định 'n' - Nano)")
    parser.add_argument("--epochs", type=int, default=30, help="Số epochs (mặc định 30)")
    parser.add_argument("--batch", type=int, default=-1, help="Batch size (mặc định -1: AutoBatch tự động đo VRAM GPU tối ưu cho RTX 3050 4GB)")
    parser.add_argument("--imgsz", type=int, default=640, help="Kích thước ảnh đầu vào (mặc định 640)")
    parser.add_argument("--device", type=str, default=None, help="Thiết bị ('0' cho RTX 3050, 'cpu', hoặc 'cuda')")
    args = parser.parse_args()

    train_yolo_detection(args.model_size, args.epochs, args.batch, args.imgsz, args.device)
