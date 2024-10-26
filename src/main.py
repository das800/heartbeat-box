import network
import time
import ssl
import math
from umqtt.simple import MQTTClient
from machine import Pin, PWM

# Import user information
from user_info import user, partner

# Import credentials from the respective files
import creds.wifi_creds as wifi
import creds.common_mqtt_creds as common_mqtt
import creds.user_mqtt_creds as user_mqtt

client_id = user
topic_sub = f'{user}/heartbeat'
topic_pub = f'{partner}/heartbeat'

# Setup LED with PWM
led = PWM(Pin("LED"))
led.freq(1000)

# Global state
heart_beating = False

def heartbeat_pulse(rise_speed=4096, fall_speed=2048, pulse_pause=0.1):
    def single_pulse():
        # Quick Rise
        for duty in range(0, 65536, rise_speed):
            led.duty_u16(duty)
            time.sleep(0.005)
        # Ensure the LED is fully on
        led.duty_u16(65535)
        
        # Dampened Fall
        for duty in range(65535, -1, -fall_speed):
            damped_value = int(65535 * math.exp(-3 * (1 - duty / 65535)))
            led.duty_u16(max(damped_value, 0))
            time.sleep(0.005)
        # Ensure the LED is fully off
        led.duty_u16(0)
    
    single_pulse()
    time.sleep(pulse_pause)
    single_pulse()

# Connect to Wi-Fi
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(wifi.wifi_ssid, wifi.wifi_password)

while not wlan.isconnected():
    print('Connecting to Wi-Fi...')
    time.sleep(1)
print('Connected to Wi-Fi, IP:', wlan.ifconfig()[0])

# Setup SSL with CA certificate
with open(common_mqtt.ca_cert_path, "rb") as f:
    ca_cert = f.read()
context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
context.load_verify_locations(cadata=ca_cert)

# Function to handle incoming messages
def message_callback(topic, msg):
    global heart_beating
    message = msg.decode('utf-8').lower()
    if message in ['true', 'false']:
        heart_beating = message == 'true'
        print(f"Heart beating state changed to: {heart_beating}")
    else:
        print("Invalid message format")

# Setup MQTT client with SSL context
client = MQTTClient(client_id, common_mqtt.mqtt_server, port=common_mqtt.mqtt_port,
                   user=user_mqtt.mqtt_user, password=user_mqtt.mqtt_password, ssl=context)
client.set_callback(message_callback)

try:
    client.connect()
except Exception as e:
    print(f"Error connecting to MQTT broker: {e}")
    while True:
        pass  # Halt if connection fails

# Subscribe to topic
client.subscribe(topic_sub)

# Main loop
while True:
    # Check for new messages
    client.check_msg()
    
    # If heart should be beating, do one heartbeat cycle
    if heart_beating:
        heartbeat_pulse()
        time.sleep(0.9)  # Pause between heartbeat cycles
    else:
        time.sleep(0.1)  # Small delay when not beating