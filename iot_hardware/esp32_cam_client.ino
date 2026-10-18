/*
 * Client ESP32-CAM AI-Thinker cho endpoint Flask /api/iot/predict.
 * Đồ án: Lê Quốc Trí (DH52201621) và Phạm Minh Thân (DH52201428).
 *
 * Gửi ảnh multipart với tên field "file". Nhiệt độ DS18B20 được dùng cục bộ
 * để điều khiển relay theo temp_range từ API; route hiện tại nhận file ảnh,
 * nhưng bỏ qua các field cảm biến gửi kèm.
 */

#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include "esp_camera.h"
#include "esp_heap_caps.h"
#include <OneWire.h>
#include <DallasTemperature.h>

// Sửa các giá trị cấu hình trước khi nạp firmware.
static const char *WIFI_SSID = "YOUR_WIFI_SSID";
static const char *WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
static const char *SERVER_URL = "http://192.168.1.100:5000/api/iot/predict";
static const char *DEVICE_ID = "esp32-cam-aquarium-01";

// Pinout AI-Thinker; cần tắt/không dùng khe microSD khi sử dụng GPIO13/14.
constexpr int FLASH_LED_PIN = 4;
constexpr int ONE_WIRE_PIN = 13;
constexpr int FAN_RELAY_PIN = 14;
constexpr int HEATER_RELAY_PIN = 15; // Chân strap: dùng module relay đầu vào trở kháng cao.
constexpr bool RELAY_ACTIVE_LOW = true;
constexpr uint32_t CAPTURE_INTERVAL_MS = 30000;
constexpr uint32_t WIFI_CONNECT_TIMEOUT_MS = 20000;

OneWire oneWire(ONE_WIRE_PIN);
DallasTemperature waterTemperature(&oneWire);
uint32_t lastCaptureMs = 0;

// Camera OV2640 trên module ESP32-CAM AI-Thinker.
bool initializeCamera() {
  camera_config_t config{};
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = 5;
  config.pin_d1 = 18;
  config.pin_d2 = 19;
  config.pin_d3 = 21;
  config.pin_d4 = 36;
  config.pin_d5 = 39;
  config.pin_d6 = 34;
  config.pin_d7 = 35;
  config.pin_xclk = 0;
  config.pin_pclk = 22;
  config.pin_vsync = 25;
  config.pin_href = 23;
  config.pin_sccb_sda = 26;
  config.pin_sccb_scl = 27;
  config.pin_pwdn = 32;
  config.pin_reset = -1;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  config.frame_size = FRAMESIZE_VGA;
  config.jpeg_quality = 12;
  config.fb_count = psramFound() ? 2 : 1;
  config.grab_mode = CAMERA_GRAB_LATEST;
  config.fb_location = psramFound() ? CAMERA_FB_IN_PSRAM : CAMERA_FB_IN_DRAM;

  const esp_err_t result = esp_camera_init(&config);
  if (result != ESP_OK) {
    Serial.printf("Khởi tạo camera lỗi: 0x%x\n", result);
    return false;
  }
  return true;
}

void setRelay(int pin, bool enabled) {
  const uint8_t onLevel = RELAY_ACTIVE_LOW ? LOW : HIGH;
  digitalWrite(pin, enabled ? onLevel : (onLevel == HIGH ? LOW : HIGH));
}

void relaysOff() {
  setRelay(FAN_RELAY_PIN, false);
  setRelay(HEATER_RELAY_PIN, false);
}

bool connectWiFi() {
  if (WiFi.status() == WL_CONNECTED) return true;
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("Đang kết nối Wi-Fi");
  const uint32_t started = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - started < WIFI_CONNECT_TIMEOUT_MS) {
    delay(400);
    Serial.print('.');
  }
  Serial.println();
  if (WiFi.status() == WL_CONNECTED) {
    Serial.print("Wi-Fi đã kết nối, IP: ");
    Serial.println(WiFi.localIP());
    return true;
  }
  Serial.println("Không kết nối được Wi-Fi.");
  return false;
}

float readWaterTemperature() {
  waterTemperature.requestTemperatures();
  const float value = waterTemperature.getTempCByIndex(0);
  if (value == DEVICE_DISCONNECTED_C || isnan(value) || value < -20.0f || value > 80.0f) {
    return NAN;
  }
  return value;
}

void regulateTemperature(float actual, float minTemp, float maxTemp) {
  if (isnan(actual) || minTemp >= maxTemp) {
    relaysOff(); // Không tự bật thiết bị nếu cảm biến hoặc phản hồi ngưỡng lỗi.
    Serial.println("Không có số đo/ngưỡng nhiệt hợp lệ; relay được tắt.");
    return;
  }
  const bool heaterOn = actual < minTemp;
  const bool fanOn = actual > maxTemp;
  setRelay(HEATER_RELAY_PIN, heaterOn);
  setRelay(FAN_RELAY_PIN, fanOn);
  Serial.printf("Nhiệt độ %.2f C; ngưỡng %.1f–%.1f C; sưởi=%s, quạt=%s\n",
                actual, minTemp, maxTemp, heaterOn ? "BẬT" : "TẮT", fanOn ? "BẬT" : "TẮT");
}

// Gửi multipart/form-data mà không ghép ảnh nhị phân vào Arduino String.
bool postCapture(camera_fb_t *frame, float actualTemp) {
  if (frame == nullptr || frame->buf == nullptr || frame->len == 0) return false;
  const String boundary = "----FishIoTBoundary7MA4YWxkTrZu0gW";
  String prefix;
  prefix.reserve(320);
  prefix += "--" + boundary + "\r\n";
  prefix += "Content-Disposition: form-data; name=\"device_id\"\r\n\r\n";
  prefix += DEVICE_ID;
  prefix += "\r\n--" + boundary + "\r\n";
  prefix += "Content-Disposition: form-data; name=\"temp_actual\"\r\n\r\n";
  prefix += isnan(actualTemp) ? "" : String(actualTemp, 2);
  prefix += "\r\n--" + boundary + "\r\n";
  prefix += "Content-Disposition: form-data; name=\"file\"; filename=\"capture.jpg\"\r\n";
  prefix += "Content-Type: image/jpeg\r\n\r\n";
  const String suffix = "\r\n--" + boundary + "--\r\n";
  const size_t bodyLength = prefix.length() + frame->len + suffix.length();

  uint8_t *body = nullptr;
  if (psramFound()) body = static_cast<uint8_t *>(heap_caps_malloc(bodyLength, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT));
  if (body == nullptr) body = static_cast<uint8_t *>(malloc(bodyLength));
  if (body == nullptr) {
    Serial.printf("Không đủ bộ nhớ cho multipart (%u byte).\n", static_cast<unsigned>(bodyLength));
    return false;
  }
  size_t offset = 0;
  memcpy(body + offset, prefix.c_str(), prefix.length()); offset += prefix.length();
  memcpy(body + offset, frame->buf, frame->len); offset += frame->len;
  memcpy(body + offset, suffix.c_str(), suffix.length());

  HTTPClient http;
  http.setTimeout(20000);
  http.setReuse(false);
  if (!http.begin(SERVER_URL)) {
    free(body);
    Serial.println("URL Flask không hợp lệ.");
    return false;
  }
  http.addHeader("Content-Type", "multipart/form-data; boundary=" + boundary);
  http.addHeader("Connection", "close");
  const int status = http.sendRequest("POST", body, bodyLength);
  free(body);

  if (status < 200 || status >= 300) {
    Serial.printf("Server trả HTTP %d: %s\n", status, http.getString().c_str());
    http.end();
    relaysOff();
    return false;
  }
  const String response = http.getString();
  http.end();

#if ARDUINOJSON_VERSION_MAJOR >= 7
  JsonDocument doc;
#else
  DynamicJsonDocument doc(8192);
#endif
  const DeserializationError error = deserializeJson(doc, response);
  if (error) {
    Serial.printf("JSON phản hồi không hợp lệ: %s\n", error.c_str());
    relaysOff();
    return false;
  }
  if (!doc["success"].as<bool>()) {
    Serial.printf("API báo lỗi: %s\n", doc["error"] | "không rõ lỗi");
    relaysOff();
    return false;
  }

  const char *species = doc["detection"]["species_name"] | "Không xác định";
  const float confidence = doc["detection"]["confidence"] | 0.0f;
  const char *optimalTemp = doc["aquatic_environment"]["optimal_temperature"] | "N/A";
  const char *optimalPh = doc["aquatic_environment"]["optimal_ph"] | "N/A";
  const char *tempAlert = doc["iot_sensor_thresholds"]["temp_alert"] | "N/A";
  const bool hybridAlert = doc["hybrid_analysis"]["is_hybrid_alert"] | false;
  const float minTemp = doc["aquatic_environment"]["temp_range"]["min"] | NAN;
  const float maxTemp = doc["aquatic_environment"]["temp_range"]["max"] | NAN;

  Serial.println("\n--- KẾT QUẢ NHẬN DIỆN ---");
  Serial.printf("Loài: %s | Tin cậy: %.1f%%\n", species, confidence);
  Serial.printf("Nhiệt độ tối ưu: %s | pH tối ưu: %s | Cảnh báo nhiệt: %s\n", optimalTemp, optimalPh, tempAlert);
  Serial.printf("Cảnh báo lai tạp: %s\n", hybridAlert ? "CÓ" : "Không");
  regulateTemperature(actualTemp, minTemp, maxTemp);
  return true;
}

void captureAndSend() {
  if (!connectWiFi()) {
    relaysOff();
    return;
  }
  const float actualTemp = readWaterTemperature();
  digitalWrite(FLASH_LED_PIN, HIGH);
  delay(150);
  camera_fb_t *frame = esp_camera_fb_get();
  digitalWrite(FLASH_LED_PIN, LOW);
  if (frame == nullptr) {
    Serial.println("Không chụp được ảnh từ OV2640.");
    relaysOff();
    return;
  }
  Serial.printf("Đã chụp JPEG: %u byte\n", static_cast<unsigned>(frame->len));
  const bool sent = postCapture(frame, actualTemp);
  esp_camera_fb_return(frame);
  if (!sent) Serial.println("Gửi ảnh thất bại; thiết bị gia nhiệt/làm mát được tắt.");
}

void setup() {
  Serial.begin(115200);
  pinMode(FLASH_LED_PIN, OUTPUT);
  digitalWrite(FLASH_LED_PIN, LOW);
  pinMode(FAN_RELAY_PIN, OUTPUT);
  pinMode(HEATER_RELAY_PIN, OUTPUT);
  relaysOff();
  waterTemperature.begin();
  if (!initializeCamera()) {
    Serial.println("Dừng vì camera không khởi tạo được.");
    while (true) { relaysOff(); delay(1000); }
  }
  connectWiFi();
  captureAndSend();
  lastCaptureMs = millis();
}

void loop() {
  if (millis() - lastCaptureMs >= CAPTURE_INTERVAL_MS) {
    lastCaptureMs = millis();
    captureAndSend();
  }
  delay(50);
}
