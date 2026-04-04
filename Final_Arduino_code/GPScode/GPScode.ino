#include <WiFi.h>
#include <HTTPClient.h>
#include <TinyGPS++.h>

// ── CONFIGURATION ────────────────────────────────
const char* ssid     = "RVHOS";
const char* password = "RVHOS2022";
String serverName    = "https://renda-distinguished-felica.ngrok-free.dev/gps";

// ── GPS SERIAL ───────────────────────────────────
TinyGPSPlus gps;
HardwareSerial gpsSerial(1);  // UART1
#define GPS_RX 16
#define GPS_TX 17
#define GPS_BAUD 9600

// ── SETUP ────────────────────────────────────────
void setup() {
  Serial.begin(115200);
  gpsSerial.begin(GPS_BAUD, SERIAL_8N1, GPS_RX, GPS_TX);

  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected");
  Serial.print("IP: ");
  Serial.println(WiFi.localIP());
  Serial.println("Waiting for GPS fix...");
}

// ── LOOP ─────────────────────────────────────────
void loop() {

  // Read GPS data
  while (gpsSerial.available() > 0) {
    gps.encode(gpsSerial.read());
  }

  // Send GPS if valid
  if (gps.location.isUpdated() && gps.location.isValid()) {
    float lat = gps.location.lat();
    float lon = gps.location.lng();

    Serial.printf("GPS → Lat: %.6f, Lon: %.6f\n", lat, lon);

    if (WiFi.status() == WL_CONNECTED) {
      HTTPClient http;

      String url = serverName + "?lat=" + String(lat, 6) + "&lon=" + String(lon, 6);

      http.begin(url);
      http.addHeader("ngrok-skip-browser-warning", "true");

      int code = http.GET();

      if (code == 200) {
        Serial.println("GPS sent");
      } else {
        Serial.printf("GPS send failed: HTTP %d\n", code);
      }

      http.end();
    } else {
      Serial.println("WiFi lost — skipping send");
    }

  } else {
    Serial.println("No GPS fix yet...");
  }

  delay(5000);  // Send every 5 seconds
}
