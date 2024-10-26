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

topic_sub = f'{user}/heartbeat'
topic_pub = f'{partner}/heartbeat'

# Setup onboard LED for status
onboard_led = Pin("LED", Pin.OUT)

# Setup LED with PWM on GPIO 15
led = PWM(Pin(15))
led.freq(1000)

# Setup switch with pull-down resistor
switch = Pin(14, Pin.IN, Pin.PULL_DOWN)

# Global states
heart_beating = False
previous_switch_state = switch.value()

# Timing configurations
last_switch_check = time.ticks_ms()
last_heartbeat = time.ticks_ms()
last_mqtt_check = time.ticks_ms()
last_switch_publish = time.ticks_ms()
last_beat_trigger = time.ticks_ms()

# Timing intervals
debounce_delay = 500     # 500ms for switch debounce
heartbeat_delay = 900    # 900ms between heartbeats
mqtt_check_delay = 100   # 100ms between MQTT checks
switch_publish_interval = 15000  # Refresh true state every 15 seconds
beat_timeout = 20000     # Stop beating after 20 seconds unless refreshed

def blink_status():
    onboard_led.on()
    time.sleep(1)
    onboard_led.off()

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
blink_status()  # Blink to show WiFi connection

# Setup SSL with CA certificate
with open(common_mqtt.ca_cert_path, "rb") as f:
    ca_cert = f.read()
context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
context.load_verify_locations(cadata=ca_cert)

# Function to handle incoming messages
def message_callback(topic, msg):
    global heart_beating, last_beat_trigger
    message = msg.decode('utf-8').lower()
    if message in ['true', 'false']:
        heart_beating = message == 'true'
        if heart_beating:
            last_beat_trigger = time.ticks_ms()  # Reset watchdog timer
        print(f"Heart beating state changed to: {heart_beating}")
    else:
        print("Invalid message format")

# Setup MQTT client with SSL context
client = MQTTClient(user, common_mqtt.mqtt_server, port=common_mqtt.mqtt_port,
                   user=user_mqtt.mqtt_user, password=user_mqtt.mqtt_password, ssl=context)
client.set_callback(message_callback)

try:
    client.connect()
    print(f"Connected to MQTT broker as {user_mqtt.mqtt_user}")
    blink_status()  # Blink to show MQTT connection
except Exception as e:
    print(f"Error connecting to MQTT broker: {e}")
    while True:
        pass  # Halt if connection fails

# Subscribe to topic
client.subscribe(topic_sub)

# Main loop
while True:
    current_time = time.ticks_ms()
    
    # Check switch state (with debounce)
    if time.ticks_diff(current_time, last_switch_check) >= debounce_delay:
        current_switch_state = switch.value()
        
        if current_switch_state != previous_switch_state:
            # State changed - always publish
            print(f"Switch toggled to: {current_switch_state}")
            client.publish(topic_pub, str(bool(current_switch_state)).lower())
            previous_switch_state = current_switch_state
            last_switch_publish = current_time
        elif current_switch_state:  # Switch is still pressed
            # Refresh the 'true' periodically
            if time.ticks_diff(current_time, last_switch_publish) >= switch_publish_interval:
                client.publish(topic_pub, "true")
                last_switch_publish = current_time
                print("Refreshing hug signal")
        
        last_switch_check = current_time
    
    # Check if we should stop beating due to watchdog timeout
    if heart_beating and time.ticks_diff(current_time, last_beat_trigger) >= beat_timeout:
        heart_beating = False
        print("Beat timeout - stopping")
    
    # Run heartbeat if active
    if heart_beating and time.ticks_diff(current_time, last_heartbeat) >= heartbeat_delay:
        heartbeat_pulse()
        last_heartbeat = current_time
    
    # Check MQTT messages periodically
    if time.ticks_diff(current_time, last_mqtt_check) >= mqtt_check_delay:
        client.check_msg()
        last_mqtt_check = current_time