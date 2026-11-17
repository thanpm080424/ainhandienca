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

### Bước 3: Tạo Task Gán Nhãn Trên CVAT

#### GIAI ĐOẠN 1: THỬ NGHIỆM PILOT (20 ẢNH - KHUYÊN DÙNG ĐẦU TIÊN)
Để tránh mất thời gian và bảo toàn dataset, hệ thống đã tạo sẵn file ZIP pilot nhẹ (4.5 MB): [`dataset_ca_pilot.zip`](file:///c:/Users/super/OneDrive/Máy tính/ainhandienca/dataset_ca_pilot.zip) gồm đúng 20 ảnh (mỗi loài 1 ảnh đại diện):
1. Trong Project `Fish Detection` trên CVAT, bấm nút **+ (Create a new task)**.
2. Đặt tên Task: `Fish_Pilot_20`.
3. Tại ô **Select files**: Kéo thả duy nhất file [`dataset_ca_pilot.zip`](file:///c:/Users/super/OneDrive/Máy tính/ainhandienca/dataset_ca_pilot.zip) vào $\rightarrow$ Bấm **Submit & Open**.
4. Gán nhãn thủ công 20 ảnh (mất ~3–5 phút).
5. Xuất nhãn: Menu **Actions (...)** $\rightarrow$ **Export dataset** $\rightarrow$ chọn **YOLO 1.1** (tải về ví dụ: `cvat_pilot_export.zip`).
6. Chuyển đổi thử nghiệm vào thư mục riêng biệt **`dataset_yolo_pilot`** (tuyệt đối không trộn vào `dataset_yolo_detection`):
   ```powershell
   python cvat_helper.py convert-yolo --cvat-input "cvat_pilot_export.zip" --output-dir dataset_yolo_pilot
   ```
7. Trực quan hóa ảnh montage pilot để kiểm tra chất lượng nhãn người gán:
   ```powershell
   python visualize_yolo_labels.py --dataset-dir dataset_yolo_pilot --preview-dir preview_pilot
   ```
> [!IMPORTANT]
> **KHÔNG chạy huấn luyện trên tập Pilot**. Tập pilot chỉ nhằm kiểm định độ trơn tru của quy trình xuất/nhập, format nhãn và tool trực quan.

---

#### GIAI ĐOẠN 2: GÁN NHÃN TOÀN BỘ 1,000 ẢNH (KHI PILOT ĐÃ ĐẠT)
1. Tạo Task chính: `Fish_Aquarium_1000`.
2. Tải duy nhất file [`dataset_ca_cvat.zip`](file:///c:/Users/super/OneDrive/Máy tính/ainhandienca/dataset_ca_cvat.zip) (1,000 ảnh).
3. Sau khi gán nhãn toàn bộ, xuất `YOLO 1.1` và chuyển đổi vào thư mục sạch:
   ```powershell
   python cvat_helper.py convert-yolo --cvat-input "cvat_full_export.zip" --output-dir dataset_yolo_detection
   ```

> [!WARNING]
> **⚠️ TUYỆT ĐỐI KHÔNG UPLOAD `cvat_annotations_yolo.zip`:**
> - File `dataset_ca_cvat.zip` và `dataset_ca_pilot.zip` chứa ảnh sạch chưa có nhãn.
> - Không nạp file `cvat_annotations_yolo.zip` vì đó là nhãn máy tự động chưa được con người thẩm định, sẽ đưa các box lỗi/rác vào task và ghi đè mất các nhãn đang gán trên CVAT (theo [tài liệu Import Datasets của CVAT](https://docs.cvat.ai/docs/dataset_management/import-datasets/)).

5. Bấm vào **Job #1** để bắt đầu giao diện gán nhãn.

---

### Bước 4: Thao Tác Gán Nhãn Chuẩn Xác Trong Bể Kính
1. **Quy trình gán nhãn thủ công (Khuyên dùng cho nhóm thử nghiệm ban đầu)**:
   - Nhấn phím `N` (hoặc chọn biểu tượng hình chữ nhật **Draw new rectangle**) $\rightarrow$ Chọn tên loài cá tương ứng $\rightarrow$ Kéo chuột vẽ khung bao quanh thân cá.
   - Khung bao sát toàn bộ thân cá bao gồm đầu, thân, vây và đuôi.
   - Bỏ qua các vệt sáng phản xạ trên kính, rêu bể hoặc bóng cây thủy sinh.
   - Nhấn phím `F` (hoặc mũi tên phải) để sang ảnh kế tiếp.
   - Nhấn `Ctrl + S` thường xuyên để lưu tiến trình.
2. **Lưu ý về AI Tools trong CVAT**:
   - Theo [tài liệu AI Tools của CVAT](https://docs.cvat.ai/docs/annotation/tools/ai-tools/), các công cụ như AI Interactor / SAM cần model backend tương ứng và chỉ hỗ trợ tạo phân đoạn theo điểm nhấp; chúng không tự động xác định đúng loài cá trong 20 loài. Người gán nhãn vẫn cần chọn đúng nhãn loài và kiểm tra ranh giới box.
3. **Chiến lược thực hiện**:
   - Gán nhãn thủ công một nhóm nhỏ trước (pilot batch, ví dụ 10–20 ảnh đầu) để kiểm tra quy trình xuất/nhập và huấn luyện thử nghiệm, sau đó mới tiến hành cho toàn bộ.

---

### Bước 5: Xuất Dữ Liệu & Huấn Luyện YOLOv8

#### 1. Xuất dữ liệu từ CVAT:
1. Tại trang Task hoặc Project trên CVAT, bấm vào menu **... (Actions)** $\rightarrow$ chọn **Export dataset**.
2. Chọn định dạng: **YOLO 1.1** (hoặc **YOLO**).
3. Bật tùy chọn **Save images** $\rightarrow$ Bấm **OK** để tải file `.zip` về máy tính (ví dụ: `project_fish-aquarium-yolo_1.1.zip`).

#### 2. Tự động chuyển đổi sang cấu trúc chuẩn YOLOv8 (80 Train / 10 Val / 10 Test):
Chạy script trợ lý [cvat_helper.py](file:///c:/Users/super/OneDrive/M%C3%A1y%20t%C3%ADnh/ainhandienca/cvat_helper.py):
```powershell
python cvat_helper.py convert-yolo --cvat-input "đường_dẫn_file_cvat_export.zip" --output-dir dataset_yolo_detection
```
Script sẽ tự động:
- Phân chia `train/` (80%), `val/` (10%) và `test/` (10%) độc lập chuẩn hóa.
- Tạo file `data.yaml` với đường dẫn tương đối chuẩn cho cả máy cục bộ và Colab.
- Tạo lại ảnh trực quan montage để kiểm tra nhanh:
  ```powershell
  python visualize_yolo_labels.py
  ```

#### 3. Bắt đầu huấn luyện mô hình YOLOv8 Detection:
- **Cách A: Huấn luyện trên máy cục bộ với GPU NVIDIA RTX 3050 Laptop (4GB VRAM)**:
  ```powershell
  python train_yolo_detection.py --device 0 --batch -1 --epochs 30 --imgsz 640
  ```
  *(Chế độ `--batch -1` kích hoạt AutoBatch tự động đo VRAM để tránh CUDA Out-Of-Memory)*.
- **Cách B: Huấn luyện trên Google Colab (GPU T4 miễn phí)**:
  Mở notebook [Fish_YOLOv8_Training_Google_Colab.ipynb](file:///c:/Users/super/OneDrive/M%C3%A1y%20t%C3%ADnh/ainhandienca/notebooks/Fish_YOLOv8_Training_Google_Colab.ipynb) trên Colab, tải `dataset_yolo_detection.zip` lên và chạy:
  ```bash
  !unzip -q dataset_yolo_detection.zip
  !yolo detect train data=dataset_yolo_detection/data.yaml model=yolov8n.pt epochs=30 imgsz=640 batch=-1 device=0 optimizer=AdamW
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
