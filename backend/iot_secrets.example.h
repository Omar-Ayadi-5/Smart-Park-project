#pragma once
// Copy to iot_secrets.h alongside the sketch. Keep real values private.
#define WIFI_SSID "replace_with_wifi_ssid"
#define WIFI_PASSWORD "replace_with_wifi_password"
#define SUPABASE_URL "https://your-project.supabase.co"
#define SUPABASE_PUBLISHABLE_KEY "replace_with_publishable_key"
// A dedicated Supabase Auth user mapped in sensor_device; never a service-role key.
#define SUPABASE_DEVICE_EMAIL "device@example.com"
#define SUPABASE_DEVICE_PASSWORD "replace_with_device_password"
// Paste the current issuing root CA PEM for your Supabase HTTPS endpoint.
// Empty configuration fails closed: no certificate verification bypass exists.
static const char SUPABASE_ROOT_CA[] PROGMEM = R"PEM(
)PEM";
