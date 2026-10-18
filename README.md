# 🐟 Hệ Thống Nhận Diện Cá Cảnh IoT & Giám Định Dataset 20 Loài

> **Đồ Án Tốt Nghiệp Đại Học**  
> **Sinh viên thực hiện:**  
> - Lê Quốc Trí (MSSV: DH52201621)  
> - Phạm Minh Thân (MSSV: DH52201428)  

Ứng dụng Web chuyên dụng phục vụ đề tài nghiên cứu **"Hệ Thống Camera IoT Nhận Diện Các Loài Cá Cảnh Bằng Trí Tuệ Nhân Tạo (YOLOv8) & Giám Sát Môi Trường Thủy Sinh"**.

---

## 🌟 Tính Năng Nổi Bật

1. 📊 **Dashboard Thống Kê & Giám Sát Sức Khỏe Dataset**:
   - Theo dõi tiến độ thu thập của 20 loài cá cảnh nhiệt đới.
   - Thống kê tỷ lệ hoàn thành (mục tiêu ≥ 300 ảnh chuẩn IoT/loài).
   - Nhật ký giám định thời gian thực hiển thị ảnh mới duyệt và ảnh bị cách ly.

2. 🖼️ **Thư Viện Ảnh (Gallery) & Kiểm Duyệt Trực Quan**:
   - Duyệt ảnh theo từng loài với tính năng phân trang (24 ảnh/trang).
   - Tự động sắp xếp ảnh mới nhất lên đầu.
   - Hỗ trợ phóng to Lightbox và xem thuộc tính ảnh (kích thước, độ nét Laplacian).

3. 🔍 **Bộ Lọc Thị Giác AI Đa Tầng (Gemini 4 Argon & Gemini 3.5 Flash)**:
   - **Argon-First Multi-Tier Architecture**: Tận dụng sức mạnh suy luận thị giác của **Gemini 4 Argon** và tự động dự phòng sang **Gemini 3.5 Flash**.
   - Soi trực tiếp vào pixel hình ảnh:
     * Xác nhận cá sống đang bơi trong nước.
     * Đối chiếu chuẩn xác hình thái giải phẫu học của từng loài.
     * Tự động loại bỏ bìa YouTube có chữ to, ảnh ghép, slide infographic, quảng cáo phụ kiện/thuốc.
     * Cách ly ảnh nghi ngờ vào thư mục riêng `_anh_nghi_ngo/` để đối chiếu.

4. 🤖 **Bộ Thu Thập Đa Nguồn Toàn Cầu (5 Global Biodiversity Sources)**:
   - Tích hợp API nghiên cứu đa dạng sinh học: iNaturalist Open Data, GBIF (Global Biodiversity Information Facility), Wikimedia Commons, Flickr Community, Bing High-Res.
   - Chống trùng lặp tuyệt đối bằng mã băm kép: **MD5 + 64-bit dHash + khoảng cách Hamming ≤ 4**.
   - Bộ lọc rõ nét cho camera IoT: Laplacian variance ≥ 38.0, tương phản dải động, độ phong phú màu sắc RGB.

5. 🌡️ **Tư Vấn Môi Trường Sống & Cảm Biến IoT Thủy Sinh**:
   - Phân loại 20 loài theo 6 họ sinh thái (Poeciliidae, Cyprinidae, Characidae, Cichlidae, Osphronemidae, Siluriformes).
   - Khuyến nghị thông số kỹ thuật chuẩn: Nhiệt độ (°C), độ pH, tầng nước bơi, độ hòa tan oxy.
   - Thiết lập ngưỡng cảnh báo (Alert Rules) cho hệ thống cảm biến IoT.

---

## 📋 Danh Sách 20 Loài Cá Cảnh

| STT | Mã Thư Mục | Tên Tiếng Việt | Tên Khoa Học / Tên Tiếng Anh | Họ Sinh Thái |
|:---:|:-----------|:---------------|:-----------------------------|:-------------|
| 1 | `ca_ba_duoi` | Cá Ba Đuôi / Cá Vàng | *Carassius auratus* (Goldfish) | Họ Cá Chép (Cyprinidae) |
| 2 | `ca_bay_mau` | Cá Bảy Màu | *Poecilia reticulata* (Guppy) | Họ Khổng Tước (Poeciliidae) |
| 3 | `ca_but_chi` | Cá Bút Chì | *Crossocheilus oblongus* (Siamese Algae Eater) | Họ Cá Chép (Cyprinidae) |
| 4 | `ca_chuot` | Cá Chuột | *Corydoras spp.* (Cory Catfish) | Họ Cá Da Trơn (Callichthyidae) |
| 5 | `ca_da_quang` | Cá Dạ Quang | *Gymnocorymbus ternetzi* (GloFish) | Họ Characin (Characidae) |
| 6 | `ca_dia` | Cá Dĩa | *Symphysodon spp.* (Discus) | Họ Cá Rô Phi (Cichlidae) |
| 7 | `ca_diec_anh_dao` | Cá Diếc Anh Đào | *Puntius titteya* (Cherry Barb) | Họ Cá Chép (Cyprinidae) |
| 8 | `ca_duoi_kiem` | Cá Đuôi Kiếm | *Xiphophorus hellerii* (Swordtail) | Họ Khổng Tước (Poeciliidae) |
| 9 | `ca_hong_ket` | Cá Hồng Két | *Amphilophus citrinellus* (Blood Parrot) | Họ Cá Rô Phi (Cichlidae) |
| 10 | `ca_koi` | Cá Chép Koi | *Cyprinus carpio koi* (Nishikigoi) | Họ Cá Chép (Cyprinidae) |
| 11 | `ca_la_han` | Cá La Hán | Flowerhorn Cichlid | Họ Cá Rô Phi (Cichlidae) |
| 12 | `ca_lau_kieng` | Cá Lau Kiếng / Tỳ Bà | *Hypostomus plecostomus* (Pleco) | Họ Cá Giáp (Loricariidae) |
| 13 | `ca_molly` | Cá Molly / Bình Tích | *Poecilia sphenops* (Molly) | Họ Khổng Tước (Poeciliidae) |
| 14 | `ca_mun` | Cá Mún / Hắc Molly | *Xiphophorus maculatus* (Platy) | Họ Khổng Tước (Poeciliidae) |
| 15 | `ca_neon` | Cá Neon | *Paracheirodon innesi* (Neon Tetra) | Họ Characin (Characidae) |
| 16 | `ca_rong` | Cá Rồng | *Scleropages formosus* (Arowana) | Họ Cá Rồng (Osteoglossidae) |
| 17 | `ca_sac` | Cá Sặc Cảnh | *Trichogaster spp.* (Gourami) | Họ Cá Sặc (Osphronemidae) |
| 18 | `ca_soc_ngua` | Cá Sóc Ngựa | *Danio rerio* (Zebra Danio) | Họ Cá Chép (Danionidae) |
| 19 | `ca_thien_than` | Cá Thần Tiên | *Pterophyllum scalare* (Angelfish) | Họ Cá Rô Phi (Cichlidae) |
| 20 | `ca_xiem` | Cá Xiêm / Betta | *Betta splendens* (Siamese Fighting Fish) | Họ Cá Sặc (Osphronemidae) |

---

## 🛠️ Cài Đặt & Khởi Chạy

### 1. Yêu cầu môi trường
* Python 3.10 trở lên
* Cài đặt các thư viện phụ thuộc:
```bash
pip install -r requirements.txt
```

### 2. Cấu hình khóa API Gemini (Tùy chọn cho tính năng AI Vision)
```bash
# Windows PowerShell
$env:GEMINI_API_KEY="your_api_key_here"

# Linux / MacOS
export GEMINI_API_KEY="your_api_key_here"
```

### 3. Khởi chạy ứng dụng Web
```bash
python app.py
```
Mở trình duyệt truy cập: `http://127.0.0.1:5000`

### 4. Chạy bộ thu thập ảnh AI tự động
```bash
# Nạp ảnh cho 1 loài cụ thể (+30 ảnh)
python smart_fish_collector.py ca_ba_duoi 30

# Nạp tự động quét cả 20 loài
python run_batch_collector.py
```

### 5. Quét dọn và cách ly ảnh sai bằng AI Vision
```bash
# Rà quét 50 ảnh của loài cá dạ quang
python ai_vision_audit_cleaner.py ca_da_quang 50
```

### 6. Thử nghiệm Nhận Diện Loài Cá (YOLOv8 & ONNX)
Mô hình đã được huấn luyện sẵn và lưu tại thư mục `weights/`:
* `weights/best_fish_yolov8.pt` (PyTorch model)
* `weights/best_fish_yolov8.onnx` (ONNX model tối ưu cho thiết bị Edge IoT: Raspberry Pi, Jetson Nano, ESP32 Gateway)

Thử nhận diện ngay trên ảnh mẫu có sẵn trong thư mục `sample_images/`:
```bash
# Nhận diện cá Koi mẫu
python predict_fish.py sample_images/ca_koi.jpg

# Nhận diện cá Neon mẫu
python predict_fish.py sample_images/ca_neon.jpg
```

### 7. Đánh Giá Hiệu Năng Mô Hình (Evaluation on Test Set)
Chạy kịch bản đánh giá độc lập trên 628 ảnh test:
```bash
python evaluate_model.py
```

**Bảng kết quả benchmark trên CPU (Intel Core i7):**
| Chỉ số (Metric) | Kết quả thực nghiệm | Ý nghĩa đồ án IoT |
|:---|:---:|:---|
| **Top-1 Accuracy** | **72.29%** | Độ chính xác nhận diện tuyệt đối (Tăng từ 58.9%) |
| **Top-5 Accuracy** | **89.33%** | Khả năng nằm trong Top-5 gợi ý hàng đầu (Tăng từ 83.1%) |
| **Inference Latency** | **6.02 ms / ảnh** | Cực nhanh, đáp ứng thời gian thực (Real-time) |
| **Tốc độ xử lý (FPS)** | **~166.1 FPS** | Xử lý mượt mà luồng stream từ camera hồ cá |
| **Định dạng Edge** | **ONNX (5.6 MB)** | Nhẹ, dễ dàng nạp lên thiết bị nhúng |


### 8. Huấn Luyện Lại Hoặc Tinh Chỉnh Mô Hình (Tùy Chọn)
```bash
# Chuẩn bị chia tập dữ liệu 80/10/10
python prepare_dataset_yolo.py

# Huấn luyện YOLOv8n-cls (15 epochs)
python train_yolo.py --epochs 15 --batch 16
```

### Huấn luyện bộ phân loại cá cảnh từ `dataset_ca/`

Script `train_fish_classifier.py` chia ảnh từ `dataset_ca/<ma_loai>/` theo tỷ lệ 80/10/10 vào thư mục riêng dưới `runs/prepared_datasets/`, sau đó fine-tune YOLOv8 Classification. Script không xóa hay ghi đè `dataset_yolo/` hiện có.

```powershell
python -m pip install -r requirements-train.txt
python train_fish_classifier.py
```

Mặc định dùng YOLOv8n-cls, tối đa 50 epoch, batch 32, ảnh 224 px, AdamW, patience 10 và thêm biến thể khúc xạ nước cho 25% ảnh train mỗi lớp. Có thể chọn ảnh 384 px, model khác hoặc tắt tăng cường offline:

```powershell
python train_fish_classifier.py --imgsz 384 --model s --water-augment-ratio 0
```

Thư mục `runs/classify/fish_classifier/thesis_report/` (hoặc tên tương ứng với `--name`) chứa báo cáo JSON, chỉ số Precision/Recall/F1/Top-1/Top-5 theo loài, ma trận nhầm lẫn CSV/PNG và đồ thị loss/accuracy. Checkpoint tốt nhất được sao chép sang `weights/best_fish_yolov8.pt`. Dùng `--force` nếu muốn tạo lại thư mục đã chỉ định bằng `--dataset-output`.

### Lịch sử IoT và báo cáo PDF

API `/api/iot/predict` ghi số đo vào `data/history.db` khi multipart form có `device_id`, `temperature` hoặc `ph`. Có thể xem 50 bản ghi mới nhất cùng thống kê theo ngày tại:

```text
GET /api/iot/history
GET /api/iot/history?days=30&device_id=raspberry-pi-aquarium-01
GET /api/iot/export_pdf?days=7
```

Cài ReportLab cùng các phụ thuộc ứng dụng và xuất báo cáo từ terminal:

```powershell
python -m pip install -r requirements.txt
python export_pdf_report.py --days 7 --output report.pdf
```

Dùng `--days 30` cho tháng gần nhất. PDF có thống kê lượt nhận diện theo loài, số liệu trung bình theo ngày và nhật ký cảnh báo; font Arial hoặc DejaVu Sans được tự dò để hiển thị tiếng Việt. Đặt `FISH_HISTORY_DB` để chọn vị trí SQLite khác. Endpoint tải PDF trả trực tiếp file, ví dụ `http://127.0.0.1:5000/api/iot/export_pdf?days=7`.

### Thu thập ảnh bổ sung bằng Codex

`codex_fish_collector.py` tìm ảnh từ Wikimedia Commons và iNaturalist; DuckDuckGo Images là nguồn bổ sung tùy chọn. Script lọc kích thước, định dạng, dung lượng, tỷ lệ khung hình, ảnh có nền trong suốt nhiều và tên có dấu hiệu logo/biểu tượng; ảnh lưu thành JPEG với tiền tố `codex_` và provenance/license được ghi ở `dataset_ca/codex_fish_collector_manifest.jsonl`.

```powershell
python -m pip install -r requirements-collector.txt
python codex_fish_collector.py --species ca_but_chi --limit 100
python codex_fish_collector.py --auto-fill
```

`--auto-fill` ưu tiên lớp thiếu nhiều nhất tới mốc 500 ảnh; `--limit N` giới hạn số ảnh mới cho mỗi lớp trong chế độ này. Nguồn DDG không cung cấp giấy phép đáng tin cậy qua kết quả tìm kiếm nên các ảnh đó bị bỏ qua mặc định; chỉ dùng `--allow-unlicensed` khi bạn sẽ kiểm tra quyền sử dụng thủ công. Dù lấy từ truy vấn tên loài, ảnh vẫn cần được rà soát/kiểm định AI trước khi đưa vào tập huấn luyện, vì script lọc chất lượng ảnh chứ không xác nhận nhãn sinh học.

