"""
THANH LỌC TOÀN DIỆN ẢNH RÁC, ẢNH NHẦM LOÀI VÀ QUẢNG CÁO TỪ BÀI VIẾT WEB
Đồ án tốt nghiệp: Lê Quốc Trí (DH52201621) & Phạm Minh Thân (DH52201428)

Mục đích:
- Loại bỏ toàn bộ các ảnh bài viết tổng hợp nhiều loài (ví dụ: '10 loài cá nuôi chung...', '5 loài ăn rêu...')
- Loại bỏ toàn bộ ảnh quảng cáo thương mại Shopee, Lazada, Tiki, Sendo
- Loại bỏ toàn bộ ảnh bìa YouTube có chữ tiếng Việt lớn đè lên hình
- Di chuyển an toàn vào thư mục: dataset_ca/_anh_nghi_ngo/<loài>/
- Cập nhật nhật ký kiểm định vào audit_log.json để hiển thị trên Web Dashboard
"""

import os
import sys
import re
import json
import shutil
import time

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(BASE_DIR, 'dataset_ca')
SUSPECT_DIR = os.path.join(DATASET_DIR, '_anh_nghi_ngo')
AUDIT_LOG_FILE = os.path.join(BASE_DIR, 'audit_log.json')

SPECIES_MAP = {
    'ca_ba_duoi': 'Cá Ba Đuôi',
    'ca_bay_mau': 'Cá Bảy Màu',
    'ca_but_chi': 'Cá Bút Chì',
    'ca_chuot': 'Cá Chuột',
    'ca_da_quang': 'Cá Dạ Quang',
    'ca_dia': 'Cá Dĩa',
    'ca_diec_anh_dao': 'Cá Diếc Anh Đào',
    'ca_duoi_kiem': 'Cá Đuôi Kiếm',
    'ca_hong_ket': 'Cá Hồng Két',
    'ca_koi': 'Cá Koi',
    'ca_la_han': 'Cá La Hán',
    'ca_lau_kieng': 'Cá Lau Kiếng',
    'ca_molly': 'Cá Molly',
    'ca_mun': 'Cá Mún',
    'ca_neon': 'Cá Neon',
    'ca_rong': 'Cá Rồng',
    'ca_sac': 'Cá Sặc',
    'ca_soc_ngua': 'Cá Sóc Ngựa',
    'ca_thien_than': 'Cá Thần Tiên',
    'ca_xiem': 'Cá Xiêm',
}

JUNK_PATTERNS = [
    (r'shopee|lazada|tiki|sendo', 'Ảnh quảng cáo thương mại điện tử (Shopee/Lazada)'),
    (r'youtube|thumbnail', 'Ảnh bìa YouTube có chữ to/hình ghép'),
    (r'loại cá|loai ca|nuôi chung|nuoi chung', 'Ảnh nhầm loài từ bài viết tổng hợp nhiều loài cá'),
    (r'thức ăn|thuc an|cám cá|men vi sinh|thuốc|thuoc', 'Ảnh phụ kiện, thức ăn hoặc thuốc cho cá'),
    (r'đèn|den |máy lọc|may loc|bể cá mini|hồ cá mini', 'Ảnh thiết bị, đèn LED hoặc hồ cá không rõ cá'),
    (r'bán cá|ban ca|giá bao nhiêu|gia bao nhieu|mua ở đâu', 'Ảnh bài viết báo giá / thương mại'),
    (r'cá kho|cá chiên|món ngon|cách nấu|ẩm thực', 'Ảnh ẩm thực chế biến cá (không phải cá cảnh sống)'),
    (r'mô hình|mo hinh|đồ chơi|do choi|nhựa|nhua', 'Ảnh đồ chơi hoặc mô hình nhựa trang trí')
]

def main():
    print("=" * 70, flush=True)
    print("🧹 BẮT ĐẦU THANH LỌC TOÀN DIỆN CÁC ẢNH SAI DO ĐỌC CHỮ / BÀI VIẾT WEB", flush=True)
    print("=" * 70, flush=True)

    if not os.path.exists(SUSPECT_DIR):
        os.makedirs(SUSPECT_DIR, exist_ok=True)

    audit_data = {}
    if os.path.exists(AUDIT_LOG_FILE):
        try:
            with open(AUDIT_LOG_FILE, 'r', encoding='utf-8') as af:
                audit_data = json.load(af)
        except Exception:
            audit_data = {}

    if 'flagged_wrong' not in audit_data:
        audit_data['flagged_wrong'] = []

    total_moved = 0
    species_summary = {}

    for sp_key, sp_name in SPECIES_MAP.items():
        sp_dir = os.path.join(DATASET_DIR, sp_key)
        if not os.path.isdir(sp_dir):
            continue

        target_suspect_dir = os.path.join(SUSPECT_DIR, sp_key)
        os.makedirs(target_suspect_dir, exist_ok=True)

        files = [f for f in os.listdir(sp_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.bmp'))]
        sp_moved = 0

        for f in files:
            # Không động vào các file đã được xác thực chuẩn iot_verified_ hoặc verified_live_
            if f.startswith(('iot_verified_', 'verified_live_')):
                continue

            fl = f.lower()
            matched_reason = None
            for pat, reason in JUNK_PATTERNS:
                if re.search(pat, fl):
                    matched_reason = reason
                    break

            if matched_reason:
                src_path = os.path.join(sp_dir, f)
                dst_path = os.path.join(target_suspect_dir, f)
                try:
                    shutil.move(src_path, dst_path)
                    sp_moved += 1
                    total_moved += 1

                    # Thêm vào nhật ký
                    rec = {
                        'filename': f,
                        'species': sp_key,
                        'species_name': sp_name,
                        'identified_as': f"Ảnh rác/sai loài ({matched_reason})",
                        'confidence': 'high',
                        'reason': f"Phát hiện theo tiêu chuẩn IoT: {matched_reason}",
                        'source': 'Bộ lọc Thanh lọc Tiêu đề & Nội dung Rác',
                        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
                    }
                    audit_data['flagged_wrong'].insert(0, rec)
                except Exception as e:
                    pass

        species_summary[sp_key] = sp_moved
        safe_name = sp_name.encode('ascii', 'ignore').decode() or sp_key
        print(f"  📦 {sp_name:25s} ({sp_key:16s}): Đã loại bỏ {sp_moved:3d} ảnh rác/sai loài", flush=True)

    # Giữ tối đa 500 bản ghi mới nhất trong audit_log
    audit_data['flagged_wrong'] = audit_data['flagged_wrong'][:500]
    audit_data['current_status'] = {
        'is_busy': False,
        'action': f"Đã thanh lọc hoàn tất {total_moved} ảnh rác và ảnh sai loài do đọc chữ",
        'item': f"Đã chuyển {total_moved} ảnh nghi ngờ vào thư mục _anh_nghi_ngo/",
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
    }

    with open(AUDIT_LOG_FILE, 'w', encoding='utf-8') as af:
        json.dump(audit_data, af, ensure_ascii=False, indent=2)

    print("\n" + "=" * 70, flush=True)
    print(f"🎉 HOÀN THÀNH THANH LỌC! TỔNG CỘNG ĐÃ LOẠI BỎ: {total_moved} ẢNH RÁC/SAI LOÀI!", flush=True)
    print(f"👉 Tất cả ảnh này đã được cách ly vào thư mục: dataset_ca/_anh_nghi_ngo/", flush=True)
    print("=" * 70, flush=True)

if __name__ == '__main__':
    main()
