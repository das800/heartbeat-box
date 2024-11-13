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

# Status timings
FAST_BLINK_MS = 100   # Fast blink for WiFi retry
SLOW_BLINK_MS = 500   # Slow blink for MQTT retry

# Setup switch with pull-down resistor
switch = Pin(16, Pin.IN, Pin.PULL_DOWN)

# LED Matrix Setup
# Row pins (PNP transistors - LOW to turn ON)
row_pwms = []
for i in range(8):
    pin = Pin(i, Pin.OUT)
    pwm = PWM(pin)
    pwm.freq(1_000_000)  # 1MHz PWM frequency
    row_pwms.append(pwm)

# Column pins (NPN transistors - HIGH to turn ON)
col_pins = [Pin(i, Pin.OUT) for i in range(8, 16)]

# LED Matrix Constants
MAX_DUTY = 65535
REFRESH_RATE = 100  # Hz
FRAME_TIME = 1/REFRESH_RATE
ROW_TIME = FRAME_TIME/8

# Heartbeat timing parameters (in seconds)
RISE_TIME = 0.09        # Time to reach peak
FALL_TIME = 0.22        # Time for exponential decay
BETWEEN_BEATS = 0.1     # Time between the two beats
BETWEEN_CYCLES = 0.6    # Time between complete heartbeats
SECOND_BEAT_SCALE = 0.8 # Scale of second beat (0-1)

# Circle patterns from medium to full
circle_patterns = [
    # 6x6 filled circle
    [
        [0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 1, 1, 1, 1, 0, 0],
        [0, 1, 1, 1, 1, 1, 1, 0],
        [0, 1, 1, 1, 1, 1, 1, 0],
        [0, 1, 1, 1, 1, 1, 1, 0],
        [0, 1, 1, 1, 1, 1, 1, 0],
        [0, 0, 1, 1, 1, 1, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0],
    ],
    # 8x8 filled circle
    [
        [0, 0, 1, 1, 1, 1, 0, 0],
        [0, 1, 1, 1, 1, 1, 1, 0],
        [1, 1, 1, 1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1, 1, 1, 1],
        [0, 1, 1, 1, 1, 1, 1, 0],
        [0, 0, 1, 1, 1, 1, 0, 0],
    ],
    # Full array filled
    [
        [1, 1, 1, 1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1, 1, 1, 1],
    ],
]

# Global states
heart_beating = False
previous_switch_state = switch.value()
mqtt_client = None  # Make client global for reconnect function
frame_count = 0

# Timing configurations
last_switch_check = time.ticks_ms()
last_mqtt_check = time.ticks_ms()
last_switch_publish = time.ticks_ms()
last_beat_trigger = time.ticks_ms()
last_connection_check = time.ticks_ms()

# Timing intervals
debounce_delay = 50     # 500ms for switch debounce
mqtt_check_delay = 100   # 100ms between MQTT checks
switch_publish_interval = 15000  # Refresh true state every 15 seconds
beat_timeout = 20000     # Stop beating after 20 seconds unless refreshed
connection_check_interval = 5000  # Check connections every 5 seconds

def clear_display():
    """Turn off all LEDs in the matrix"""
    for row in row_pwms:
        row.duty_u16(MAX_DUTY)
    for col in col_pins:
        col.value(0)

def heartbeat_pulse(t):
    """Calculate heartbeat intensity at time t"""
    beat_time = RISE_TIME + FALL_TIME
    sequence_time = (beat_time * 2) + BETWEEN_BEATS + BETWEEN_CYCLES
    
    t = t % sequence_time
    
    # First beat
    if t < RISE_TIME:
        return t / RISE_TIME
    elif t < beat_time:
        decay_time = t - RISE_TIME
        return math.exp(-3 * decay_time / FALL_TIME)
    # Gap between beats
    elif t < beat_time + BETWEEN_BEATS:
        return 0
    # Second beat
    elif t < beat_time + BETWEEN_BEATS + RISE_TIME:
        t_into_beat = t - (beat_time + BETWEEN_BEATS)
        return SECOND_BEAT_SCALE * (t_into_beat / RISE_TIME)
    elif t < (beat_time * 2) + BETWEEN_BEATS:
        t_into_fall = t - (beat_time + BETWEEN_BEATS + RISE_TIME)
        return SECOND_BEAT_SCALE * math.exp(-3 * t_into_fall / FALL_TIME)
    # Rest until next sequence
    else:
        return 0

def blink_status():
    """Single blink to indicate a connection attempt"""
    onboard_led.on()
    time.sleep(1)
    onboard_led.off()

def connect_wifi():
    """Keep trying WiFi until connected"""
    wlan = network.WLAN(network.STA_IF)
    last_blink = time.ticks_ms()
    led_state = False
    
    # Keep trying until connected
    while not wlan.isconnected():
        print('Attempting WiFi connection...')
        wlan.active(True)
        wlan.connect(wifi.wifi_ssid, wifi.wifi_password)
        
        # Blink while waiting/retrying
        while not wlan.isconnected():
            if time.ticks_diff(time.ticks_ms(), last_blink) >= FAST_BLINK_MS:
                led_state = not led_state
                onboard_led.value(led_state)
                last_blink = time.ticks_ms()
            
            time.sleep_ms(10)  # Small delay to prevent tight loop
    
    print('Connected to Wi-Fi, IP:', wlan.ifconfig()[0])
    onboard_led.off()
    blink_status()  # Single blink for success
    return True

def connect_mqtt():
    """Keep trying MQTT until connected"""
    global mqtt_client
    last_blink = time.ticks_ms()
    led_state = False
    
    while True:
        try:
            # Setup SSL
            with open(common_mqtt.ca_cert_path, "rb") as f:
                ca_cert = f.read()
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            context.load_verify_locations(cadata=ca_cert)
            
            # Try connection
            mqtt_client = MQTTClient(user, common_mqtt.mqtt_server, 
                                   port=common_mqtt.mqtt_port,
                                   user=user_mqtt.mqtt_user, 
                                   password=user_mqtt.mqtt_password, 
                                   ssl=context)
            mqtt_client.set_callback(message_callback)
            mqtt_client.connect()
            mqtt_client.subscribe(topic_sub)
            
            print(f"Connected to MQTT broker as {user_mqtt.mqtt_user}")
            onboard_led.off()
            blink_status()  # Single blink for success
            return True
            
        except Exception as e:
            print(f"MQTT connection failed ({type(e).__name__}): {e}")
            
            # Blink and wait before retry
            if time.ticks_diff(time.ticks_ms(), last_blink) >= SLOW_BLINK_MS:
                led_state = not led_state
                onboard_led.value(led_state)
                last_blink = time.ticks_ms()
            
            time.sleep_ms(10)  # Small delay to prevent tight loop

def check_connections():
    """Verify connections and retry if needed"""
    global mqtt_client
    
    # Check WiFi first
    if not network.WLAN(network.STA_IF).isconnected():
        print("WiFi disconnected")
        connect_wifi()  # Will keep trying until reconnected
    
    # Only check MQTT if WiFi is ok
    try:
        mqtt_client.ping()
    except:
        print("MQTT disconnected")
        connect_mqtt()  # Will keep trying until reconnected
    
    return True  # If we get here, both connections are good

def message_callback(topic, msg):
    global heart_beating, last_beat_trigger
    try:
        message = msg.decode('utf-8').lower()
        if message in ['true', 'false']:
            heart_beating = message == 'true'
            if heart_beating:
                last_beat_trigger = time.ticks_ms()
            print(f"Heart beating state changed to: {heart_beating}")
        else:
            print("Invalid message format")
    except (ValueError, TypeError) as e:
        print(f"Message parsing error ({type(e).__name__}): {e}")

# Initial connections
print("Starting connection process...")
connect_wifi()    # Will keep trying until connected
connect_mqtt()    # Will keep trying until connected
print("All connections established!")

try:
    # Main loop
    while True:
        current_time = time.ticks_ms()
        
        # Check connections (will retry indefinitely if either fails)
        if time.ticks_diff(current_time, last_connection_check) >= connection_check_interval:
            check_connections()
            last_connection_check = current_time
        
        # Check switch state (with debounce)
        if time.ticks_diff(current_time, last_switch_check) >= debounce_delay:
            current_switch_state = switch.value()
            
            if current_switch_state != previous_switch_state:
                # State changed - always publish
                print(f"Switch toggled to: {current_switch_state}")
                try:
                    mqtt_client.publish(topic_pub, str(bool(current_switch_state)).lower())
                except (OSError, MemoryError) as e:
                    print(f"Failed to publish ({type(e).__name__}): {e}")
                previous_switch_state = current_switch_state
                last_switch_publish = current_time
            elif current_switch_state:  # Switch is still pressed
                # Refresh the 'true' periodically
                if time.ticks_diff(current_time, last_switch_publish) >= switch_publish_interval:
                    try:
                        mqtt_client.publish(topic_pub, "true")
                        print("Refreshing hug signal")
                    except (OSError, MemoryError) as e:
                        print(f"Failed to publish refresh ({type(e).__name__}): {e}")
                    last_switch_publish = current_time
            
            last_switch_check = current_time
        
        # Check if we should stop beating due to watchdog timeout
        if heart_beating and time.ticks_diff(current_time, last_beat_trigger) >= beat_timeout:
            heart_beating = False
            print("Beat timeout - stopping")
        
        # Check MQTT messages periodically
        if time.ticks_diff(current_time, last_mqtt_check) >= mqtt_check_delay:
            try:
                mqtt_client.check_msg()
            except (OSError, MemoryError) as e:
                print(f"Failed to check messages ({type(e).__name__}): {e}")
            last_mqtt_check = current_time

        # Handle LED matrix display
        if heart_beating:
            frame_start = time.ticks_us()
            
            # Calculate heartbeat value
            current_time = frame_count / REFRESH_RATE
            brightness = heartbeat_pulse(current_time)
            
            # Use brightness to determine both size and intensity
            size_index = min(2, int(brightness * 3))
            duty = int((1.0 - brightness) * MAX_DUTY)  # Invert for PNP
            pattern = circle_patterns[size_index]
            
            # Display pattern
            for row in range(8):
                row_start = time.ticks_us()
                
                # Set up columns
                for col in col_pins:
                    col.value(0)
                for col in range(8):
                    if pattern[row][col]:
                        col_pins[col].value(1)
                
                # Display row
                row_pwms[row].duty_u16(duty)
                while (time.ticks_us() - row_start) < ROW_TIME * 1_000_000:
                    pass
                row_pwms[row].duty_u16(MAX_DUTY)
            
            # Wait for exact frame time
            while (time.ticks_us() - frame_start) < FRAME_TIME * 1_000_000:
                pass
                
            frame_count += 1
        else:
            clear_display()
            frame_count = 0

except KeyboardInterrupt:
    clear_display()
    for pwm in row_pwms:
        pwm.deinit()
    print("\nStopped")