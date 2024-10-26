import network
import time
import ssl
from umqtt.simple import MQTTClient
from machine import Pin

# Import credentials from the respective files
import creds.wifi_creds as wifi
import creds.common_mqtt_creds as common_mqtt
import creds.dayan_mqtt_creds as dayan_mqtt

client_id = 'dayan'
topic_sub = 'dayan/control'
topic_pub = 'luna/control'

# Setup LED
led = Pin("LED", Pin.OUT)

# Connect to Wi-Fi
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(wifi.wifi_ssid, wifi.wifi_password)

while not wlan.isconnected():
    print('Connecting to Wi-Fi...')
    time.sleep(1)

print('Connected to Wi-Fi, IP:', wlan.ifconfig()[0])

# Load the CA certificate
with open(common_mqtt.ca_cert_path, "rb") as f:
    ca_cert = f.read()

# Create SSL context
context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
context.load_verify_locations(cadata=ca_cert)

# Function to handle incoming messages
def message_callback(topic, msg):
    message = msg.decode('utf-8')
    print(f"Received message: {message} on topic: {topic.decode('utf-8')}")
    if message == 'ON':
        led.on()
    elif message == 'OFF':
        led.off()

# Setup MQTT client with SSL context
client = MQTTClient(client_id, common_mqtt.mqtt_server, port=common_mqtt.mqtt_port, 
                    user=dayan_mqtt.mqtt_user, password=dayan_mqtt.mqtt_password, ssl=context)
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
led_state = False
while True:
    # Publish the LED state to Luna
    message = 'ON' if led_state else 'OFF'
    client.publish(topic_pub, message)
    print(f"Published message: {message} to topic: {topic_pub}")
    
    # Toggle the state for the next cycle
    led_state = not led_state
    
    # Check for new messages
    client.check_msg()
    
    # Wait for 1 second
    time.sleep(1)
