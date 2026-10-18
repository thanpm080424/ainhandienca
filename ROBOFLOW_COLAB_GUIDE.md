# 🚀 Hướng Dẫn Tích Hợp Roboflow & Google Colab Huấn Luyện AI Nhận Diện Cá Cảnh

**Đồ án tốt nghiệp:** Hệ Thống IoT AI Nhận Diện Cá & Giám Sát Môi Trường Hồ Thủy Sinh  
**Sinh viên thực hiện:**
- **Lê Quốc Trí** - MSSV: DH52201621
- **Phạm Minh Thân** - MSSV: DH52201428

---

## 🎯 Tổng Quan Kiến Trúc

Khi nhận diện cá **trực tiếp trong bể kính hồ cá**, có 2 bài toán chính:
1. **Phân loại ảnh (Classification - YOLOv8-cls)**: Phân loại toàn bộ bức ảnh cá chụp từ camera hồ thành 1 trong 20 loài cá cảnh.
2. **Khoanh vùng phát hiện đối tượng (Object Detection - YOLOv8-det)**: Vẽ Bounding Box xung quanh **từng con cá đang bơi** trong bể kính (phát hiện nhiều cá khác loài cùng bơi trong hồ thủy sinh).

**Roboflow** và **Google Colab** đóng vai trò hoàn hảo cho đồ án:
- **Roboflow**: Nền tảng quản lý dataset, hỗ trợ gán nhãn Bounding Box tự động (Smart Polygon / Auto-label) và xuất chuẩn `YOLOv8`.
- **Google Colab**: Cung cấp phần cứng GPU T4/A100 miễn phí để huấn luyện mô hình trong 15-25 phút thay vì mất nhiều giờ trên máy tính cá nhân.

---

## 🛠️ PHẦN 1: Hướng Dẫn Sử Dụng Roboflow

### Bước 1: Đóng gói ảnh từ dataset cục bộ
Chạy script trợ lý có sẵn trong dự án:
```powershell
python roboflow_helper.py pack --limit-per-species 50 --output dataset_ca_roboflow.zip
```
Lệnh này sẽ tự động trích xuất các ảnh đẹp nhất của từng loài cá đang bơi trong bể kính và nén thành file `dataset_ca_roboflow.zip`.

### Bước 2: Tạo Project trên Roboflow
1. Truy cập [https://app.roboflow.com](https://app.roboflow.com) và đăng nhập (bằng Google / GitHub).
2. Bấm **Create New Project**:
   - **Project Name**: `fish-aquarium-detection`
   - **Project Type**: Chọn **Object Detection** (Khoanh vùng cá trong hồ) hoặc **Classification** (Phân loại ảnh).
   - **What are you detecting?**: `fish`
3. Kéo thả file `dataset_ca_roboflow.zip` vào giao diện tải lên.
4. Bấm **Save and Continue** để hoàn tất việc tải ảnh lên.

### Bước 3: Gán nhãn (Annotate Bounding Box)
- Sử dụng tính năng **Label Assist (Auto-label)** của Roboflow để AI tự động vẽ khung quanh các con cá đang bơi trong bể kính.
- Gán nhãn theo đúng mã loài tương ứng (ví dụ: `ca_bay_mau`, `ca_dia`, `ca_la_han`, `ca_neon`...).

### Bước 4: Tạo Version & Lấy API Key
1. Bấm vào tab **Generate** $\rightarrow$ chọn các tùy chọn Augmentation (tăng cường xoay nhẹ, lật ảnh, độ sáng mô phỏng nước).
2. Bấm **Generate Version**.
3. Bấm **Export Dataset** $\rightarrow$ chọn định dạng **YOLOv8** $\rightarrow$ chọn **Show Download Code**.
4. Bạn sẽ nhận được đoạn mã dạng:
```python
from roboflow import Roboflow
rf = Roboflow(api_key="ROBOFLOW_API_KEY_CUA_BAN")
project = rf.workspace("workspace-name").project("fish-aquarium-detection")
version = project.version(1)
dataset = version.download("yolov8")
```

---

## ⚡ PHẦN 2: Huấn Luyện Trên Google Colab (GPU Miễn Phí)

Dự án đã tích hợp sẵn Jupyter Notebook chuẩn Google Colab tại:
👉 `notebooks/Fish_YOLOv8_Training_Google_Colab.ipynb`

### Cách mở trên Google Colab:
1. Truy cập [Google Colab](https://colab.research.google.com/).
2. Bấm vào tab **Upload** $\rightarrow$ Chọn file `notebooks/Fish_YOLOv8_Training_Google_Colab.ipynb` từ máy tính của bạn.
3. Vào menu **Runtime** $\rightarrow$ **Change runtime type** $\rightarrow$ Chọn **T4 GPU** $\rightarrow$ Bấm **Save**.

### Các bước chạy trên Colab (đã tự động hóa trong Notebook):
1. **Kiểm tra GPU**: `!nvidia-smi` để xác nhận GPU T4 đã kích hoạt.
2. **Cài đặt Ultralytics & Roboflow**: `!pip install ultralytics roboflow`
3. **Nạp Dataset**:
   - Dán đoạn mã Roboflow API từ Bước 4 ở trên vào Cell 3A.
   - Hoặc clone trực tiếp từ GitHub repo: `!git clone https://github.com/thanpm080424/ainhandienca.git`
4. **Bắt đầu huấn luyện**:
   - Nếu huấn luyện **Phân loại 20 loài**:
     ```bash
     !python train_fish_classifier.py --epochs 50 --batch 32 --device 0
     ```
   - Nếu huấn luyện **Khoanh vùng cá bơi trong bể (Object Detection)**:
     ```bash
     !yolo detect train data=data.yaml model=yolov8n.pt epochs=50 imgsz=640 batch=16 device=0 optimizer=AdamW
     ```
5. **Đánh giá kết quả**: Colab sẽ vẽ biểu đồ Loss, Accuracy, Confusion Matrix trực tiếp.
6. **Tải file trọng số về**: Chạy cell cuối cùng, Colab sẽ tự động tải file `best_fish_yolov8.pt` về máy tính của bạn!

---

## 🔌 PHẦN 3: Đưa Trọng Số Mới Vào Hệ Thống IoT Hồ Cá

Sau khi tải file `best_fish_yolov8.pt` từ Google Colab về:
1. Chép đè file vào thư mục dự án: `c:\Users\super\OneDrive\Máy tính\ainhandienca\weights\best_fish_yolov8.pt`
2. Khởi động lại ứng dụng Flask:
   ```powershell
   python app.py
   ```
3. Truy cập vào trang web `http://127.0.0.1:5000/iot`:
   - Gửi ảnh chụp từ camera hồ cá lên để kiểm tra độ chính xác.
   - Cảm biến nhiệt độ / pH sẽ đối chiếu trực tiếp với loài cá vừa được nhận diện để đưa ra cảnh báo thời gian thực!
