"""
CVAT (Computer Vision Annotation Tool) Integration Helper for Fish Dataset
Đồ án tốt nghiệp: Lê Quốc Trí (DH52201621) & Phạm Minh Thân (DH52201428)
Hỗ trợ: https://app.cvat.ai/projects

Các tính năng chính:
1. `labels`: Xuất cấu hình nhãn 20 loài cá cảnh định dạng JSON và Text chuẩn để dán trực tiếp vào CVAT.
2. `pack`: Đóng gói ảnh cá thành file ZIP chuẩn tối ưu để upload lên Task của CVAT.
3. `convert-yolo`: Chuyển đổi file xuất từ CVAT (YOLO 1.1 format) sang cấu trúc chuẩn YOLOv8 (data.yaml, train/val split).
4. `pre-annotate`: Tự động tạo nhãn gợi ý (Pre-annotation) bằng mô hình YOLOv8 để giảm 90% công sức vẽ bounding box thủ công trên CVAT.
"""

import os
import sys
import json
import zipfile
import shutil
import argparse
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = Path(__file__).resolve().parent
DATASET_DIR = BASE_DIR / "dataset_ca"

# Danh mục 20 loài cá cảnh chuẩn của đồ án kèm mã màu phân biệt trên CVAT
SPECIES_CVAT_CONFIG = [
    {"name": "ca_ba_duoi", "vn": "Cá Ba Đuôi / Cá Vàng", "color": "#ff7f0e"},
    {"name": "ca_bay_mau", "vn": "Cá Bảy Màu / Guppy", "color": "#1f77b4"},
    {"name": "ca_but_chi", "vn": "Cá Bút Chì", "color": "#8c564b"},
    {"name": "ca_chuot", "vn": "Cá Chuột", "color": "#bcbd22"},
    {"name": "ca_da_quang", "vn": "Cá Dạ Quang / GloFish", "color": "#e377c2"},
    {"name": "ca_dia", "vn": "Cá Dĩa / Discus", "color": "#d62728"},
    {"name": "ca_diec_anh_dao", "vn": "Cá Diếc Anh Đào", "color": "#9467bd"},
    {"name": "ca_duoi_kiem", "vn": "Cá Đuôi Kiếm", "color": "#ff9896"},
    {"name": "ca_hong_ket", "vn": "Cá Hồng Két", "color": "#c49c94"},
    {"name": "ca_koi", "vn": "Cá Chép Koi", "color": "#f7b6d2"},
    {"name": "ca_la_han", "vn": "Cá La Hán", "color": "#c5b0d5"},
    {"name": "ca_lau_kieng", "vn": "Cá Lau Kiếng", "color": "#7f7f7f"},
    {"name": "ca_molly", "vn": "Cá Molly / Bình Tích", "color": "#17becf"},
    {"name": "ca_mun", "vn": "Cá Mún / Platy", "color": "#9edae5"},
    {"name": "ca_neon", "vn": "Cá Neon", "color": "#2ca02c"},
    {"name": "ca_rong", "vn": "Cá Rồng / Arowana", "color": "#aec7e8"},
    {"name": "ca_sac", "vn": "Cá Sặc Cảnh", "color": "#dbdb8d"},
    {"name": "ca_soc_ngua", "vn": "Cá Sọc Ngựa", "color": "#98df8a"},
    {"name": "ca_thien_than", "vn": "Cá Thần Tiên", "color": "#c7c7c7"},
    {"name": "ca_xiem", "vn": "Cá Xiêm / Betta", "color": "#393b79"},
]

def export_labels(output_json: Path, output_txt: Path):
    """Xuất file định dạng CVAT Labels Constructor để nạp vào https://app.cvat.ai/projects."""
    cvat_json_labels = []
    plain_labels = []

    for item in SPECIES_CVAT_CONFIG:
        cvat_json_labels.append({
            "name": item["name"],
            "color": item["color"],
            "attributes": [
                {
                    "name": "ten_tieng_viet",
                    "input_type": "text",
                    "mutable": False,
                    "values": [item["vn"]]
                }
            ]
        })
        plain_labels.append(item["name"])

    output_json.write_text(json.dumps(cvat_json_labels, indent=2, ensure_ascii=False), encoding="utf-8")
    output_txt.write_text("\n".join(plain_labels), encoding="utf-8")

    print(f"✅ Đã xuất cấu hình nhãn CVAT JSON: {output_json.resolve()}")
    print(f"✅ Đã xuất danh sách nhãn dạng Text: {output_txt.resolve()}")
    print("\n💡 Hướng dẫn tạo Project trên https://app.cvat.ai/projects/create:")
    print("   1. Nhập Project Name: 'Fish Aquarium Detection - DH52201621 & DH52201428'")
    print("   2. Tại mục 'Labels' -> Chọn tab 'Raw' -> Sao chép nội dung file cvat_labels.json dán vào!")


def package_images_for_cvat(output_zip: Path, limit_per_species: int = 50):
    """Đóng gói ảnh cá sạch đang bơi trong bể kính thành file zip để upload lên CVAT task."""
    if not DATASET_DIR.is_dir():
        print(f"❌ Không tìm thấy thư mục {DATASET_DIR}")
        return

    species_folders = sorted([p for p in DATASET_DIR.iterdir() if p.is_dir() and not p.name.startswith("_")])
    output_zip = output_zip.resolve()

    print(f"📦 Đang đóng gói ảnh cá cho CVAT Task (Tối đa {limit_per_species} ảnh/loài)...")
    total_packed = 0

    with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for folder in species_folders:
            imgs = sorted(list(folder.glob("*.jpg")) + list(folder.glob("*.png")) + list(folder.glob("*.jpeg")))
            selected = imgs[:limit_per_species]
            for img in selected:
                # Đổi tên file chứa tên loài để người gán nhãn dễ nhận biết trên CVAT
                arcname = f"{folder.name}_{img.name}"
                zf.write(img, arcname=arcname)
                total_packed += 1
            print(f"  • {folder.name:18s}: {len(selected)} ảnh")

    print(f"\n🎉 Đã nén thành công {total_packed} ảnh vào: {output_zip}")
    print(f"💡 Bước tiếp theo: Vào https://app.cvat.ai/tasks/create -> Kéo thả {output_zip.name} vào mục 'Select files'!")


def convert_cvat_to_yolov8(cvat_zip_or_dir: Path, output_dir: Path, val_ratio: float = 0.2):
    """
    Chuyển đổi tập dữ liệu xuất từ CVAT (định dạng 'YOLO 1.1') sang cấu trúc Ultralytics YOLOv8 chuẩn:
    dataset/
      ├── data.yaml
      ├── train/
      │   ├── images/
      │   └── labels/
      └── val/
          ├── images/
          └── labels/
    """
    import random
    cvat_path = cvat_zip_or_dir.resolve()
    output_dir = output_dir.resolve()

    extract_dir = output_dir / "_temp_extract"
    if extract_dir.exists():
        shutil.rmtree(extract_dir)

    if cvat_path.is_file() and cvat_path.suffix.lower() == ".zip":
        print(f"📂 Đang giải nén file CVAT export: {cvat_path.name}...")
        with zipfile.ZipFile(cvat_path, "r") as zf:
            zf.extractall(extract_dir)
        source_root = extract_dir
    else:
        source_root = cvat_path

    # Đọc danh sách classes từ obj.names
    obj_names_file = next(source_root.rglob("obj.names"), None)
    class_names = [item["name"] for item in SPECIES_CVAT_CONFIG]
    if obj_names_file and obj_names_file.is_file():
        names = [line.strip() for line in obj_names_file.read_text(encoding="utf-8").splitlines() if line.strip()]
        if names:
            class_names = names

    # Tìm tất cả ảnh và file nhãn txt tương ứng
    image_exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
    all_images = [p for p in source_root.rglob("*") if p.is_file() and p.suffix.lower() in image_exts]

    if not all_images:
        print(f"❌ Không tìm thấy ảnh nào trong {source_root}")
        if extract_dir.exists():
            shutil.rmtree(extract_dir)
        return

    print(f"🔍 Tìm thấy {len(all_images)} ảnh kèm nhãn từ CVAT export.")

    # Chuẩn bị thư mục YOLOv8
    for split in ("train", "val"):
        (output_dir / split / "images").mkdir(parents=True, exist_ok=True)
        (output_dir / split / "labels").mkdir(parents=True, exist_ok=True)

    random.seed(42)
    random.shuffle(all_images)
    n_val = int(len(all_images) * val_ratio)
    val_set = set(all_images[:n_val])

    for img_path in all_images:
        split = "val" if img_path in val_set else "train"
        label_path = img_path.with_suffix(".txt")

        # Copy ảnh
        dest_img = output_dir / split / "images" / img_path.name
        shutil.copy2(img_path, dest_img)

        # Copy nhãn (nếu có nhãn; nếu không có thì tạo file rỗng - background image)
        dest_label = output_dir / split / "labels" / f"{img_path.stem}.txt"
        if label_path.is_file():
            shutil.copy2(label_path, dest_label)
        else:
            dest_label.write_text("", encoding="utf-8")

    # Tạo data.yaml chuẩn YOLOv8
    lines = [
        f"path: {output_dir.as_posix()}",
        "train: train/images",
        "val: val/images",
        "names:"
    ]
    for i, name in enumerate(class_names):
        lines.append(f"  {i}: {name}")
    yaml_content = "\n".join(lines) + "\n"

    (output_dir / "data.yaml").write_text(yaml_content, encoding="utf-8")

    if extract_dir.exists():
        shutil.rmtree(extract_dir)

    print(f"\n🎉 Đã chuyển đổi thành công sang YOLOv8 Dataset tại: {output_dir}")
    print(f"   • Train images: {len(all_images) - n_val}")
    print(f"   • Val images:   {n_val}")
    print(f"   • File cấu hình: {output_dir / 'data.yaml'}")
    print(f"\n🚀 Lệnh huấn luyện YOLOv8:")
    print(f"   yolo detect train data={output_dir / 'data.yaml'} model=yolov8n.pt epochs=50 imgsz=640 batch=16")


def pre_annotate_for_cvat(input_dir: Path, output_dir: Path, conf_threshold: float = 0.35):
    """
    Sử dụng mô hình YOLOv8n detector kết hợp bộ phân loại cá để tự động tạo nhãn Bounding Box.
    Giúp người dùng tải trực tiếp nhãn vào CVAT để chỉ việc kiểm tra, không cần vẽ từ đầu.
    """
    try:
        from ultralytics import YOLO
    except ImportError:
        print("❌ Cần thư viện ultralytics. Hãy chạy: pip install ultralytics")
        return

    det_model_path = BASE_DIR / "yolov8n.pt"
    if not det_model_path.is_file():
        print("📥 Đang tải mô hình yolov8n.pt...")
        det_model = YOLO("yolov8n.pt")
    else:
        det_model = YOLO(str(det_model_path))

    output_dir.mkdir(parents=True, exist_ok=True)
    images = [p for p in input_dir.rglob("*") if p.is_file() and p.suffix.lower() in {".jpg", ".png", ".jpeg"}]

    print(f"🤖 Đang chạy AI Pre-annotation cho {len(images)} ảnh...")
    annotated_count = 0

    class_to_id = {item["name"]: i for i, item in enumerate(SPECIES_CVAT_CONFIG)}

    for img_path in images:
        results = det_model.predict(source=str(img_path), conf=conf_threshold, verbose=False)[0]
        label_lines = []

        parent_name = img_path.parent.name
        species_id = class_to_id.get(parent_name, 0)

        for box in results.boxes:
            xywhn = box.xywhn[0].tolist()
            label_lines.append(f"{species_id} {xywhn[0]:.6f} {xywhn[1]:.6f} {xywhn[2]:.6f} {xywhn[3]:.6f}")

        label_file = output_dir / f"{img_path.stem}.txt"
        label_file.write_text("\n".join(label_lines), encoding="utf-8")
        if label_lines:
            annotated_count += 1

    print(f"✅ Hoàn tất! Đã tạo nhãn gợi ý cho {annotated_count}/{len(images)} ảnh.")
    print(f"📁 Thư mục lưu nhãn: {output_dir}")


def main():
    parser = argparse.ArgumentParser(description="Hỗ trợ tích hợp nền tảng gán nhãn CVAT (https://app.cvat.ai).")
    subparsers = parser.add_subparsers(dest="action", required=True)

    # Lệnh labels
    lbl_parser = subparsers.add_parser("labels", help="Xuất file cấu hình nhãn 20 loài cá cho CVAT Project")
    lbl_parser.add_argument("--json-out", type=Path, default=BASE_DIR / "cvat_labels.json", help="File JSON xuất ra")
    lbl_parser.add_argument("--txt-out", type=Path, default=BASE_DIR / "cvat_labels.txt", help="File TXT xuất ra")

    # Lệnh pack
    pack_parser = subparsers.add_parser("pack", help="Đóng gói ảnh cá để tạo Task trên CVAT")
    pack_parser.add_argument("--output", type=Path, default=BASE_DIR / "dataset_ca_cvat.zip", help="File zip xuất ra")
    pack_parser.add_argument("--limit-per-species", type=int, default=50, help="Số ảnh/loài đưa lên CVAT (mặc định 50)")

    # Lệnh convert-yolo
    conv_parser = subparsers.add_parser("convert-yolo", help="Chuyển đổi dataset tải từ CVAT sang cấu trúc YOLOv8")
    conv_parser.add_argument("--cvat-input", type=Path, required=True, help="File zip hoặc thư mục xuất từ CVAT (YOLO 1.1)")
    conv_parser.add_argument("--output-dir", type=Path, default=BASE_DIR / "dataset_cvat_yolov8", help="Thư mục YOLOv8 xuất ra")
    conv_parser.add_argument("--val-ratio", type=float, default=0.2, help="Tỷ lệ tập validation (mặc định 0.2)")

    # Lệnh pre-annotate
    pre_parser = subparsers.add_parser("pre-annotate", help="Tự động tạo nhãn bounding box ban đầu bằng AI")
    pre_parser.add_argument("--input-dir", type=Path, default=DATASET_DIR, help="Thư mục ảnh đầu vào")
    pre_parser.add_argument("--output-dir", type=Path, default=BASE_DIR / "cvat_pre_annotations", help="Thư mục nhãn đầu ra")

    args = parser.parse_args()

    if args.action == "labels":
        export_labels(args.json_out, args.txt_out)
    elif args.action == "pack":
        package_images_for_cvat(args.output, args.limit_per_species)
    elif args.action == "convert-yolo":
        convert_cvat_to_yolov8(args.cvat_input, args.output_dir, args.val_ratio)
    elif args.action == "pre-annotate":
        pre_annotate_for_cvat(args.input_dir, args.output_dir)


if __name__ == "__main__":
    main()
