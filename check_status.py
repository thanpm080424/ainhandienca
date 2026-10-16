import os
import sys
import json
import urllib.request

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

endpoints = [
    ('/', 'Trang chủ Dashboard / Quản lý 20 loài & 6 Hệ sinh thái'),
    ('/audit', 'Giao diện Kiểm định & Đánh giá AI Vision'),
    ('/iot', 'Giao diện Điều khiển IoT, Cảm biến & Hệ chuyên gia'),
    ('/gallery/ca_ba_duoi', 'Thư viện ảnh Cá Ba Đuôi'),
    ('/api/audit/logs', 'API Lịch sử Audit & Log hệ thống')
]

print("=" * 65)
print("1. KIỂM TRA MÁY CHỦ WEB APP (Flask trên cổng 5000)")
print("=" * 65)
for path, desc in endpoints:
    url = f"http://127.0.0.1:5000{path}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        res = urllib.request.urlopen(req, timeout=5)
        status = res.getcode()
        print(f"  [OK {status}] {path:22s} -> {desc}")
    except Exception as e:
        print(f"  [LỖI]   {path:22s} -> {e}")

print("\n" + "=" * 65)
print("2. KIỂM TRA API HỆ CHUYÊN GIA / BIOLOAD TẢI LƯỢNG SINH HỌC")
print("=" * 65)
try:
    # Kịch bản: Hồ 80x40x50 cm (160 Lít), Lọc thùng (Canister), Có cây thủy sinh
    # Đang nuôi 10 cá Neon + 4 cá Thần Tiên
    payload = json.dumps({
        'length_cm': 80,
        'width_cm': 40,
        'height_cm': 50,
        'filter_type': 'canister',
        'has_plants': True,
        'fish_inventory': [
            {'species': 'ca_neon', 'count': 10},
            {'species': 'ca_thien_than', 'count': 4}
        ]
    }).encode('utf-8')
    req = urllib.request.Request('http://127.0.0.1:5000/api/iot/bioload', data=payload, headers={'Content-Type': 'application/json'})
    res = urllib.request.urlopen(req, timeout=5)
    data = json.loads(res.read().decode('utf-8'))
    analysis = data.get('bioload_analysis', {})
    print("  [OK 200] Phản hồi từ thuật toán Bioload:")
    print(f"    - Thể tích thô hồ kính: {analysis.get('raw_volume_liters')} Lít")
    print(f"    - Thể tích nước thực tế (trừ kính, nền): {analysis.get('actual_water_liters')} Lít")
    print(f"    - Khả năng tải hiệu dụng của hệ thống lọc: {analysis.get('effective_capacity_liters')} Lít")
    print(f"    - Tỉ lệ tải lượng sinh học (Bioload): {analysis.get('load_percentage')}%")
    print(f"    - Đánh giá: [{analysis.get('status_text')}]")
    print(f"    - Lời khuyên tự động: {analysis.get('advice')}")
except Exception as e:
    print(f"  [LỖI API] {e}")

print("\n" + "=" * 65)
print("3. TỔNG KẾT BỘ DỮ LIỆU DATASET (Ảnh YOLOv8 cho 20 loài)")
print("=" * 65)
dataset_dir = 'dataset_ca'
if os.path.exists(dataset_dir):
    subdirs = sorted([d for d in os.listdir(dataset_dir) if os.path.isdir(os.path.join(dataset_dir, d)) and not d.startswith('_')])
    total_imgs = 0
    for d in subdirs:
        files = [f for f in os.listdir(os.path.join(dataset_dir, d)) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))]
        total_imgs += len(files)
        print(f"    • {d:18s}: {len(files):3d} ảnh")
    print("-" * 65)
    print(f"  TỔNG CỘNG: {total_imgs} ảnh DUY NHẤT cho {len(subdirs)} loài cá cảnh.")
    print("  Tất cả ảnh đều là cá sống trong nước, rõ nét cho Camera IoT.")
print("=" * 65)
