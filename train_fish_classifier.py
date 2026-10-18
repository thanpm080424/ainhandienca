"""Huấn luyện và lập báo cáo YOLOv8 Classification cho 20 loài cá cảnh.

Tác giả đồ án: Lê Quốc Trí (DH52201621) và Phạm Minh Thân (DH52201428).
Nguồn ảnh: dataset_ca/<ma_loai>/. Tập chia mới được tạo riêng dưới runs/;
script không ghi đè dataset_yolo hiện có.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

BASE_DIR = Path(__file__).resolve().parent
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
AUTHORS = ["Lê Quốc Trí (DH52201621)", "Phạm Minh Thân (DH52201428)"]


def discover_images(source: Path) -> dict[str, list[Path]]:
    """Đọc ảnh hợp lệ theo thư mục lớp; bỏ qua thư mục ẩn/bắt đầu bằng _.

    Kiểm tra ảnh bằng Pillow để loại tệp hỏng trước khi chia tập.
    """
    if not source.is_dir():
        raise FileNotFoundError(f"Không tìm thấy thư mục dữ liệu: {source}")
    classes: dict[str, list[Path]] = {}
    for class_dir in sorted(p for p in source.iterdir() if p.is_dir() and not p.name.startswith("_")):
        valid: list[Path] = []
        for path in sorted(class_dir.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in IMAGE_EXTENSIONS:
                continue
            try:
                with Image.open(path) as image:
                    image.verify()
                valid.append(path)
            except Exception as exc:
                print(f"Bỏ ảnh lỗi {path}: {exc}", file=sys.stderr)
        if valid:
            classes[class_dir.name] = valid
    if len(classes) < 2:
        raise ValueError(f"Cần ít nhất 2 lớp có ảnh hợp lệ trong {source}; hiện có {len(classes)}.")
    too_small = {name: len(paths) for name, paths in classes.items() if len(paths) < 3}
    if too_small:
        raise ValueError(f"Mỗi lớp cần ít nhất 3 ảnh để chia train/val/test: {too_small}")
    return classes


def water_augment(image: Image.Image, rng: random.Random) -> Image.Image:
    """Tạo một biến thể nhẹ: lệch hue/saturation, khúc xạ gợn nước, mờ nhẹ, lật ngang."""
    image = image.convert("RGB")
    # Dịch hue nhẹ trong không gian HSV (không thay đổi nhãn ảnh).
    hsv = image.convert("HSV")
    hue_shift = rng.randint(-8, 8)
    hue, saturation, value = hsv.split()
    lut = [(i + hue_shift) % 256 for i in range(256)]
    hue = hue.point(lut)
    image = Image.merge("HSV", (hue, saturation, value)).convert("RGB")
    image = ImageEnhance.Color(image).enhance(rng.uniform(0.85, 1.18))
    image = ImageEnhance.Brightness(image).enhance(rng.uniform(0.90, 1.10))

    # Các dải xanh trong mờ mô phỏng gợn khúc xạ; alpha thấp để giữ đặc điểm cá.
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    width, height = image.size
    for band in range(rng.randint(2, 4)):
        y = int((band + 1) * height / (rng.randint(4, 6)))
        amplitude = max(2, height // 90)
        points = [(x, int(y + amplitude * math.sin(x / max(12, width / 9) + band)))
                  for x in range(0, width + 1, max(1, width // 80))]
        draw.line(points, fill=(100, 205, 220, rng.randint(8, 18)), width=max(1, height // 180))
    image = Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")
    if rng.random() < 0.45:
        image = image.filter(ImageFilter.GaussianBlur(radius=rng.uniform(0.15, 0.55)))
    if rng.random() < 0.5:
        image = image.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    return image


def prepare_dataset(source: Path, output: Path, seed: int, ratios: tuple[float, float, float],
                    augment_ratio: float, force: bool) -> dict[str, Any]:
    """Chia theo lớp, giữ split test tách biệt, sao chép ảnh và tăng cường train tùy chọn."""
    if abs(sum(ratios) - 1.0) > 1e-8 or min(ratios) <= 0:
        raise ValueError("Tổng các tỷ lệ train/val/test phải bằng 1 và mỗi tỷ lệ phải dương.")
    if augment_ratio < 0:
        raise ValueError("--water-augment-ratio không được âm.")
    if output.exists():
        if not force:
            raise FileExistsError(f"Thư mục đích đã tồn tại: {output}. Dùng --force để tạo lại.")
        shutil.rmtree(output)
    classes = discover_images(source)
    rng = random.Random(seed)
    summary: dict[str, Any] = {"seed": seed, "ratios": dict(zip(("train", "val", "test"), ratios)),
                               "source": str(source), "species_count": len(classes), "classes": {}}
    for split in ("train", "val", "test"):
        (output / split).mkdir(parents=True, exist_ok=True)

    for class_name, paths in classes.items():
        items = paths.copy()
        rng.shuffle(items)
        n_train = int(len(items) * ratios[0])
        n_val = int(len(items) * ratios[1])
        partitions = {"train": items[:n_train], "val": items[n_train:n_train + n_val],
                      "test": items[n_train + n_val:]}
        counts: dict[str, int] = {}
        for split, split_paths in partitions.items():
            class_target = output / split / class_name
            class_target.mkdir(parents=True, exist_ok=True)
            for index, source_path in enumerate(split_paths):
                # Prefix index tránh xung đột tên khi thư mục nguồn có thư mục con.
                target_path = class_target / f"{index:06d}_{source_path.name}"
                shutil.copy2(source_path, target_path)
            counts[split] = len(split_paths)
        originals = partitions["train"]
        generated = int(len(originals) * augment_ratio)
        for index in range(generated):
            source_path = originals[index % len(originals)]
            try:
                with Image.open(source_path) as image:
                    augmented = water_augment(image, rng)
                    augmented.save(output / "train" / class_name / f"aug_{index:06d}.jpg", quality=94)
            except Exception as exc:
                raise RuntimeError(f"Không tạo được ảnh tăng cường từ {source_path}: {exc}") from exc
        counts["train_augmented"] = generated
        counts["train_total"] = counts["train"] + generated
        summary["classes"][class_name] = counts

    summary["total_original"] = sum(sum(c[k] for k in ("train", "val", "test")) for c in summary["classes"].values())
    summary["total_augmented"] = sum(c["train_augmented"] for c in summary["classes"].values())
    output.mkdir(parents=True, exist_ok=True)
    (output / "split_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def evaluate_test(model: Any, dataset: Path, output_dir: Path, imgsz: int, batch: int, device: str) -> dict[str, Any]:
    """Tính chỉ số theo lớp bằng phân bố xác suất YOLO và lưu CSV/JSON/ma trận nhầm lẫn."""
    import numpy as np
    from sklearn.metrics import confusion_matrix
    import matplotlib.pyplot as plt

    test_dir = dataset / "test"
    class_names = sorted(p.name for p in test_dir.iterdir() if p.is_dir())
    if not class_names:
        raise ValueError(f"Không có thư mục lớp trong {test_dir}")
    class_to_index = {name: index for index, name in enumerate(class_names)}
    paths: list[Path] = []
    truth: list[int] = []
    for class_name in class_names:
        for path in sorted((test_dir / class_name).rglob("*")):
            if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS:
                paths.append(path)
                truth.append(class_to_index[class_name])
    if not paths:
        raise ValueError(f"Không có ảnh kiểm thử hợp lệ trong {test_dir}")

    predicted: list[int] = []
    top5_correct: list[bool] = []
    # Gửi theo lô để tránh nạp toàn bộ tập test vào bộ nhớ GPU.
    for start in range(0, len(paths), batch):
        chunk = paths[start:start + batch]
        results = model.predict(source=[str(p) for p in chunk], imgsz=imgsz, device=device,
                                verbose=False, stream=False)
        if len(results) != len(chunk):
            raise RuntimeError("Số kết quả suy luận không khớp số ảnh kiểm thử.")
        for result in results:
            probs = result.probs.data.detach().cpu().numpy()
            order = np.argsort(probs)[::-1]
            predicted.append(int(order[0]))
            top5_correct.append(int(truth[len(predicted) - 1]) in set(map(int, order[:min(5, len(order))])))

    matrix = confusion_matrix(truth, predicted, labels=list(range(len(class_names))))
    rows = []
    for index, class_name in enumerate(class_names):
        tp = int(matrix[index, index])
        fp = int(matrix[:, index].sum() - tp)
        fn = int(matrix[index, :].sum() - tp)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        class_mask = [actual == index for actual in truth]
        class_top1 = sum(actual == guess for actual, guess in zip(truth, predicted) if actual == index)
        class_top5 = sum(ok for ok, is_class in zip(top5_correct, class_mask) if is_class)
        support = int(sum(class_mask))
        rows.append({"species": class_name, "precision": precision, "recall": recall, "f1_score": f1,
                     "top1_accuracy": class_top1 / support if support else 0.0,
                     "top5_accuracy": class_top5 / support if support else 0.0, "support": support})

    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "per_species_metrics.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    with (output_dir / "confusion_matrix.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(["actual/predicted", *class_names])
        for name, row in zip(class_names, matrix.tolist()):
            writer.writerow([name, *row])

    fig, ax = plt.subplots(figsize=(max(10, len(class_names) * 0.65), max(8, len(class_names) * 0.55)))
    image = ax.imshow(matrix, cmap="Blues")
    ax.set(xticks=range(len(class_names)), yticks=range(len(class_names)),
           xticklabels=class_names, yticklabels=class_names, xlabel="Loài dự đoán", ylabel="Loài thực tế",
           title="Ma trận nhầm lẫn trên tập test")
    plt.setp(ax.get_xticklabels(), rotation=65, ha="right", rotation_mode="anchor")
    fig.colorbar(image, ax=ax)
    fig.tight_layout()
    fig.savefig(output_dir / "confusion_matrix.png", dpi=180)
    plt.close(fig)

    n = len(truth)
    return {"test_samples": n, "top1_accuracy": sum(a == p for a, p in zip(truth, predicted)) / n,
            "top5_accuracy": sum(top5_correct) / n,
            "macro_precision": sum(row["precision"] for row in rows) / len(rows),
            "macro_recall": sum(row["recall"] for row in rows) / len(rows),
            "macro_f1": sum(row["f1_score"] for row in rows) / len(rows), "per_species": rows,
            "confusion_matrix": matrix.tolist(), "class_names": class_names}


def plot_training_curves(results_csv: Path, output_dir: Path) -> None:
    """Vẽ loss và độ chính xác theo epoch từ results.csv của Ultralytics."""
    import pandas as pd
    import matplotlib.pyplot as plt

    if not results_csv.is_file():
        raise FileNotFoundError(f"Ultralytics không tạo results.csv: {results_csv}")
    frame = pd.read_csv(results_csv)
    frame.columns = [column.strip() for column in frame.columns]
    epoch_col = "epoch" if "epoch" in frame.columns else frame.columns[0]
    loss_cols = [c for c in frame.columns if "loss" in c.lower()]
    accuracy_cols = [c for c in frame.columns if "accuracy" in c.lower() or "top1" in c.lower() or "top5" in c.lower()]
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    for column in loss_cols:
        axes[0].plot(frame[epoch_col], frame[column], label=column)
    axes[0].set(title="Loss theo epoch", xlabel="Epoch", ylabel="Loss")
    axes[0].legend()
    for column in accuracy_cols:
        axes[1].plot(frame[epoch_col], frame[column], label=column)
    axes[1].set(title="Accuracy theo epoch", xlabel="Epoch", ylabel="Accuracy")
    axes[1].legend()
    for axis in axes:
        axis.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_dir / "training_curves.png", dpi=180)
    plt.close(fig)


def run(args: argparse.Namespace) -> Path:
    try:
        import torch
        from ultralytics import YOLO
    except ImportError as exc:
        raise RuntimeError("Thiếu phụ thuộc: cài bằng `pip install ultralytics torch torchvision scikit-learn matplotlib pandas Pillow`.") from exc

    source = Path(args.source).resolve()
    output = Path(args.dataset_output).resolve()
    ratio = (args.train_ratio, args.val_ratio, args.test_ratio)
    summary = prepare_dataset(source, output, args.seed, ratio, args.water_augment_ratio, args.force)
    device = args.device or ("0" if torch.cuda.is_available() else "cpu")
    project_dir = Path(args.project).resolve()
    project_dir.mkdir(parents=True, exist_ok=True)

    print(f"Đã chia {summary['total_original']} ảnh gốc ({summary['species_count']} loài) vào {output}")
    print(f"Biến thể khúc xạ nước được thêm vào train: {summary['total_augmented']}")
    print(f"Huấn luyện YOLOv8{args.model}-cls trên {device}; kết quả tại {project_dir}")
    model = YOLO(args.weights or f"yolov8{args.model}-cls.pt")
    results = model.train(
        data=str(output), epochs=args.epochs, patience=args.patience, batch=args.batch,
        imgsz=args.imgsz, device=device, optimizer=args.optimizer, lr0=args.lr0,
        project=str(project_dir), name=args.name, exist_ok=args.exist_ok,
        workers=args.workers, seed=args.seed, deterministic=True, plots=True, verbose=True,
        # Augmentation online phù hợp môi trường dưới nước; ảnh gốc val/test không bị biến đổi.
        hsv_h=0.015, hsv_s=0.45, hsv_v=0.30, fliplr=0.5, flipud=0.0,
        degrees=3.0, translate=0.04, scale=0.12, erasing=0.10,
    )
    save_dir = Path(results.save_dir).resolve()
    best_weights = save_dir / "weights" / "best.pt"
    if not best_weights.is_file():
        raise FileNotFoundError(f"Không tìm thấy checkpoint tốt nhất: {best_weights}")

    report_dir = save_dir / "thesis_report"
    report_dir.mkdir(parents=True, exist_ok=True)
    trained = YOLO(str(best_weights))
    metrics = evaluate_test(trained, output, report_dir, args.imgsz, args.batch, device)
    plot_training_curves(save_dir / "results.csv", report_dir)
    report = {"project": "Hệ thống AI nhận diện 20 loài cá cảnh & Giám sát nuôi trồng thủy sinh IoT",
              "authors": AUTHORS, "model": str(best_weights), "base_model": f"YOLOv8{args.model}-cls",
              "epochs_requested": args.epochs, "seed": args.seed, "image_size": args.imgsz,
              "optimizer": args.optimizer, "device": device, "dataset": str(output),
              "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"), **metrics}
    (report_dir / "evaluation_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    target = BASE_DIR / "weights" / "best_fish_yolov8.pt"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(best_weights, target)
    print(f"Đã lưu model dùng cho ứng dụng: {target}")
    print(f"Báo cáo luận văn: {report_dir}")
    print(f"Test Top-1: {metrics['top1_accuracy']:.4f} | Top-5: {metrics['top5_accuracy']:.4f} | Macro F1: {metrics['macro_f1']:.4f}")
    return report_dir


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Chia dataset_ca, train YOLOv8-cls và xuất báo cáo đánh giá.")
    parser.add_argument("--source", default=str(BASE_DIR / "dataset_ca"), help="Thư mục ảnh nguồn dạng <root>/<loài>/*.jpg")
    parser.add_argument("--dataset-output", default=str(BASE_DIR / "runs" / "prepared_datasets" / "fish_cls_seed42"))
    parser.add_argument("--project", default=str(BASE_DIR / "runs" / "classify"))
    parser.add_argument("--name", default="fish_classifier")
    parser.add_argument("--weights", default=None, help="Checkpoint khởi tạo; mặc định tải YOLOv8*-cls pretrained nếu chưa có cục bộ.")
    parser.add_argument("--model", choices=("n", "s", "m"), default="n")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--patience", type=int, default=10, help="Early stopping theo số epoch không cải thiện.")
    parser.add_argument("--batch", type=int, default=32)
    parser.add_argument("--imgsz", type=int, choices=(224, 384), default=224)
    parser.add_argument("--optimizer", choices=("AdamW", "SGD"), default="AdamW")
    parser.add_argument("--lr0", type=float, default=0.001)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--device", default=None, help="Ultralytics device, ví dụ cpu, 0; mặc định tự dò GPU.")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--train-ratio", type=float, default=0.8)
    parser.add_argument("--val-ratio", type=float, default=0.1)
    parser.add_argument("--test-ratio", type=float, default=0.1)
    parser.add_argument("--water-augment-ratio", type=float, default=0.25,
                        help="Số ảnh tăng cường offline / ảnh train gốc mỗi lớp; đặt 0 để tắt.")
    parser.add_argument("--force", action="store_true", help="Xóa và tạo lại riêng thư mục --dataset-output đã chỉ định.")
    parser.add_argument("--exist-ok", action="store_true", help="Cho phép Ultralytics dùng lại thư mục lần chạy.")
    return parser


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    arguments = build_parser().parse_args()
    try:
        run(arguments)
    except Exception as error:
        print(f"Lỗi: {error}", file=sys.stderr)
        raise SystemExit(1)
