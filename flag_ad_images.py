import os
import sys
import json
from datetime import datetime

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(BASE_DIR, 'dataset_ca')
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
    'ca_xiem': 'Cá Xiêm'
}

AD_RULES = [
    ('shopee', 'Quảng cáo Shopee / Bán hàng', 'Ảnh chụp banner sản phẩm thương mại trên sàn TMĐT Shopee, không phải cá sống trong bể nước.'),
    ('lazada', 'Quảng cáo Lazada / Bán hàng', 'Ảnh chụp banner sản phẩm thương mại trên sàn TMĐT Lazada, không phải cá sống trong bể nước.'),
    ('tiki', 'Quảng cáo Tiki / Bán hàng', 'Ảnh chụp sản phẩm thương mại trên sàn TMĐT Tiki.'),
    ('khô cá', 'Món ăn / Khô cá ăn liền', 'Ảnh chụp khô cá / thực phẩm khô đóng gói, vi phạm tiêu chuẩn cá sống trong hồ nước.'),
    ('kho ca', 'Món ăn / Khô cá ăn liền', 'Ảnh chụp khô cá / thực phẩm khô đóng gói, vi phạm tiêu chuẩn cá sống trong hồ nước.'),
    ('nhựa resin', 'Mô hình đồ chơi nhựa', 'Ảnh chụp mô hình cá cảnh bằng nhựa resin / đồ chơi trang trí, không phải sinh vật sống.'),
    ('mô hình', 'Mô hình đồ chơi / Tượng', 'Ảnh chụp mô hình hoặc tượng cá, không phải cá thật.'),
    ('cám', 'Bao bì cám thức ăn', 'Ảnh bao bì gói cám hạt / thức ăn gia súc gia cầm thủy sản, không phải cá bơi trong bể.'),
    ('thức ăn', 'Bao bì thức ăn cá', 'Ảnh chụp gói thức ăn cho cá cảnh, cần loại bỏ khỏi dataset huấn luyện YOLOv8.'),
    ('men vi sinh', 'Chai thuốc / Vi sinh', 'Ảnh chai lọ men vi sinh hoặc chế phẩm sinh học xử lý nước hồ cá.'),
    ('seachem', 'Hóa chất hồ cá', 'Ảnh chai hóa chất / chất đệm cân bằng pH của hãng Seachem.'),
    ('quang phổ', 'Đèn LED hồ cá', 'Ảnh thiết bị đèn chiếu sáng hồ cá, không phải cá cảnh.'),
    ('đèn b', 'Đèn LED hồ cá', 'Ảnh thiết bị đèn chiếu sáng hồ cá cảnh.')
]

def scan_and_flag():
    with open(AUDIT_LOG_FILE, 'r', encoding='utf-8') as f:
        audit_data = json.load(f)

    existing_flagged = {
        (item['original_species'], item['filename'])
        for item in audit_data.get('flagged_wrong', [])
    }

    flagged_list = list(audit_data.get('flagged_wrong', []))
    new_flagged_count = 0

    print("=" * 70)
    print("QUÉT VÀ ĐƯA ẢNH RÁC / QUẢNG CÁO VÀO MỤC 'ẢNH NHẦM LẪN'")
    print("=" * 70)

    for sp_key in sorted(SPECIES_MAP.keys()):
        sp_dir = os.path.join(DATASET_DIR, sp_key)
        if not os.path.isdir(sp_dir):
            continue

        for fname in os.listdir(sp_dir):
            if not fname.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.bmp')):
                continue

            fl = fname.lower()
            detected_tag = None
            detected_reason = None

            for kw, tag, reason in AD_RULES:
                if kw in fl:
                    detected_tag = tag
                    detected_reason = reason
                    break

            if detected_tag:
                key = (sp_key, fname)
                if key not in existing_flagged:
                    new_item = {
                        'filename': fname,
                        'original_species': sp_key,
                        'original_species_name': SPECIES_MAP[sp_key],
                        'detected_as': detected_tag,
                        'suggested_species_key': '',
                        'reason': detected_reason,
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    flagged_list.append(new_item)
                    existing_flagged.add(key)
                    new_flagged_count += 1
                    print(f"  🚨 [{SPECIES_MAP[sp_key]}] {fname[:55]}... -> {detected_tag}")

    audit_data['flagged_wrong'] = flagged_list
    with open(AUDIT_LOG_FILE, 'w', encoding='utf-8') as f:
        json.dump(audit_data, f, ensure_ascii=False, indent=2)

    print("-" * 70)
    print(f"✅ ĐÃ ĐƯA THÀNH CÔNG {new_flagged_count} ẢNH RÁC/QUẢNG CÁO VÀO MỤC 'ẢNH NHẦM LẪN'!")
    print(f"👉 Tổng cộng hiện có: {len(flagged_list)} ảnh trong mục 'Ảnh Nhầm Lẫn Do AI Phát Hiện'.")
    print(f"👉 Bạn hãy mở ngay Dashboard (http://127.0.0.1:5000/) để xem trực quan!")
    print("=" * 70)

if __name__ == '__main__':
    scan_and_flag()
