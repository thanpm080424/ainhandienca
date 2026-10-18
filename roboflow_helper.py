"""
ROBOFLOW INTEGRATION HELPER FOR FISH RECOGNITION DATASET
Đồ án tốt nghiệp: Lê Quốc Trí (DH52201621) & Phạm Minh Thân (DH52201428)

Công cụ hỗ trợ:
1. Đóng gói dataset_ca thành file ZIP chuẩn để tải lên Roboflow gán nhãn Bounding Box.
2. Tải dataset từ Roboflow về máy cục bộ bằng Roboflow Python SDK.
3. Chuyển đổi định dạng hoặc kiểm tra nhãn cho YOLOv8.
"""

import os
import sys
import zipfile
import argparse
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = Path(__file__).resolve().parent
DATASET_DIR = BASE_DIR / "dataset_ca"

def package_for_roboflow(output_zip: Path, max_per_species: int = 100):
    """Đóng gói ảnh cá (chọn lọc tối đa max_per_species ảnh/loài) thành file ZIP để upload lên Roboflow."""
    if not DATASET_DIR.is_dir():
        print(f"❌ Không tìm thấy thư mục {DATASET_DIR}")
        return

    species_folders = sorted([p for p in DATASET_DIR.iterdir() if p.is_dir() and not p.name.startswith("_")])
    output_zip = output_zip.resolve()
    print(f"📦 Bắt đầu đóng gói ảnh cá lên Roboflow: {output_zip.name}")
    print(f"🎯 Mức trần: {max_per_species} ảnh/loài để upload và gán nhãn bounding box nhanh chóng.")

    total_packed = 0
    with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for folder in species_folders:
            images = sorted(list(folder.glob("*.jpg")) + list(folder.glob("*.png")) + list(folder.glob("*.jpeg")))
            selected = images[:max_per_species]
            for img in selected:
                arcname = f"{folder.name}/{img.name}"
                zf.write(img, arcname=arcname)
                total_packed += 1
            print(f"  - {folder.name:18s}: {len(selected)} ảnh")

    print(f"\n✅ Đã đóng gói thành công {total_packed} ảnh vào: {output_zip}")
    print(f"💡 Hướng dẫn: Đăng nhập https://app.roboflow.com -> Tạo Project 'fish-aquarium-detection' -> Kéo thả file {output_zip.name} vào để gán nhãn!")


def download_from_roboflow(api_key: str, workspace: str, project_name: str, version: int, dest_dir: Path):
    """Tải dataset từ Roboflow Universe về máy theo định dạng YOLOv8."""
    try:
        from roboflow import Roboflow
    except ImportError:
        print("❌ Chưa cài đặt thư viện roboflow. Hãy chạy: pip install roboflow")
        return

    print(f"🌐 Đang kết nối Roboflow: workspace={workspace}, project={project_name}, v{version}...")
    rf = Roboflow(api_key=api_key)
    project = rf.workspace(workspace).project(project_name)
    dataset = project.version(version).download("yolov8", location=str(dest_dir.resolve()))
    print(f"✅ Tải thành công dataset về: {dataset.location}")


def main():
    parser = argparse.ArgumentParser(description="Hỗ trợ tích hợp Roboflow cho đồ án Nhận diện cá cảnh.")
    subparsers = parser.add_subparsers(dest="action", required=True)

    # Lệnh pack
    pack_parser = subparsers.add_parser("pack", help="Đóng gói dataset_ca thành ZIP để upload lên Roboflow")
    pack_parser.add_argument("--output", type=Path, default=BASE_DIR / "dataset_ca_roboflow.zip", help="Đường dẫn file zip xuất ra")
    pack_parser.add_argument("--limit-per-species", type=int, default=100, help="Số ảnh tối đa mỗi loài để upload gán nhãn (mặc định 100)")

    # Lệnh download
    dl_parser = subparsers.add_parser("download", help="Tải dataset đã gán nhãn từ Roboflow về")
    dl_parser.add_argument("--api-key", required=True, help="Roboflow Private API Key")
    dl_parser.add_argument("--workspace", default="ainhandienca", help="Tên workspace Roboflow")
    dl_parser.add_argument("--project", default="fish-aquarium-detection", help="Tên project Roboflow")
    dl_parser.add_argument("--version", type=int, default=1, help="Phiên bản dataset trên Roboflow")
    dl_parser.add_argument("--dest", type=Path, default=BASE_DIR / "dataset_roboflow", help="Thư mục lưu dataset")

    args = parser.parse_args()
    if args.action == "pack":
        package_for_roboflow(args.output, args.limit_per_species)
    elif args.action == "download":
        download_from_roboflow(args.api_key, args.workspace, args.project, args.version, args.dest)


if __name__ == "__main__":
    main()
