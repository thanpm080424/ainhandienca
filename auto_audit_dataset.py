"""
KỊCH BẢN TỰ ĐỘNG DUYỆT & LỌC SẠCH DATASET 20 LOÀI CÁ CẢNH (AUTO-AUDIT & CLEAN)
Đồ án tốt nghiệp: Lê Quốc Trí (DH52201621) & Phạm Minh Thân (DH52201428)

Tính năng:
- Tự động duyệt toàn bộ dataset 20 loài bằng mô hình YOLOv8 Edge AI kết hợp toán tử Laplacian
- Phát hiện ảnh mờ (Laplacian variance < 18.0) hoặc ảnh nghi ngờ sai loài (YOLOv8 phân loại khác loài)
- Tự động cách ly ảnh nghi ngờ vào thư mục: dataset_ca/_anh_nghi_ngo/<loài>/
- Cập nhật nhật ký thẩm định thời gian thực vào audit_log.json
"""

import os
import sys
import time
import json
import shutil
import cv2
from datetime import datetime

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(BASE_DIR, 'dataset_ca')
SUSPECT_DIR = os.path.join(DATASET_DIR, '_anh_nghi_ngo')
AUDIT_LOG_FILE = os.path.join(BASE_DIR, 'audit_log.json')

# 20 loài cá cảnh chuẩn
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


def check_blur(img_path):
    try:
        img = cv2.imread(img_path)
        if img is None:
            return 0.0
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        return round(float(cv2.Laplacian(gray, cv2.CV_64F).var()), 1)
    except Exception:
        return 0.0


def auto_audit_all_species(max_per_species=50, clean_suspect=True):
    print("=" * 75)
    print("🐟 HỆ THỐNG TỰ ĐỘNG DUYỆT & LỌC DATASET 20 LOÀI CÁ CẢNH")
    print("   Sinh viên thực hiện: Lê Quốc Trí (DH52201621) & Phạm Minh Thân (DH52201428)")
    print(f"⚙️ Chế độ cách ly: {'BẬT (Tự động chuyển ảnh sai vào _anh_nghi_ngo)' if clean_suspect else 'TẮT (Chỉ báo cáo)'}")
    print(f"📊 Giới hạn kiểm tra: {max_per_species if max_per_species else 'Toàn bộ'} ảnh/loài")
    print("=" * 75)

    import predict_fish

    # Tải audit log hiện tại
    audit_data = {}
    if os.path.exists(AUDIT_LOG_FILE):
        try:
            with open(AUDIT_LOG_FILE, 'r', encoding='utf-8') as f:
                audit_data = json.load(f)
        except Exception:
            pass
    audit_data.setdefault('recent_approved', [])
    audit_data.setdefault('flagged_wrong', [])

    total_scanned_all = 0
    total_approved_all = 0
    total_quarantined_all = 0

    valid_ext = ('.jpg', '.jpeg', '.png', '.webp', '.bmp')

    for s_idx, (s_key, s_name) in enumerate(sorted(SPECIES_MAP.items()), 1):
        s_folder = os.path.join(DATASET_DIR, s_key)
        if not os.path.exists(s_folder):
            continue

        files = [f for f in sorted(os.listdir(s_folder)) if f.lower().endswith(valid_ext)]
        if max_per_species:
            files = files[:max_per_species]

        print(f"\n[{s_idx:02d}/20] Đang tự động duyệt: {s_name} ({len(files)} ảnh)...")

        approved = 0
        quarantined = 0

        for f_idx, fname in enumerate(files, 1):
            fp = os.path.join(s_folder, fname)
            total_scanned_all += 1

            # 1. Đo độ nét
            blur_score = check_blur(fp)
            is_blur = (blur_score > 0 and blur_score < 18.0)

            # 2. Chạy YOLOv8 Edge
            res = predict_fish.predict_image(fp, as_json=False)
            is_ok = False
            reason = ""
            pred_name = s_name
            pred_key = s_key
            conf = 0.0

            if res and res.get('success'):
                top1 = res.get('top1', {})
                pred_key = top1.get('species_key')
                pred_name = top1.get('name')
                conf = top1.get('confidence', 0.0)

                if is_blur:
                    is_ok = False
                    reason = f"Độ nét quá thấp ({blur_score} < 18). Ảnh bị rung/nhòe."
                elif pred_key == s_key:
                    is_ok = True
                    reason = f"YOLOv8 xác nhận chuẩn loài {pred_name} ({conf:.1f}%)"
                else:
                    is_ok = False
                    reason = f"YOLOv8 nhận diện {pred_name} ({conf:.1f}%) thay vì {s_name}"
            else:
                is_ok = not is_blur
                reason = "Không chạy được YOLOv8; giữ lại dựa trên độ nét"

            now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            if is_ok:
                approved += 1
                total_approved_all += 1
                audit_data['recent_approved'].insert(0, {
                    'filename': fname,
                    'species': s_key,
                    'species_name': s_name,
                    'identified_as': pred_name,
                    'confidence': f"{conf:.1f}%",
                    'blur_score': blur_score,
                    'source': 'Tự động duyệt YOLOv8 Edge',
                    'timestamp': now_str
                })
            else:
                quarantined += 1
                total_quarantined_all += 1

                if clean_suspect:
                    target_sub = os.path.join(SUSPECT_DIR, s_key)
                    os.makedirs(target_sub, exist_ok=True)
                    dest = os.path.join(target_sub, fname)
                    try:
                        shutil.move(fp, dest)
                    except Exception:
                        pass

                audit_data['flagged_wrong'].insert(0, {
                    'id': f"flag_{int(time.time()*1000)}_{f_idx}",
                    'filename': fname,
                    'original_species': s_key,
                    'original_species_name': s_name,
                    'detected_as': pred_name,
                    'suggested_species_key': pred_key,
                    'reason': reason,
                    'blur_score': blur_score,
                    'action': 'Đã tự động cách ly' if clean_suspect else 'Đã gắn cờ',
                    'timestamp': now_str
                })

        print(f"   -> Kết quả: ✅ Đạt chuẩn: {approved} | ⚠️ Nghi ngờ/Cách ly: {quarantined}")

    # Cắt gọn lịch sử lưu trữ
    audit_data['recent_approved'] = audit_data['recent_approved'][:100]
    audit_data['flagged_wrong'] = audit_data['flagged_wrong'][:100]
    audit_data['current_status'] = {
        'is_busy': False,
        'action': 'Đã hoàn tất tự động duyệt & làm sạch dataset',
        'item': f"Đã quét: {total_scanned_all} ảnh (Đạt: {total_approved_all}, Cách ly: {total_quarantined_all})",
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

    with open(AUDIT_LOG_FILE, 'w', encoding='utf-8') as f:
        json.dump(audit_data, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 75)
    print("🎉 HOÀN TẤT TỰ ĐỘNG DUYỆT TOÀN BỘ 20 LOÀI CÁ CẢNH!")
    print("=" * 75)
    print(f"📊 Tổng số ảnh đã quét:      {total_scanned_all}")
    print(f"✅ Số ảnh đạt chuẩn:         {total_approved_all} ({(total_approved_all/total_scanned_all)*100:.1f}%)")
    print(f"⚠️ Số ảnh nghi ngờ/cách ly:  {total_quarantined_all} ({(total_quarantined_all/total_scanned_all)*100:.1f}%)")
    print(f"💾 Nhật ký đã cập nhật lên: {AUDIT_LOG_FILE}")
    print("🌐 Bạn có thể vào Web Dashboard xem kết quả trực quan: http://127.0.0.1:5000/audit")
    print("=" * 75)


if __name__ == '__main__':
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    clean = '--no-clean' not in sys.argv
    auto_audit_all_species(max_per_species=limit, clean_suspect=clean)
