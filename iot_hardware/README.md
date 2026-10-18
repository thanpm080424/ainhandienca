# Client phần cứng IoT cho hệ thống nhận diện cá

Tác giả đồ án: **Lê Quốc Trí (DH52201621)** và **Phạm Minh Thân (DH52201428)**.

Thư mục gồm firmware ESP32-CAM AI-Thinker và client Raspberry Pi. Cả hai gửi ảnh JPEG dạng `multipart/form-data`, tên trường ảnh là **`file`**, tới `POST /api/iot/predict`.

## 1. ESP32-CAM AI-Thinker

### Nối dây

| Thiết bị | Chân ESP32-CAM | Ghi chú |
| --- | --- | --- |
| OV2640 | Camera connector trên board | Firmware dùng pin map AI-Thinker, JPEG VGA 640×480. |
| LED flash | GPIO 4 | Firmware bật trong lúc chụp. Không gắn microSD khi dùng GPIO13/14. |
| DS18B20 DATA | GPIO 13 | Điện trở kéo lên 4.7 kΩ giữa DATA và 3.3 V. |
| Relay quạt | GPIO 14 | Chỉ điều khiển ngõ IN của module/driver, không nối tải trực tiếp vào GPIO. |
| Relay sưởi | GPIO 15 | Chân strap; dùng driver/relay có ngõ vào trở kháng cao, giữ trạng thái relay tắt trong reset. Kiểm tra khởi động board trước khi gắn tải. |
| DS18B20 VDD/GND | 3.3 V/GND | Chế độ 3 dây; dùng chung GND tín hiệu với ESP32. |
| Module relay | Nguồn riêng theo định mức module | Tách nguồn tải quạt/sưởi; dùng cầu chì và thiết bị đóng cắt đúng điện áp/dòng định mức. Không cấp tải từ GPIO hoặc chân 3.3 V. |

Board ESP32-CAM có rất ít GPIO trống. Thiết kế dùng GPIO13/14 nên không dùng microSD. GPIO15 là chân cấu hình lúc boot; cần relay driver không kéo sai mức khi reset. Firmware dùng relay active-low; đổi `RELAY_ACTIVE_LOW` nếu module relay của bạn active-high. Relay được tắt khi cảm biến/ngưỡng/API lỗi.

### Cài đặt và nạp

1. Trong Arduino IDE cài ESP32 board package; chọn **AI Thinker ESP32-CAM** và bật PSRAM nếu tùy chọn có sẵn.
2. Qua Library Manager cài **ArduinoJson** (v6 hoặc v7), **OneWire** và **DallasTemperature**.
3. Mở `esp32_cam_client.ino`, sửa `WIFI_SSID`, `WIFI_PASSWORD`, `SERVER_URL` và `DEVICE_ID`.
4. Nạp bằng USB-to-TTL 3.3 V: TX↔U0R, RX↔U0T, GND↔GND; giữ GPIO0 nối GND khi nạp, sau đó tháo GPIO0 khỏi GND và reset để chạy.
5. Mở Serial Monitor ở 115200 baud. Firmware chụp và gửi ảnh mỗi 30 giây.

Đặt `SERVER_URL` thành địa chỉ LAN của máy chạy Flask, ví dụ `http://192.168.1.20:5000/api/iot/predict`; không dùng `127.0.0.1` vì đó là loopback của thiết bị. `app.py` mặc định chỉ lắng nghe loopback; chạy server với `FLASK_HOST=0.0.0.0` để cho phép thiết bị trong LAN kết nối (PowerShell: `$env:FLASK_HOST="0.0.0.0"; python app.py`; Linux/macOS: `FLASK_HOST=0.0.0.0 python app.py`). Debug mặc định tắt; chỉ bật `FLASK_DEBUG=1` khi phát triển trên máy tin cậy.

Firmware đọc `detection.species_name`, `detection.confidence`, `aquatic_environment.optimal_temperature`, `aquatic_environment.optimal_ph`, `iot_sensor_thresholds.temp_alert`, `hybrid_analysis.is_hybrid_alert` và `aquatic_environment.temp_range`. DS18B20 được so sánh với min/max số của `temp_range` để bật quạt/sưởi cục bộ. Firmware gửi `temperature` và `device_id` kèm multipart; Flask lưu các trường này trong lịch sử.

## 2. Raspberry Pi

### Nối dây cảm biến

| DS18B20 | Raspberry Pi |
| --- | --- |
| VDD (đỏ) | 3.3 V, pin vật lý 1 |
| GND (đen) | GND, pin vật lý 6 |
| DATA (vàng) | GPIO4 / pin vật lý 7 |

Đặt điện trở 4.7 kΩ giữa DATA và 3.3 V. Không cấp DS18B20 bằng 5 V khi DATA nối trực tiếp GPIO. Kích hoạt giao tiếp 1-Wire trong `raspi-config` (Interface Options → 1-Wire), rồi khởi động lại. Nếu có nhiều cảm biến, lấy ID bằng `ls /sys/bus/w1/devices/` và truyền `--sensor-id 28-...`.

Camera CSI nối qua cáp ribbon vào cổng camera của Pi; dùng Picamera2. Với webcam USB, cài OpenCV và dùng `--camera-index 0`.

Đầu ra cảm biến pH analog không nối trực tiếp vào GPIO vì Pi không có ADC. Client nhận pH đã đo/hiệu chuẩn qua `--ph-actual` hoặc biến môi trường `FISH_PH_ACTUAL`; nếu dùng module pH analog, cần ADC (ví dụ ADS1115) và hiệu chuẩn bằng dung dịch đệm trước khi đưa giá trị vào client.

### Cài và chạy

```bash
sudo apt update
sudo apt install -y python3-requests python3-picamera2
python3 -m pip install -r requirements-pi.txt
```

Trên Raspberry Pi OS mới, Picamera2 nên được cài bằng `apt`. Nếu môi trường Python được quản lý bởi OS và `pip` từ chối cài gói, tạo virtualenv có quyền truy cập system packages hoặc cài OpenCV qua apt.

```bash
export FISH_SERVER_URL="http://192.168.1.20:5000"
python3 pi_sensor_client.py --keep-image
python3 pi_sensor_client.py --server http://192.168.1.20:5000 --ph-actual 7.1 --loop --interval 60
```

Client đọc DS18B20, chụp ảnh, gửi trường ảnh `file` cùng `device_id`, `temperature` và `ph` nếu có. Nó in kết quả nhận diện, khoảng nhiệt độ/pH phù hợp, số đo thực tế và cảnh báo lai tạp. Flask lưu mẫu vào `data/history.db` khi có telemetry; nếu chỉ gửi ảnh không kèm các field telemetry thì endpoint không thêm bản ghi lịch sử.

## 3. Xử lý sự cố nhanh

- **Không kết nối được server:** kiểm tra Pi/ESP32 và máy Flask cùng LAN, firewall cho phép cổng 5000 và chạy app với `FLASK_HOST=0.0.0.0`; chỉ dùng trong mạng tin cậy.
- **Không thấy DS18B20:** kiểm tra pull-up 4.7 kΩ, bật 1-Wire và xem thư mục ID `28-*`.
- **ESP32 khởi động lại khi gắn relay:** kiểm tra GPIO15 không bị module kéo mức sai trong boot; giữ microSD rút ra khi dùng GPIO13/14.
- **API trả lỗi JSON:** xem nội dung lỗi được in trên Serial/terminal; kiểm tra endpoint và model/server Flask đang chạy.
