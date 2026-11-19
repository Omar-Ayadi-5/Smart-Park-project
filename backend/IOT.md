# ESP32 occupancy sensor

The firmware measures distance, waits for a stable observation, and calls a Supabase RPC mapped to one parking spot. The canonical source is `iot_config`; `firmware/smart_park/smart_park.ino` includes it for the Arduino build.

## Hardware

| Signal | ESP32 GPIO |
| --- | --- |
| Ultrasonic trigger | 5 |
| Ultrasonic echo | 18 |
| Red LED (occupied) | 22 |
| Green LED (free) | 21 |

Use 3.3 V-compatible input levels, including level shifting for a 5 V sensor echo output. Thresholds are at or below 10 cm for occupied and above 20 cm for free. A state must remain stable for 15 seconds; invalid readings reset that timer. Updates are retried at least 3 seconds apart, and the initial stable state is synchronized even if it is free.

## Database and device identity

1. Configure a **fresh** Supabase PostgreSQL database and run the backend's `flask db upgrade` command. This installs the schema, RLS, and `public.sync_spot(boolean)`.
2. Create parking data with `flask seed-demo` or your own provisioning process.
3. Create a dedicated Supabase Auth user for the device using your project's administrative interface. Confirm the account and save its UUID and credentials privately.
4. From `backend/`, map its UUID to exactly one existing spot:

```shell
python -m flask --app app:create_app provision-device --subject YOUR_DEVICE_USER_UUID --spot-code A1
```

The function reads the authenticated JWT subject and looks up `sensor_device`; the request cannot choose another spot. It locks the spot, records a history event only when the state changes, and preserves `OUT_OF_SERVICE`. Direct client table access and anonymous function execution are revoked. The Auth user must be dedicated to the device, not an administrator's personal account.

## Private firmware configuration

Copy `iot_secrets.example.h` to `iot_secrets.h` beside `iot_config`. Fill in Wi-Fi settings, your Supabase HTTPS URL, publishable API key, and dedicated device email/password. Paste the valid root CA PEM for the endpoint into `SUPABASE_ROOT_CA`; obtain it from your provider's certificate chain documentation and verify it independently.

The firmware sets the trusted CA, synchronizes time over SNTP, and refuses to send credentials without a configured certificate and a valid clock. It signs in to Supabase Auth over verified HTTPS, keeps the short-lived access token in memory, and renews authentication before expiry. The publishable key and device access token are separate headers. Never embed a service-role key, Flask signing key, or database password.

Wi-Fi reconnect attempts are bounded by a retry interval; the loop does not wait indefinitely for Wi-Fi during startup. Device credentials remain extractable from physical firmware, so use unique low-privilege identities and revoke compromised devices.

## Compile

Install Arduino CLI, the ESP32 board package, and ArduinoJson:

```shell
arduino-cli core update-index --additional-urls https://espressif.github.io/arduino-esp32/package_esp32_index.json
arduino-cli core install esp32:esp32@3.3.12 --additional-urls https://espressif.github.io/arduino-esp32/package_esp32_index.json
arduino-cli lib install ArduinoJson@7.4.2
arduino-cli compile --fqbn esp32:esp32:esp32 backend/firmware/smart_park
```

Run the compile command from the repository root after creating the private header. CI copies the placeholder header only to compile; it never connects to Wi-Fi or Supabase. Compilation does not replace bench testing: verify real sensor distances, CA trust, clock synchronization, device sign-in, reconnect behavior, and the correct spot mapping before installing hardware.
