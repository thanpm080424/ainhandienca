# 🏷️ Hướng Dẫn Sử Dụng CVAT (app.cvat.ai) Gán Nhãn & Huấn Luyện Nhận Diện Cá Trong Hồ Cá

**Đồ án tốt nghiệp:** Hệ Thống IoT AI Nhận Diện Cá & Giám Sát Môi Trường Hồ Thủy Sinh  
**Sinh viên thực hiện:**
- **Lê Quốc Trí** - MSSV: DH52201621
- **Phạm Minh Thân** - MSSV: DH52201428

**Nền tảng gán nhãn:** [https://app.cvat.ai/projects](https://app.cvat.ai/projects) (Computer Vision Annotation Tool)

---

## 🎯 Tại Sao Dùng CVAT Cho Bài Toán Nhận Diện Cá Trong Hồ?

1. **Nhận diện nhiều con cá cùng bơi**: Trong hồ cá thực tế, nhiều cá khác loài hoặc cùng loài bơi cùng lúc. CVAT cho phép vẽ Bounding Box (khung chữ nhật) quanh từng con cá một cách chuẩn xác.
2. **Hỗ trợ video hồ cá**: Bạn có thể quay 1 video hồ cá 30 giây đến 1 phút, tải lên CVAT và dùng tính năng **AI Tracker** để tự động bám đuôi cá bơi qua các khung hình mà không phải vẽ từng ảnh!
3. **AI Assist (SAM & Interactors)**: CVAT tích hợp sẵn AI hỗ trợ gán nhãn nhanh (chỉ cần nhấp 1 điểm vào thân cá là tự bắt khung).
4. **Miễn phí & xuất chuẩn YOLO**: Xuất dữ liệu trực tiếp sang định dạng YOLO để đưa thẳng vào huấn luyện YOLOv8.

---

## 🛠️ Quy Trình 5 Bước Thực Hiện Trên CVAT

### Bước 1: Tạo Project trên CVAT & Nạp 20 Nhãn Cá Cảnh
1. Truy cập [https://app.cvat.ai/projects](https://app.cvat.ai/projects) và đăng nhập tài khoản.
2. Bấm nút **+ (Create a new project)**:
   - **Name**: `Fish Aquarium Detection - DH52201621 & DH52201428`
3. Tại mục **Labels**:
   - Chọn tab **Raw** (hoặc Setup manually).
   - Mở file [cvat_labels.json](file:///c:/Users/super/OneDrive/Máy tính/ainhandienca/cvat_labels.json) có sẵn trong thư mục dự án, sao chép toàn bộ nội dung và **dán (Paste)** vào ô.
   - Bấm **Submit** $\rightarrow$ Hệ thống sẽ tự động tạo đủ 20 loài cá cảnh với màu sắc trực quan!
4. Bấm **Submit & Open** để lưu Project.

---

### Bước 2: Đóng Gói Ảnh Cá Bể Kính Để Tải Lên CVAT Task
Trong thư mục dự án `ainhandienca`, chạy lệnh sau để đóng gói ảnh cá đã lọc sạch vào file ZIP:
```powershell
python cvat_helper.py pack --limit-per-species 50 --output dataset_ca_cvat.zip
```
*(Lệnh này chọn lọc 50 ảnh đẹp nhất mỗi loài đang bơi trong bể kính và nén thành `dataset_ca_cvat.zip`)*.

---

### Bước 3: Tạo Task Gán Nhãn Trên CVAT & Nạp Nhãn Tự Động (Pre-annotations)
1. Trong Project vừa tạo, bấm **+ (Create a new task)**.
2. Đặt tên Task: ví dụ `Task_Bể_Kính_Lô_1`.
3. Tại mục **Select files**: Kéo thả file `dataset_ca_cvat.zip` (1,000 ảnh chuẩn đã lọc) vào ô tải lên.
4. Bấm **Submit & Open** $\rightarrow$ CVAT sẽ tải và giải nén ảnh tự động.

> [!TIP]
> **🚀 MẸO TIẾT KIỆM 90% THỜI GIAN - NẠP PRE-ANNOTATIONS CÓ SẴN:**
> Bạn **không cần phải vẽ 1,000 ảnh từ đầu**! Hệ thống đã tạo sẵn file nhãn Bounding Box [cvat_annotations_yolo.zip](file:///c:/Users/super/OneDrive/Máy tính/ainhandienca/cvat_annotations_yolo.zip) chứa sẵn 2,497 khung nhận diện cá.
> - Tại trang Task trên CVAT, bấm menu **... (Actions)** $\rightarrow$ Chọn **Upload annotations**.
> - Chọn định dạng: **YOLO 1.1**.
> - Chọn file [cvat_annotations_yolo.zip](file:///c:/Users/super/OneDrive/Máy tính/ainhandienca/cvat_annotations_yolo.zip) và bấm **OK**.
> - Toàn bộ 1,000 ảnh trên CVAT sẽ tự động xuất hiện Bounding Box và đúng tên loài cá! Bạn chỉ cần vào kiểm tra sơ bộ và bấm Lưu (`Ctrl + S`).

5. Bấm vào **Job #1** để bắt đầu giao diện gán nhãn hoặc hiệu chỉnh.

---

### Bước 4: Thao Tác Gán Nhãn (Bounding Box) Trong Bể Kính
1. **Phím tắt nhanh trên CVAT**:
   - Nhấn phím `N` (hoặc chọn biểu tượng hình chữ nhật bên trái) $\rightarrow$ Chọn tên loài cá tương ứng $\rightarrow$ Kéo chuột vẽ khung bao quanh thân cá.
   - Nhấn phím `F` (hoặc mũi tên phải) để chuyển sang ảnh kế tiếp.
   - Nhấn `Ctrl + S` để lưu tiến trình thường xuyên.
2. **Mẹo gán nhãn cho cá trong hồ cá**:
   - Khung bao sát toàn bộ thân cá bao gồm cả đuôi và vây bơi.
   - Nếu có nhiều cá bơi đè lên nhau, vẽ từng khung riêng cho từng con.
   - Bỏ qua các bóng mờ phản chiếu trên mặt kính hoặc rêu đáy bể.

---

### Bước 5: Xuất Dữ Liệu & Huấn Luyện YOLOv8

#### 1. Xuất dữ liệu từ CVAT:
1. Tại trang Task hoặc Project trên CVAT, bấm vào menu **... (Actions)** $\rightarrow$ chọn **Export dataset**.
2. Chọn định dạng: **YOLO 1.1** (hoặc **YOLO**).
3. Bật tùy chọn **Save images** $\rightarrow$ Bấm **OK** để tải file `.zip` về máy tính (ví dụ: `project_fish-aquarium-yolo_1.1.zip`).

#### 2. Tự động chuyển đổi sang cấu trúc chuẩn YOLOv8:
Chạy script trợ lý [cvat_helper.py](file:///c:/Users/super/OneDrive/M%C3%A1y%20t%C3%ADnh/ainhandienca/cvat_helper.py):
```powershell
python cvat_helper.py convert-yolo --cvat-input "đường_dẫn_file_cvat_export.zip" --output-dir dataset_cvat_yolov8
```
Script sẽ tự động:
- Phân chia `train/` và `val/` theo tỷ lệ 80/20.
- Tạo file `data.yaml` chuẩn cho YOLOv8.

#### 3. Bắt đầu huấn luyện mô hình:
- **Cách A: Huấn luyện trên Google Colab (GPU T4 miễn phí)**:
  Mở notebook [Fish_YOLOv8_Training_Google_Colab.ipynb](file:///c:/Users/super/OneDrive/M%C3%A1y%20t%C3%ADnh/ainhandienca/notebooks/Fish_YOLOv8_Training_Google_Colab.ipynb) trên Colab, tải thư mục hoặc zip lên và chạy:
  ```bash
  !yolo detect train data=data.yaml model=yolov8n.pt epochs=50 imgsz=640 batch=16 device=0 optimizer=AdamW
  ```
- **Cách B: Huấn luyện trực tiếp trên máy cục bộ**:
  ```powershell
  yolo detect train data=dataset_cvat_yolov8/data.yaml model=yolov8n.pt epochs=50 imgsz=640 batch=16
  ```

---

## 📋 Danh Mục Nhãn Nhanh (Copy & Paste)

Nếu bạn muốn nhập nhãn thủ công hoặc copy danh sách, copy đoạn text bên dưới:
```text
ca_ba_duoi
ca_bay_mau
ca_but_chi
ca_chuot
ca_da_quang
ca_dia
ca_diec_anh_dao
ca_duoi_kiem
ca_hong_ket
ca_koi
ca_la_han
ca_lau_kieng
ca_molly
ca_mun
ca_neon
ca_rong
ca_sac
ca_soc_ngua
ca_thien_than
ca_xiem
```
Hoặc dùng trực tiếp file JSON cấu hình đầy đủ mã màu tại: [cvat_labels.json](file:///c:/Users/super/OneDrive/Máy tính/ainhandienca/cvat_labels.json).
