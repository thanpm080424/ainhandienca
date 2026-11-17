"""
Trực quan hóa nhãn Bounding Box YOLOv8 cho 20 loài cá cảnh.
Đồ án tốt nghiệp: Lê Quốc Trí (DH52201621) & Phạm Minh Thân (DH52201428)

Công dụng:
1. Vẽ bounding box và tên loài trực tiếp lên ảnh để kiểm tra chất lượng nhãn trước khi huấn luyện.
2. Tạo bảng thống kê số lượng box và kích thước box theo từng loài (train / val / test).
3. Tạo ảnh ghép (Montage) 20 loài để xem nhanh trực quan.
"""

import os
import sys
import argparse
from pathlib import Path
from collections import defaultdict
import cv2
import numpy as np

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = Path(__file__).resolve().parent
DATASET_DIR = BASE_DIR / "dataset_yolo_detection"
PREVIEW_DIR = BASE_DIR / "preview_samples"

# 20 loài cá cảnh và mã màu BGR
CLASS_INFO = [
    {"id": 0,  "key": "ca_ba_duoi",      "vn": "Ca Ba Duoi / Ca Vang",     "color": (14, 127, 255)},
    {"id": 1,  "key": "ca_bay_mau",      "vn": "Ca Bay Mau / Guppy",       "color": (180, 119, 31)},
    {"id": 2,  "key": "ca_but_chi",      "vn": "Ca But Chi",               "color": (75, 86, 140)},
    {"id": 3,  "key": "ca_chuot",        "vn": "Ca Chuot",                 "color": (34, 189, 188)},
    {"id": 4,  "key": "ca_da_quang",     "vn": "Ca Da Quang / GloFish",    "color": (194, 119, 227)},
    {"id": 5,  "key": "ca_dia",          "vn": "Ca Dia / Discus",          "color": (40, 39, 214)},
    {"id": 6,  "key": "ca_diec_anh_dao", "vn": "Ca Diec Anh Dao",          "color": (189, 103, 148)},
    {"id": 7,  "key": "ca_duoi_kiem",    "vn": "Ca Duoi Kiem",             "color": (150, 152, 255)},
    {"id": 8,  "key": "ca_hong_ket",     "vn": "Ca Hong Ket",              "color": (148, 156, 196)},
    {"id": 9,  "key": "ca_koi",          "vn": "Ca Chep Koi",              "color": (210, 182, 247)},
    {"id": 10, "key": "ca_la_han",       "vn": "Ca La Han",                "color": (213, 176, 197)},
    {"id": 11, "key": "ca_lau_kieng",    "vn": "Ca Lau Kieng",             "color": (127, 127, 127)},
    {"id": 12, "key": "ca_molly",        "vn": "Ca Molly / Binh Tich",     "color": (207, 190, 23)},
    {"id": 13, "key": "ca_mun",          "vn": "Ca Mun / Platy",           "color": (229, 218, 158)},
    {"id": 14, "key": "ca_neon",         "vn": "Ca Neon",                  "color": (44, 160, 44)},
    {"id": 15, "key": "ca_rong",         "vn": "Ca Rong / Arowana",        "color": (232, 199, 174)},
    {"id": 16, "key": "ca_sac",          "vn": "Ca Sac Canh",              "color": (141, 219, 219)},
    {"id": 17, "key": "ca_soc_ngua",     "vn": "Ca Soc Ngua",              "color": (138, 223, 152)},
    {"id": 18, "key": "ca_thien_than",   "vn": "Ca Than Tien",             "color": (199, 199, 199)},
    {"id": 19, "key": "ca_xiem",         "vn": "Ca Xiem / Betta",          "color": (121, 59, 57)},
]

ID_TO_INFO = {c["id"]: c for c in CLASS_INFO}
KEY_TO_INFO = {c["key"]: c for c in CLASS_INFO}


def read_image_safe(path: Path):
    try:
        data = np.fromfile(str(path), dtype=np.uint8)
        return cv2.imdecode(data, cv2.IMREAD_COLOR)
    except Exception:
        return None


def write_image_safe(path: Path, img):
    ext = path.suffix.lower() if path.suffix else ".jpg"
    is_ok, buf = cv2.imencode(ext, img)
    if is_ok:
        buf.tofile(str(path))
        return True
    return False


def draw_yolo_boxes(img, label_path: Path):
    """Vẽ bounding box lên ảnh từ file nhãn YOLO .txt"""
    if not label_path.exists():
        return img, 0

    h, w = img.shape[:2]
    content = label_path.read_text(encoding='utf-8').strip()
    if not content:
        return img, 0

    lines = content.splitlines()
    box_count = 0
    for line in lines:
        parts = line.strip().split()
        if len(parts) < 5:
            continue
        try:
            cid = int(parts[0])
            xc, yc, bw, bh = map(float, parts[1:5])
        except ValueError:
            continue

        info = ID_TO_INFO.get(cid, {"key": f"class_{cid}", "vn": f"Class {cid}", "color": (0, 255, 0)})
        color = info["color"]

        # Chuyển đổi từ normalized YOLO sang pixel coordinates
        x1 = max(0, int((xc - bw / 2) * w))
        y1 = max(0, int((yc - bh / 2) * h))
        x2 = min(w - 1, int((xc + bw / 2) * w))
        y2 = min(h - 1, int((yc + bh / 2) * h))

        # Vẽ khung hình chữ nhật
        cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)

        # Vẽ nhãn text có nền để nhìn rõ
        label_text = f"{info['key']} #{cid}"
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.5
        thickness = 1
        (tw, th), baseline = cv2.getTextSize(label_text, font, font_scale, thickness)

        bg_y1 = max(0, y1 - th - baseline - 4)
        bg_y2 = y1
        bg_x1 = x1
        bg_x2 = min(w - 1, x1 + tw + 6)

        cv2.rectangle(img, (bg_x1, bg_y1), (bg_x2, bg_y2), color, -1)
        cv2.putText(img, label_text, (bg_x1 + 3, bg_y2 - baseline - 2), font, font_scale, (255, 255, 255), thickness, cv2.LINE_AA)
        box_count += 1

    return img, box_count


def generate_samples(num_per_species: int = 1):
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    print(f"🎨 Đang xuất mẫu trực quan Bounding Box vào thư mục: {PREVIEW_DIR.resolve()}")

    stats = defaultdict(lambda: {"train": 0, "val": 0, "test": 0, "boxes": 0})
    samples_created = 0

    for split in ("train", "val", "test"):
        img_dir = DATASET_DIR / split / "images"
        lbl_dir = DATASET_DIR / split / "labels"
        if not img_dir.exists():
            continue

        for img_path in sorted(img_dir.glob("*.*")):
            lbl_path = lbl_dir / f"{img_path.stem}.txt"
            sp_key = "_".join(img_path.stem.split("_")[:-1])
            stats[sp_key][split] += 1

            if lbl_path.exists():
                lines = [l for l in lbl_path.read_text(encoding='utf-8').strip().splitlines() if l.strip()]
                stats[sp_key]["boxes"] += len(lines)

    # Xuất ảnh mẫu cho từng loài
    montage_tiles = []
    tile_w, tile_h = 320, 240

    for c in CLASS_INFO:
        sp = c["key"]
        imgs = sorted(list((DATASET_DIR / "train" / "images").glob(f"{sp}_*.*")))
        if not imgs:
            imgs = sorted(list((DATASET_DIR / "val" / "images").glob(f"{sp}_*.*")))

        for i in range(min(num_per_species, len(imgs))):
            target_img = imgs[i]
            split_name = target_img.parent.parent.name
            target_lbl = DATASET_DIR / split_name / "labels" / f"{target_img.stem}.txt"

            img = read_image_safe(target_img)
            if img is None:
                continue

            drawn, bcount = draw_yolo_boxes(img.copy(), target_lbl)

            out_name = f"sample_{c['id']:02d}_{sp}_{i+1}.jpg"
            write_image_safe(PREVIEW_DIR / out_name, drawn)
            samples_created += 1

            # Resize cho ảnh ghép
            resized = cv2.resize(drawn, (tile_w, tile_h))
            cv2.rectangle(resized, (0, 0), (tile_w, 22), (25, 25, 25), -1)
            cv2.putText(resized, f"#{c['id']} {sp} ({bcount} box)", (6, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)
            montage_tiles.append(resized)

    # Ghép ảnh tổng hợp 20 loài (4 hàng x 5 cột)
    if len(montage_tiles) >= 20:
        rows, cols = 4, 5
        grid = np.zeros((rows * tile_h, cols * tile_w, 3), dtype=np.uint8)
        for idx in range(min(20, len(montage_tiles))):
            r = idx // cols
            col = idx % cols
            grid[r*tile_h:(r+1)*tile_h, col*tile_w:(col+1)*tile_w] = montage_tiles[idx]

        montage_path = PREVIEW_DIR / "montage_20_species.jpg"
        write_image_safe(montage_path, grid)
        print(f"🖼️ Đã tạo ảnh ghép tổng quan 20 loài: {montage_path.resolve()}")

    # In bảng thống kê
    print("\n" + "=" * 80)
    print("📊 THỐNG KÊ BỘ DỮ LIỆU YOLOV8 DETECTION (TRAIN / VAL / TEST):")
    print("=" * 80)
    print(f"{'Loài cá':20s} | {'Train':>6s} | {'Val':>6s} | {'Test':>6s} | {'Tổng ảnh':>8s} | {'Tổng Bounding Box':>18s}")
    print("-" * 80)

    total_tr, total_va, total_te, total_bx = 0, 0, 0, 0
    for c in CLASS_INFO:
        sp = c["key"]
        s = stats[sp]
        tr = s["train"]
        va = s["val"]
        te = s["test"]
        tot = tr + va + te
        bx = s["boxes"]
        total_tr += tr
        total_va += va
        total_te += te
        total_bx += bx
        print(f"{sp:20s} | {tr:6d} | {va:6d} | {te:6d} | {tot:8d} | {bx:18d}")

    print("-" * 80)
    print(f"{'TỔNG CỘNG':20s} | {total_tr:6d} | {total_va:6d} | {total_te:6d} | {total_tr+total_va+total_te:8d} | {total_bx:18d}")
    print("=" * 80)
    print(f"✅ Hoàn tất xuất {samples_created} ảnh trực quan mẫu!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Trực quan hóa nhãn YOLOv8 Bounding Box.")
    parser.add_argument("--samples-per-class", type=int, default=1, help="Số ảnh mẫu mỗi loài (mặc định 1)")
    args = parser.parse_args()
    generate_samples(args.samples_per_class)
