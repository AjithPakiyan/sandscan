#include "esp_camera.h"
#include <WiFi.h>
#include <HTTPClient.h>
#include <TinyGPSPlus.h>

// ================= WIFI =================
const char* ssid = "Realme";
const char* password = "12345678";

// CHANGE THIS to your PC IP
String serverName = "http://10.77.78.38:5000/upload";   //IP will change as it is dynamic IP

// ================= GPS =================
TinyGPSPlus gps;
HardwareSerial gpsSerial(1);

// ================= CAMERA PINS =================
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM       5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

void startCamera() {
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;

  config.frame_size = FRAMESIZE_VGA;
  config.jpeg_quality = 10;
  config.fb_count = 1;

  esp_camera_init(&config);
}

void setup() {
  Serial.begin(115200);

  gpsSerial.begin(9600, SERIAL_8N1, 15, 13);

  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
  }

  startCamera();
}

void loop() {
   // Read GPS data (if available)
  while (gpsSerial.available()) {
    gps.encode(gpsSerial.read());
  }

  float lat = 0.0;
  float lon = 0.0;

  if (gps.location.isValid()) {
    lat = gps.location.lat();
    lon = gps.location.lng();
    Serial.print("📍 GPS FIX: ");
  } else {
    Serial.println("⚠️ GPS NOT FIXED — sending image anyway");
  }

  Serial.print(lat, 6);
  Serial.print(", ");
  Serial.println(lon, 6);

  // Capture image
  camera_fb_t * fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("❌ Camera capture failed");
    delay(2000);
    return;
  }

  // Send to PC
  HTTPClient http;
  http.begin(serverName);
  http.addHeader("Content-Type", "application/octet-stream");
  http.addHeader("Latitude", String(lat, 6));
  http.addHeader("Longitude", String(lon, 6));

  int httpResponseCode = http.POST(fb->buf, fb->len);

  Serial.print("📡 HTTP response: ");
  Serial.println(httpResponseCode);

  http.end();
  esp_camera_fb_return(fb);

  delay(10000);   // capture every 10 sec
}
