# IoT Connected Heartbeat Display

A pair of decorative heartbeat displays that react to each other over the internet, housed in laser-cut acrylic enclosures. When the button on one display is pressed, its partner device shows a synchronized heartbeat pattern through an 8x8 LED matrix, creating an intimate way to share a moment of connection at a distance. For example, when "Alice" presses their button, "Bob's" display shows the heartbeat, and vice versa.

## Hardware Components

- Raspberry Pi Pico W
- 8x8 LED Matrix (TOM-1988BS-B)
- Transistors:
  - 8x PNP (2N3906) for row control
  - 8x NPN (2N2222A) for column control
- Resistors:
  - 1kΩ resistors for transistor bases
  - 68Ω current limiting resistor for LED power
- Push button (momentary switch)
- Power supply: 3x NiMH batteries in series (3.6V nominal)

## Circuit Structure

The LED matrix is controlled through transistor multiplexing:
- Row control: PNP transistors connected to power (3.6V)
  - GPIO pins control base through 1kΩ resistors
  - LOW turns on rows, HIGH turns off
- Column control: NPN transistors connected to ground
  - GPIO pins control base through 1kΩ resistors
  - HIGH turns on columns, LOW turns off
- Single 68Ω resistor on power line for current limiting
- Push button connected to GPIO16 with internal pull-down

## Software Structure

The project uses MQTT over TLS for communication between paired devices. When one device detects a button press, it publishes to its partner's topic, triggering the heartbeat animation on the partner's display.

```
/creds
  ├── wifi_creds.py         # WiFi credentials
  ├── common_mqtt_creds.py  # MQTT broker details & broker's CA cert path
  ├── user_mqtt_creds.py    # User-specific MQTT credentials
  └── user_info.py          # User and partner identifiers
/lib
  └── MQTT library files
/certs
  └── CA certificate for your MQTT broker
/src
  └── main.py              # Main application code
```

### Credential Setup
1. Create the following files in `/creds`:
   ```python
   # wifi_creds.py
   wifi_ssid = "your_ssid"
   wifi_password = "your_password"
   
   # common_mqtt_creds.py
   mqtt_server = "your_broker"
   mqtt_port = 8883
   ca_cert_path = "/certs/your_ca.crt"  # Path to your MQTT broker's CA certificate
   
   # user_mqtt_creds.py
   mqtt_user = "your_username"
   mqtt_password = "your_password"
   ```

2. Place your MQTT broker's CA certificate in `/certs` - this is needed to establish a secure TLS connection with your MQTT broker

### Installation
The project includes an installation script `install_pico.sh` that handles deployment. Each paired set needs two devices, one configured as 'alice' and one as 'bob':

```bash
# For Alice's device
./install_pico.sh alice

# For Bob's device
./install_pico.sh bob
```

The script:
1. Creates necessary directories on the Pico
2. Copies library files and the MQTT broker's certificate
3. Sets up user-specific credentials
4. Deploys the main application

Each device in a pair needs the opposite configuration - one 'alice' and one 'bob'. This establishes:
- Which button triggers which display
- The MQTT topics each device subscribes to
- The credentials used for authentication

## Operation
Once a pair of devices is installed, they will:
1. Connect to WiFi and the MQTT broker
2. Listen for their partner's button presses via MQTT
3. When a button press is received from the partner device:
   - Display an expanding/contracting circle animation
   - Control brightness using PWM
   - Show a natural heartbeat rhythm (two beats followed by a pause)
4. When the local button is pressed:
   - Send a message to trigger the partner's display
   - No local animation is shown (only the receiving device shows the heartbeat)

The LED display uses both multiplexing (100Hz refresh) and PWM (1MHz) to create smooth animations with varied brightness levels.