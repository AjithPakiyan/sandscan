#include "esp_camera.h"
#include <WiFi.h>
#include <HTTPClient.h>

// ── CONFIGURATION ────────────────────────────────
const char* ssid     = "RVHOS";
const char* password = "RVHOS2022";
String serverName    = "https://renda-distinguished-felica.ngrok-free.dev/upload";

// ── PINS ─────────────────────────────────────────
#define BUTTON_PIN  12
#define FLASH_PIN    4

bool imageSent = false;

// ── CAMERA PIN MAP (AI Thinker ESP32-CAM) ────────
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

// ── CAMERA INIT ──────────────────────────────────
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

// ── SETUP ────────────────────────────────────────
void setup() {
  Serial.begin(115200);
  pinMode(BUTTON_PIN, INPUT_PULLUP);
  pinMode(FLASH_PIN, OUTPUT);
  digitalWrite(FLASH_PIN, LOW);

  delay(500);

  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected");
  Serial.print("IP: ");
  Serial.println(WiFi.localIP());

  startCamera();
  Serial.println("Ready — press button to capture and upload.");
}

// ── LOOP ─────────────────────────────────────────
void loop() {

  // Button pressed
  if (digitalRead(BUTTON_PIN) == LOW && !imageSent) {
    Serial.println("Button pressed — capturing...");

    // Flash ON
    digitalWrite(FLASH_PIN, HIGH);
    delay(200);

    // Capture image
    camera_fb_t* fb = esp_camera_fb_get();

    // Flash OFF
    digitalWrite(FLASH_PIN, LOW);

    if (!fb) {
      Serial.println("Capture failed!");
      return;
    }

    Serial.printf("Image size: %d bytes\n", fb->len);

    // Upload to Flask server
    if (WiFi.status() == WL_CONNECTED) {
      HTTPClient http;
      http.begin(serverName);
      http.addHeader("Content-Type", "application/octet-stream");
      http.addHeader("ngrok-skip-browser-warning", "true");

      int code = http.POST(fb->buf, fb->len);

      if (code == 200) {
        Serial.println("Upload success");
      } else {
        Serial.printf("Upload failed: HTTP %d\n", code);
      }

      http.end();
    } else {
      Serial.println("WiFi lost — skipping upload");
    }

    esp_camera_fb_return(fb);
    imageSent = true;
  }

  // Reset flag when button released
  if (digitalRead(BUTTON_PIN) == HIGH) {
    imageSent = false;
  }
}
