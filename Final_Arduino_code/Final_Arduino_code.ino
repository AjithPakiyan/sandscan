#include "esp_camera.h"
#include <WiFi.h>
#include <HTTPClient.h>
#include <HardwareSerial.h>
#include <TinyGPS++.h>

// ================= WIFI =================
const char* ssid = "Realme";
const char* password = "12345678";
String serverName = "http://10.77.78.38:5000/upload";

// ================= GPS =================
TinyGPSPlus gps;
HardwareSerial gpsSerial(2);  // UART2 — RX=14, TX=15

// ================= BUTTON =================
#define BUTTON_PIN 12
bool imageSent = false;

// ================= CAMERA PINS (AI Thinker) =================
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
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

void startCamera() {
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer   = LEDC_TIMER_0;
  config.pin_d0       = Y2_GPIO_NUM;
  config.pin_d1       = Y3_GPIO_NUM;
  config.pin_d2       = Y4_GPIO_NUM;
  config.pin_d3       = Y5_GPIO_NUM;
  config.pin_d4       = Y6_GPIO_NUM;
  config.pin_d5       = Y7_GPIO_NUM;
  config.pin_d6       = Y8_GPIO_NUM;
  config.pin_d7       = Y9_GPIO_NUM;
  config.pin_xclk     = XCLK_GPIO_NUM;
  config.pin_pclk     = PCLK_GPIO_NUM;
  config.pin_vsync    = VSYNC_GPIO_NUM;
  config.pin_href     = HREF_GPIO_NUM;
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn     = PWDN_GPIO_NUM;
  config.pin_reset    = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  config.frame_size   = FRAMESIZE_VGA;
  config.jpeg_quality = 12;
  config.fb_count     = 1;
  if (esp_camera_init(&config) != ESP_OK) {
    Serial.println("Camera init failed");
    return;
  }
  Serial.println("Camera ready");
}

void setup() {
  Serial.begin(115200);
  pinMode(BUTTON_PIN, INPUT_PULLUP);

  // GPS
  gpsSerial.begin(9600, SERIAL_8N1, 14, 15);
  Serial.println("Waiting for GPS fix...");

  // WiFi
  WiFi.begin(ssid, password);
  Serial.print("Connecting WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
    while (gpsSerial.available() > 0)
      gps.encode(gpsSerial.read());
  }
  Serial.println("\nWiFi connected");

  startCamera();
  Serial.println("=== System Ready ===");
}

void loop() {

  // ========== Always read GPS ==========
  while (gpsSerial.available() > 0) {
    gps.encode(gpsSerial.read());
  }

  // ========== GPS status every 2 seconds ==========
  static unsigned long lastPrint = 0;
  if (millis() - lastPrint > 2000) {
    lastPrint = millis();
    if (gps.location.isValid()) {
      Serial.println("✅ GPS Ready — press button to capture!");
      Serial.print("   LAT: ");       Serial.println(gps.location.lat(), 6);
      Serial.print("   LON: ");       Serial.println(gps.location.lng(), 6);
      Serial.print("   Satellites: "); Serial.println(gps.satellites.value());
      Serial.print("   Altitude: ");  Serial.print(gps.altitude.meters()); Serial.println(" m");
      Serial.print("   Speed: ");     Serial.print(gps.speed.kmph()); Serial.println(" km/h");
      Serial.println("-------------------");
    } else {
      Serial.print("⏳ Waiting for GPS fix... Sats: ");
      Serial.println(gps.satellites.value());
    }
  }

  // ========== Button pressed ==========
  if (digitalRead(BUTTON_PIN) == LOW && !imageSent) {
    Serial.println("📸 Button pressed");

    // Read GPS for 5 more seconds
    unsigned long startTime = millis();
    while (millis() - startTime < 5000) {
      while (gpsSerial.available() > 0)
        gps.encode(gpsSerial.read());
    }

    // Block if GPS not locked
    if (!gps.location.isValid()) {
      Serial.println("❌ GPS not locked — photo NOT sent");
      Serial.print("   Satellites: ");
      Serial.println(gps.satellites.value());
      Serial.println("   Go outside and wait for fix");
      imageSent = true;
      return;
    }

    float lat = gps.location.lat();
    float lon = gps.location.lng();
    float alt = gps.altitude.meters();
    int   sat = gps.satellites.value();
    float spd = gps.speed.kmph();

    Serial.println("✅ GPS locked — capturing photo...");
    Serial.print("   LAT: ");        Serial.println(lat, 6);
    Serial.print("   LON: ");        Serial.println(lon, 6);
    Serial.print("   Altitude: ");   Serial.print(alt); Serial.println(" m");
    Serial.print("   Satellites: "); Serial.println(sat);
    Serial.print("   Speed: ");      Serial.print(spd); Serial.println(" km/h");
    Serial.println("-------------------");

    // Capture photo
    camera_fb_t* fb = esp_camera_fb_get();
    if (!fb) {
      Serial.println("❌ Camera capture failed");
      return;
    }
    Serial.println("📷 Photo captured");

    // Send to server
    HTTPClient http;
    http.begin(serverName);
    http.addHeader("Content-Type",  "application/octet-stream");
    http.addHeader("Latitude",      String(lat, 6));
    http.addHeader("Longitude",     String(lon, 6));
    http.addHeader("Altitude",      String(alt, 2));
    http.addHeader("Satellites",    String(sat));
    http.addHeader("Speed",         String(spd, 2));
    int httpResponseCode = http.POST(fb->buf, fb->len);
    Serial.print("📤 HTTP Response: ");
    Serial.println(httpResponseCode);

    if (httpResponseCode == 200) {
      Serial.println("✅ Photo + GPS sent successfully!");
    } else {
      Serial.println("❌ Send failed — check server");
    }

    http.end();
    esp_camera_fb_return(fb);
    imageSent = true;
  }

  // Reset when button released
  if (digitalRead(BUTTON_PIN) == HIGH) {
    imageSent = false;
  }
}
