"""Script rà soát chất lượng ảnh nghiêm ngặt theo yêu cầu người dùng:
1. Phát hiện người/tay/cơ thể người (dùng YOLOv8 Object Detection + Mặt/Cơ thể + Tỷ lệ da người YCrCb).
2. Phát hiện động vật ăn/bắt cá (chim, mèo, chó...).
3. Kiểm tra độ tin cậy nhận diện loài cá (áp dụng cứng ngưỡng >= 60.0%).
4. BÁO CÁO TOÀN BỘ ẢNH NGHI NGỜ MÀ KHÔNG XÓA HAY DI CHUYỂN ẢNH GỐC.

Tác giả đồ án: Lê Quốc Trí (DH52201621) và Phạm Minh Thân (DH52201428).
"""

import os
import sys
import json
import glob
import time
from pathlib import Path
from PIL import Image
import numpy as np
import cv2
from ultralytics import YOLO

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = Path(__file__).resolve().parent
DATASET_DIR = BASE_DIR / "dataset_ca"

# Load models
print("Đang nạp mô hình nhận diện đối tượng yolov8n.pt...")
detector = YOLO(str(BASE_DIR / "yolov8n.pt"))

print("Đang nạp mô hình phân loại cá best_fish_yolov8.pt...")
import predict_fish

def detect_skin_ratio(pil_img):
    """Phát hiện tỷ lệ da người (bàn tay, cánh tay, ngón tay giữ cá) qua không gian màu YCrCb."""
    try:
        thumb = pil_img.copy()
        thumb.thumbnail((300, 300))
        img_np = np.array(thumb.convert('RGB'))
        ycrcb = cv2.cvtColor(img_np, cv2.COLOR_RGB2YCrCb)
        
        # Ngưỡng màu da người thông dụng trong thị giác máy tính:
        # 133 <= Cr <= 173, 77 <= Cb <= 127
        lower_skin = np.array([0, 133, 77], dtype=np.uint8)
        upper_skin = np.array([255, 173, 127], dtype=np.uint8)
        
        mask = cv2.inRange(ycrcb, lower_skin, upper_skin)
        skin_pixels = np.count_nonzero(mask)
        total_pixels = mask.size
        skin_ratio = skin_pixels / total_pixels
        return skin_ratio
    except Exception:
        return 0.0

def audit_image(image_path, target_species):
    """
    Rà soát 1 ảnh theo các tiêu chí nghiêm ngặt:
    - Không có người, bàn tay người giữ cá.
    - Không có chim, mèo, chó ăn/bắt cá.
    - YOLOv8 phân loại cá: Đúng loài mục tiêu VÀ Conf >= 60.0%.
    """
    suspicions = []
    
    try:
        pil_img = Image.open(image_path)
        pil_img.verify()
        pil_img = Image.open(image_path)
    except Exception as e:
        return True, [f"Ảnh lỗi hoặc không mở được: {e}"], {}
    
    # 1. Quét đối tượng lạ bằng YOLOv8n (người, chim, mèo, chó)
    try:
        det_res = detector(image_path, verbose=False, conf=0.22)[0]
        detected_objects = {}
        for box in det_res.boxes:
            cls_name = det_res.names[int(box.cls[0])]
            conf = float(box.conf[0])
            detected_objects[cls_name] = max(detected_objects.get(cls_name, 0.0), conf)
            
        if 'person' in detected_objects:
            suspicions.append(f"Phát hiện người / tay người cầm cá ({detected_objects['person']*100:.1f}%)")
        if 'bird' in detected_objects:
            suspicions.append(f"Phát hiện chim bắt/ăn cá ({detected_objects['bird']*100:.1f}%)")
        if 'cat' in detected_objects:
            suspicions.append(f"Phát hiện mèo bắt/ăn cá ({detected_objects['cat']*100:.1f}%)")
        if 'dog' in detected_objects:
            suspicions.append(f"Phát hiện chó ({detected_objects['dog']*100:.1f}%)")
    except Exception as e:
        detected_objects = {}
        
    # 2. Quét bàn tay/ngón tay qua tỷ lệ màu da người
    skin_ratio = detect_skin_ratio(pil_img)
    if skin_ratio >= 0.16:
        suspicions.append(f"Tỷ lệ màu da người lớn ({skin_ratio*100:.1f}% >= 16%): nghi vấn tay người cầm cá")
        
    # 3. Phân loại cá bằng YOLOv8 Classifier
    try:
        cls_res = predict_fish.predict_pil(pil_img)
        if cls_res and cls_res.get('success'):
            top1 = cls_res.get('top1', {})
            pred_key = top1.get('species_key')
            conf = float(top1.get('confidence', 0.0))
            pred_name = top1.get('name')
            
            if pred_key != target_species:
                suspicions.append(f"Sai loài: Mô hình nhận diện là '{pred_name}' ({conf:.1f}%) thay vì '{target_species}'")
            elif conf < 60.0:
                suspicions.append(f"Độ tin cậy dưới ngưỡng cứng 60%: chỉ đạt {conf:.1f}%")
        else:
            suspicions.append("Không nhận diện được cá trong ảnh")
            pred_key = None
            conf = 0.0
    except Exception as e:
        suspicions.append(f"Lỗi khi chạy bộ phân loại cá: {e}")
        pred_key = None
        conf = 0.0

    is_suspicious = len(suspicions) > 0
    details = {
        'skin_ratio': round(skin_ratio * 100, 1),
        'detected_objects': detected_objects,
        'predicted_species': pred_key,
        'confidence': conf
    }
    return is_suspicious, suspicions, details


def main():
    target_folders = sys.argv[1:] if len(sys.argv) > 1 else ['ca_but_chi', 'ca_ba_duoi', 'ca_mun', 'ca_soc_ngua', 'ca_duoi_kiem', 'ca_rong', 'ca_bay_mau']
    
    print("=" * 70)
    print("BẮT ĐẦU RÀ SOÁT CHẤT LƯỢNG ẢNH THEO TIÊU CHUẨN NGHIÊM NGẶT")
    print("Tiêu chuẩn: Không người/tay cầm, không động vật ăn, đúng loài & Conf >= 60.0%")
    print("Cam kết: CHỈ BÁO CÁO, KHÔNG XÓA HAY DI CHUYỂN ẢNH GỐC")
    print("=" * 70)
    
    flagged_results = []
    
    for sp in target_folders:
        folder = DATASET_DIR / sp
        if not folder.is_dir():
            continue
            
        # Lấy tất cả ảnh trong thư mục, ưu tiên quét các ảnh mới nhất (verified_clean_* và codex_*)
        all_images = sorted(list(folder.glob("verified_clean_*.jpg")) + list(folder.glob("codex_*.jpg")), 
                            key=lambda p: p.stat().st_mtime, reverse=True)
        
        # Quét 60 ảnh gần nhất của mỗi loài để rà soát đợt thêm ảnh gần đây
        sample_images = all_images[:60]
        print(f"\n🔍 Đang rà soát loài '{sp}' ({len(sample_images)} ảnh mới nhất)...")
        
        sp_flagged_count = 0
        for p in sample_images:
            is_suspicious, reasons, details = audit_image(str(p), sp)
            if is_suspicious:
                sp_flagged_count += 1
                flag_item = {
                    'species': sp,
                    'filename': p.name,
                    'path': str(p),
                    'reasons': reasons,
                    'details': details
                }
                flagged_results.append(flag_item)
                print(f"  ❌ NGHI NGỜ: {p.name}")
                for r in reasons:
                    print(f"      - {r}")
                    
        print(f"  -> Hoàn tất '{sp}': phát hiện {sp_flagged_count}/{len(sample_images)} ảnh nghi ngờ.")
        
    print("\n" + "=" * 70)
    print(f"TỔNG KẾT RÀ SOÁT: PHÁT HIỆN {len(flagged_results)} ẢNH NGHI NGỜ TRÊN TOÀN BỘ CÁC LOÀI ĐƯỢC QUÉT.")
    print("=" * 70)
    
    # Lưu báo cáo vào file JSON để tham chiếu
    report_path = BASE_DIR / "strict_audit_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(flagged_results, f, ensure_ascii=False, indent=2)
    print(f"Báo cáo chi tiết đã lưu vào: {report_path}")

if __name__ == "__main__":
    main()
