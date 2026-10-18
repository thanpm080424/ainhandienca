import os
import sys
import shutil
import unicodedata
from PIL import Image
import numpy as np
import predict_fish

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(BASE_DIR, 'dataset_ca')
QUARANTINE_DIR = os.path.join(DATASET_DIR, '_anh_nghi_ngo')
os.makedirs(QUARANTINE_DIR, exist_ok=True)

model, _ = predict_fish.load_model()
if not model:
    print("Error: Could not load YOLOv8 model")
    sys.exit(1)

def check_image_clarity(p, target_species):
    try:
        sz = os.path.getsize(p)
        if sz < 15000:
            return False, f"Dung lượng quá nhỏ ({sz} bytes)"

        with Image.open(p) as im:
            w, h = im.size
            if w < 320 or h < 320:
                return False, f"Độ phân giải quá nhỏ ({w}x{h})"

            # Sharpness check
            gray = np.array(im.convert('L'), dtype=np.float32)
            conv = (gray[:-2, 1:-1] + gray[2:, 1:-1] + gray[1:-1, :-2] + gray[1:-1, 2:] - 4 * gray[1:-1, 1:-1])
            lap_var = float(np.var(conv))
            if lap_var < 25.0:
                return False, f"Ảnh mờ nét (Laplacian={lap_var:.1f})"

            # YOLOv8 Prominent Fish Verification
            res = predict_fish.predict_pil(im)
            if not res or not res.get('success'):
                return False, "Lỗi chạy YOLOv8"

            top1 = res['top1']
            pred_key = top1['species_key']
            conf = top1['confidence']

            # Tiêu chuẩn nghiêm ngặt:
            # 1. Nếu Top-1 đúng loài thì độ tin cậy phải >= 50% (cá phải to, rõ nét, chiếm khung hình)
            if pred_key == target_species:
                if conf < 50.0:
                    return False, f"Cá không rõ trong khung hình (Top-1 đúng loài nhưng tin cậy chỉ {conf:.1f}% < 50%)"
                return True, f"Top-1 chuẩn nét: {conf:.1f}%"

            # 2. Nếu Top-1 khác loài nhưng Top-2 đúng loài:
            top3 = res.get('top3', [])
            for item in top3[:2]:
                if item.get('species_key') == target_species and item.get('confidence', 0.0) >= 42.0 and top1['confidence'] < 48.0:
                    return True, f"Top-2 chấp nhận được: {item.get('confidence'):.1f}%"

            return False, f"Nhầm loài hoặc cá quá nhỏ/khó thấy: Top-1 là {top1.get('name')} ({conf:.1f}%)"

    except Exception as e:
        return False, str(e)


def run_audit(dry_run=True):
    print("=" * 65)
    print("🔍 BẮT ĐẦU RÀ SOÁT & LỌC BỎ ẢNH CÁ KHÔNG RÕ NÉT / NHỎ TRONG KHUNG HÌNH")
    print(f"Chế độ: {'DRY RUN (Chỉ kiểm tra, chưa di chuyển)' if dry_run else 'THỰC THI CÁCH LY'}")
    print("=" * 65)

    species_list = [d for d in sorted(os.listdir(DATASET_DIR)) 
                    if not d.startswith('_') and os.path.isdir(os.path.join(DATASET_DIR, d))]

    total_checked = 0
    total_quarantined = 0
    results_per_species = {}

    for sp in species_list:
        sp_dir = os.path.join(DATASET_DIR, sp)
        q_sp_dir = os.path.join(QUARANTINE_DIR, sp)
        if not dry_run:
            os.makedirs(q_sp_dir, exist_ok=True)

        files = [f for f in os.listdir(sp_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))]
        sp_quarantine = []

        for f in files:
            total_checked += 1
            p = os.path.join(sp_dir, f)
            ok, reason = check_image_clarity(p, sp)
            if not ok:
                sp_quarantine.append((f, reason))
                total_quarantined += 1
                if not dry_run:
                    dest = os.path.join(q_sp_dir, f)
                    try:
                        shutil.move(p, dest)
                    except Exception as e:
                        print(f"Error moving {f}: {e}")

        results_per_species[sp] = {
            'total': len(files),
            'quarantined': len(sp_quarantine),
            'kept': len(files) - len(sp_quarantine),
            'reasons': sp_quarantine[:3]
        }
        print(f"Loài '{sp}': {len(files)} ảnh -> Giữ: {len(files) - len(sp_quarantine)} ảnh nét, Cách ly: {len(sp_quarantine)} ảnh mờ/nhỏ")

    print("\n" + "=" * 65)
    print(f"TỔNG KẾT RÀ SOÁT:")
    print(f"  - Tổng ảnh đã quét: {total_checked}")
    print(f"  - Tổng ảnh đạt chuẩn nét rõ ràng: {total_checked - total_quarantined} ảnh")
    print(f"  - Tổng ảnh bị cách ly (cá nhỏ / mờ / khó nhìn): {total_quarantined} ảnh")
    print("=" * 65)


if __name__ == '__main__':
    dry_run = '--execute' not in sys.argv
    run_audit(dry_run=dry_run)
