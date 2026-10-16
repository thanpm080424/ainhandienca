"""
CHƯƠNG TRÌNH NẠP ẢNH TỰ ĐỘNG THÔNG MINH CHO TẤT CẢ CÁC LOÀI CÁ CẢNH IOT
Đồ án tốt nghiệp: Lê Quốc Trí (DH52201621) & Phạm Minh Thân (DH52201428)
- Tự động quét 20 loài, ưu tiên nạp các loài dưới 320 ảnh trước.
- Đảm bảo 100% không trùng lặp (MD5 + dHash + Hamming <= 4).
- Tiêu chuẩn độ nét cao cho Camera IoT (YOLOv8).
- Tự động đồng bộ vào Web Dashboard (http://127.0.0.1:5000/) ngay lập tức.
"""

import os
import sys
import json
import time
from datetime import datetime
import smart_fish_collector
import sync_recent_approved

# Reconfigure console Windows UTF-8
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(BASE_DIR, 'dataset_ca')
TARGET_THRESHOLD = 320


def get_species_counts():
    counts = {}
    for sp_key in smart_fish_collector.SPECIES_METADATA.keys():
        sp_dir = os.path.join(DATASET_DIR, sp_key)
        if os.path.exists(sp_dir):
            imgs = [f for f in os.listdir(sp_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))]
            counts[sp_key] = len(imgs)
        else:
            counts[sp_key] = 0
    return counts


def main():
    print("=" * 70, flush=True)
    print("🚀 BẮT ĐẦU NẠP BỔ SUNG TOÀN DIỆN CHO 20 LOÀI CÁ CẢNH IOT (MỤC TIÊU >= 320 ẢNH)", flush=True)
    print("=" * 70, flush=True)

    smart_fish_collector.init_database_hashes()

    counts = get_species_counts()
    sorted_species = sorted(counts.items(), key=lambda x: x[1])

    print("\n📊 BẢNG THỐNG KÊ SỐ LƯỢNG ẢNH HIỆN TẠI:", flush=True)
    for sp_key, count in sorted_species:
        status_icon = "🟢" if count >= TARGET_THRESHOLD else "🟡"
        meta = smart_fish_collector.SPECIES_METADATA.get(sp_key, {})
        print(f"  {status_icon} {meta.get('vn_name', sp_key):25s} ({sp_key:16s}): {count:4d} ảnh", flush=True)

    total_added = 0
    for sp_key, count in sorted_species:
        if count < TARGET_THRESHOLD:
            needed = min(35, TARGET_THRESHOLD - count)
            try:
                added = smart_fish_collector.process_species_collection(sp_key, target_add=needed)
                total_added += added
                # Đồng bộ ngay vào Web Dashboard
                try:
                    sync_recent_approved.sync_approved()
                except Exception:
                    pass
            except Exception as e:
                print(f"  ❌ Lỗi thu thập {sp_key}: {e}", flush=True)

    print("\n" + "=" * 70, flush=True)
    print(f"🎉 HOÀN THÀNH ĐỢT NẠP ẢNH! TỔNG CỘNG ĐÃ THÊM: +{total_added} ẢNH RÕ NÉT IOT!", flush=True)
    print("=" * 70, flush=True)


if __name__ == '__main__':
    main()
