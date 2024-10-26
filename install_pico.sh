#!/bin/bash

# Check if user argument is provided
if [ -z "$1" ]; then
  echo "Usage: $0 <user>"
  echo "<user> should be either 'dayan' or 'luna'"
  exit 1
fi

USER=$1

# Validate user argument
if [ "$USER" != "dayan" ] && [ "$USER" != "luna" ]; then
  echo "Invalid user: $USER"
  echo "<user> should be either 'dayan' or 'luna'"
  exit 1
fi

# Check if creds directory exists on the Pico and create it if not
echo "Checking if /creds directory exists on Pico..."
mpremote fs mkdir /creds || true

# Copy the lib folder to the Pico
echo "Copying lib folder to Pico..."
mpremote cp -r lib :

# Copy the certs folder to the Pico
echo "Copying certs folder to Pico..."
mpremote cp -r certs :

# Copy the credentials to the Pico
echo "Copying Wi-Fi and common MQTT credentials..."
mpremote cp creds/wifi_creds.py :/creds/wifi_creds.py
mpremote cp creds/common_mqtt_creds.py :/creds/common_mqtt_creds.py

# Copy user-specific MQTT credentials and main script
USER_MQTT_CREDS="creds/${USER}_mqtt_creds.py"
MAIN_SCRIPT="src/${USER}_main.py"

echo "Copying ${USER^}'s MQTT credentials..."
mpremote cp "$USER_MQTT_CREDS" :/creds/${USER}_mqtt_creds.py

# Copy the main script to the root of the Pico
if [ -f "$MAIN_SCRIPT" ]; then
  echo "Copying main script ($MAIN_SCRIPT) to Pico..."
  mpremote cp "$MAIN_SCRIPT" :/main.py
else
  echo "Main script not found: $MAIN_SCRIPT"
  exit 1
fi

echo "Installation complete!"
