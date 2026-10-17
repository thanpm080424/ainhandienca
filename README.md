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
| **Top-1 Accuracy** | **58.92%** | Độ chính xác nhận diện tuyệt đối |
| **Top-5 Accuracy** | **83.12%** | Khả năng nằm trong Top-5 gợi ý hàng đầu |
| **Inference Latency** | **5.12 ms / ảnh** | Cực nhanh, đáp ứng thời gian thực (Real-time) |
| **Tốc độ xử lý (FPS)** | **~195 FPS** | Xử lý mượt mà luồng stream từ camera hồ cá |
| **Định dạng Edge** | **ONNX (5.6 MB)** | Nhẹ, dễ dàng nạp lên thiết bị nhúng |

### 8. Huấn Luyện Lại Hoặc Tinh Chỉnh Mô Hình (Tùy Chọn)
```bash
# Chuẩn bị chia tập dữ liệu 80/10/10
python prepare_dataset_yolo.py

# Huấn luyện YOLOv8n-cls (15 epochs)
python train_yolo.py --epochs 15 --batch 16
```

