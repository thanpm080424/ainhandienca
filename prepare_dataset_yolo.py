"""
KỊCH BẢN CHUẨN HÓA & PHÂN CHIA TẬP DỮ LIỆU HUẤN LUYỆN YOLOV8 (TRAIN / VAL / TEST)
Đồ án tốt nghiệp: Lê Quốc Trí (DH52201621) & Phạm Minh Thân (DH52201428)
Hệ thống nhận diện cá cảnh IoT 20 loài

Tỉ lệ phân chia chuẩn khoa học:
- 80% Train: Dùng để huấn luyện trọng số mô hình YOLOv8
- 10% Val:   Dùng để tinh chỉnh siêu tham số và đánh giá epoch (Validation)
- 10% Test:  Dùng để kiểm thử độc lập cuối cùng (Unseen Testing)
"""

import os
import sys
import shutil
import random
import json
from collections import defaultdict
from PIL import Image

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_RAW = os.path.join(BASE_DIR, 'dataset_ca')
DATASET_YOLO = os.path.join(BASE_DIR, 'dataset_yolo')

RANDOM_SEED = 42
TRAIN_RATIO = 0.80
VAL_RATIO = 0.10
TEST_RATIO = 0.10


def prepare_yolo_dataset():
    random.seed(RANDOM_SEED)

    print("=" * 75)
    print("🚀 BẮT ĐẦU PHÂN CHIA DATASET CHO MÔ HÌNH YOLOV8 (20 LOÀI CÁ CẢNH IOT)")
    print(f"📊 Tỉ lệ: {int(TRAIN_RATIO*100)}% Train | {int(VAL_RATIO*100)}% Val | {int(TEST_RATIO*100)}% Test (Seed={RANDOM_SEED})")
    print(f"📁 Thư mục nguồn: {DATASET_RAW}")
    print(f"📁 Thư mục đích:  {DATASET_YOLO}")
    print("=" * 75)

    if os.path.exists(DATASET_YOLO):
        print(f"⚠️ Thư mục '{DATASET_YOLO}' đã tồn tại, đang dọn sạch để tạo mới...")
        shutil.rmtree(DATASET_YOLO)

    for split in ['train', 'val', 'test']:
        os.makedirs(os.path.join(DATASET_YOLO, split), exist_ok=True)

    species_folders = sorted([
        d for d in os.listdir(DATASET_RAW)
        if os.path.isdir(os.path.join(DATASET_RAW, d)) and not d.startswith('_')
    ])

    stats = {}
    total_train = 0
    total_val = 0
    total_test = 0

    print(f"\n{'STT':<4} {'Mã Loài':<18} {'Tổng ảnh':<10} {'Train (80%)':<12} {'Val (10%)':<11} {'Test (10%)':<11}")
    print("-" * 75)

    for idx, sp in enumerate(species_folders, 1):
        sp_src = os.path.join(DATASET_RAW, sp)
        valid_images = []
        for f in os.listdir(sp_src):
            if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                fp = os.path.join(sp_src, f)
                if os.path.isfile(fp):
                    valid_images.append(f)

        random.shuffle(valid_images)
        total_count = len(valid_images)

        n_train = int(total_count * TRAIN_RATIO)
        n_val = int(total_count * VAL_RATIO)
        n_test = total_count - n_train - n_val

        train_files = valid_images[:n_train]
        val_files = valid_images[n_train : n_train + n_val]
        test_files = valid_images[n_train + n_val :]

        for split, files in [('train', train_files), ('val', val_files), ('test', test_files)]:
            dest_dir = os.path.join(DATASET_YOLO, split, sp)
            os.makedirs(dest_dir, exist_ok=True)
            for fname in files:
                src_path = os.path.join(sp_src, fname)
                dest_path = os.path.join(dest_dir, fname)
                shutil.copy2(src_path, dest_path)

        stats[sp] = {
            'total': total_count,
            'train': len(train_files),
            'val': len(val_files),
            'test': len(test_files)
        }

        total_train += len(train_files)
        total_val += len(val_files)
        total_test += len(test_files)

        print(f"{idx:<4} {sp:<18} {total_count:<10} {len(train_files):<12} {len(val_files):<11} {len(test_files):<11}")

    grand_total = total_train + total_val + total_test
    print("-" * 75)
    print(f"{'TỔNG':<4} {'20 LOÀI CÁ':<18} {grand_total:<10} {total_train:<12} {total_val:<11} {total_test:<11}")
    print("=" * 75)

    # Lưu metadata phân chia vào file json
    summary_path = os.path.join(DATASET_YOLO, 'split_summary.json')
    summary_data = {
        'seed': RANDOM_SEED,
        'ratios': {'train': TRAIN_RATIO, 'val': VAL_RATIO, 'test': TEST_RATIO},
        'grand_total': grand_total,
        'total_train': total_train,
        'total_val': total_val,
        'total_test': total_test,
        'species_count': len(species_folders),
        'species_breakdown': stats
    }
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary_data, f, ensure_ascii=False, indent=2)

    print(f"\n✅ ĐÃ HOÀN THÀNH PHÂN CHIA!")
    print(f"📄 Báo cáo chi tiết đã lưu tại: {summary_path}")
    print(f"👉 Thư mục sẵn sàng cho Ultralytics YOLOv8: {DATASET_YOLO}")


if __name__ == '__main__':
    prepare_yolo_dataset()
