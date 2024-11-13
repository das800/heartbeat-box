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
  exit 0
fi

# Determine partner based on user
if [ "$USER" == "dayan" ]; then
  PARTNER="luna"
else
  PARTNER="dayan"
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

# Copy user-specific MQTT credentials
echo "Copying user-specific MQTT credentials..."
mpremote cp "creds/${USER}_mqtt_creds.py" :/creds/user_mqtt_creds.py

# Create user_info.py file with user and partner information
echo "Creating user_info.py file..."
echo "user = '$USER'" > user_info.py
echo "partner = '$PARTNER'" >> user_info.py

# Copy the user_info.py file to the root of the Pico
echo "Copying user_info.py to Pico..."
mpremote cp user_info.py :/user_info.py

# Copy the main script to the root of the Pico
echo "Copying main script to Pico..."
mpremote cp src/main.py :/main.py

# Cleanup temporary user_info.py file
rm user_info.py

echo "Installation complete!"
