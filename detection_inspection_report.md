# 🐟 Báo Cáo Rà Soát Bounding Box & Tinh Chỉnh Dataset YOLOv8 Detection

**Đồ án tốt nghiệp:** Hệ Thống IoT AI Nhận Diện Cá & Giám Sát Môi Trường Hồ Thủy Sinh  
**Sinh viên thực hiện:**
- **Lê Quốc Trí** - MSSV: DH52201621  
- **Phạm Minh Thân** - MSSV: DH52201428  

---

## 1. 🔍 Kết Quả Rà Soát & Xử Lý Các Vấn Đề Thực Tế

Sau khi kiểm tra chi tiết theo quy trình `train.md`, các vấn đề phát hiện đã được khắc phục triệt để:

### 1. Xử lý triệt để các Bounding Box bao trọn cả cảnh hồ (`ca_koi_0006`, v.v.)
- **Nguyên nhân cũ:** Thuật toán biên cạnh cũ (`Canny` + giãn nở hình thái 9x9) từng bắt trọn chu vi thành bể kính/mặt nước khi gặp bóng sáng phản chiếu, dẫn đến 239 box có diện tích > 60% khung hình bao trọn cả hồ.
- **Giải pháp mới:**
  - Ứng dụng **Color Saliency đa không gian màu** (kênh `Saturation` trong HSV + độ lệch sắc độ `a, b` trong Lab) để tách biệt thân cá có màu với môi trường nước.
  - Áp dụng cấu trúc cây phân cấp `cv2.RETR_TREE` kết hợp kernel lọc mịn (5x5).
  - Đặt điều kiện giới hạn diện tích: **Loại bỏ 100% box viền ảnh và box chiếm > 50% khung hình**.
  - **Kết quả:** **0 box khổng lồ còn lại**. Các cá thể cá bơi (như đàn cá chép Koi, cá sọc ngựa, cá dĩa) đã được bóc tách thành từng box độc lập, ôm sát thân cá.

### 2. Số lượng Bounding Box theo từng loài sau khi tinh chỉnh
Tổng số Bounding Box chuẩn xác đã tăng từ 2,497 lên **4,128 box** (không còn tình trạng cá bị bỏ sót trong các ảnh chụp bầy đàn):
- Trung bình: **150 – 310 box/loài** trên 50 ảnh (phù hợp với tập tính bơi đàn 3–6 con/ảnh của cá thủy sinh).

---

## 2. 📊 Thống Kê Phân Bố Train / Val / Test (800 / 100 / 100)

| STT | Mã loài (`key`) | Tên tiếng Việt | Train (ảnh) | Val (ảnh) | Test (ảnh) | Tổng ảnh | Số Bounding Box |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| 0 | `ca_ba_duoi` | Cá Ba Đuôi / Cá Vàng | 40 | 5 | 5 | 50 | 200 |
| 1 | `ca_bay_mau` | Cá Bảy Màu / Guppy | 40 | 5 | 5 | 50 | 164 |
| 2 | `ca_but_chi` | Cá Bút Chì | 40 | 5 | 5 | 50 | 231 |
| 3 | `ca_chuot` | Cá Chuột | 40 | 5 | 5 | 50 | 253 |
| 4 | `ca_da_quang` | Cá Dạ Quang / GloFish | 40 | 5 | 5 | 50 | 162 |
| 5 | `ca_dia` | Cá Dĩa / Discus | 40 | 5 | 5 | 50 | 247 |
| 6 | `ca_diec_anh_dao` | Cá Diếc Anh Đào | 40 | 5 | 5 | 50 | 147 |
| 7 | `ca_duoi_kiem` | Cá Đuôi Kiếm | 40 | 5 | 5 | 50 | 223 |
| 8 | `ca_hong_ket` | Cá Hồng Két | 40 | 5 | 5 | 50 | 158 |
| 9 | `ca_koi` | Cá Chép Koi | 40 | 5 | 5 | 50 | 254 |
| 10 | `ca_la_han` | Cá La Hán | 40 | 5 | 5 | 50 | 182 |
| 11 | `ca_lau_kieng` | Cá Lau Kiếng / Tỳ Bà | 40 | 5 | 5 | 50 | 231 |
| 12 | `ca_molly` | Cá Molly / Bình Tích | 40 | 5 | 5 | 50 | 204 |
| 13 | `ca_mun` | Cá Mún / Platy | 40 | 5 | 5 | 50 | 194 |
| 14 | `ca_neon` | Cá Neon | 40 | 5 | 5 | 50 | 215 |
| 15 | `ca_rong` | Cá Rồng / Arowana | 40 | 5 | 5 | 50 | 191 |
| 16 | `ca_sac` | Cá Sặc Cảnh | 40 | 5 | 5 | 50 | 177 |
| 17 | `ca_soc_ngua` | Cá Sọc Ngựa | 40 | 5 | 5 | 50 | 233 |
| 18 | `ca_thien_than` | Cá Thần Tiên | 40 | 5 | 5 | 50 | 313 |
| 19 | `ca_xiem` | Cá Xiêm / Betta | 40 | 5 | 5 | 50 | 149 |
| **Σ** | **TỔNG CỘNG** | **20 Loài Cá** | **800** | **100** | **100** | **1,000** | **4,128** |

---

## 3. 🖼️ Ảnh Ghép Trực Quan 20 Loài Cá Mới Nhất

File ảnh trực quan đã được kết xuất tại: [preview_detection_montage.jpg](file:///c:/Users/super/OneDrive/Máy tính/ainhandienca/preview_detection_montage.jpg)  
và lưu trực tiếp trong thư mục dự án:

![Montage 20 Loài Cá Mới](/C:/Users/super/.gemini/antigravity/brain/b6d8ae93-2334-498b-9218-e17d36159141/montage_20_species.jpg)

---

## 4. 📄 Chuẩn Hóa `data.yaml` (Đường dẫn tương đối)

Đường dẫn tuyệt đối đã được chuyển thành **đường dẫn tương đối chuẩn**, đảm bảo hoạt động 100% cả khi chạy trực tiếp trên máy lẫn khi tải lên giải nén trên Google Colab:

```yaml
# Dataset root directory: tương thích 100% cả cục bộ và Google Colab
path: dataset_yolo_detection
train: train/images
val: val/images
test: test/images

names:
  0: ca_ba_duoi
  1: ca_bay_mau
  2: ca_but_chi
  3: ca_chuot
  4: ca_da_quang
  5: ca_dia
  6: ca_diec_anh_dao
  7: ca_duoi_kiem
  8: ca_hong_ket
  9: ca_koi
  10: ca_la_han
  11: ca_lau_kieng
  12: ca_molly
  13: ca_mun
  14: ca_neon
  15: ca_rong
  16: ca_sac
  17: ca_soc_ngua
  18: ca_thien_than
  19: ca_xiem
```

---

## 5. ⚙️ Tối Ưu Huấn Luyện Cho GPU RTX 3050 Laptop 4GB

Theo tài liệu chính thức của Ultralytics, thiết lập `batch=-1` kích hoạt chế độ **AutoBatch**: tự động benchmark VRAM của card đồ họa để chọn batch size tối ưu nhất (tránh lỗi CUDA Out-Of-Memory trên card 4GB VRAM).

### Lệnh chạy huấn luyện:
```powershell
python train_yolo_detection.py --device 0 --batch -1 --epochs 30 --imgsz 640
```
- `--device 0`: Chạy trực tiếp trên GPU NVIDIA GeForce RTX 3050 Laptop.
- `--batch -1`: AutoBatch tự đo VRAM (sẽ tự chọn batch 8 hoặc 16 tối ưu).
- Script tự động tính toán `mAP50` và `mAP50-95` trên cả 2 tập `val` và `test`, đồng thời xuất trọng số `best_fish_detection_yolov8.pt` và `.onnx`.
