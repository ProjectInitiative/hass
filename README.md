# Home Automation System

A comprehensive AppDaemon-based home automation system for Home Assistant, featuring garage control, lighting automation, door management, and notification systems.

## Core Features

### 📊 State History

The `GlobalStateManager` maintains entity state history:
- Maximum of 10 historical states per entity
- Timestamp tracking
- State locking capability
- Reversion to previous states

```python
# Revert to previous state
state_manager.revert_to_previous_state(entity_id, steps_back=1)

# Lock current state
state_manager.lock_state(entity_id)
```

### 🔄 MQTT Integration

Automated MQTT entity creation:
- Dynamic topic generation
- Auto-discovery support
- State synchronization
- Availability tracking

Entity types:
- Switches
- Numbers
- Sensors
- Binary sensors

Example MQTT switch creation:
```python
switch = MQTTSwitch(
    entity_id="global_switch",
    name="Global Control Switch"
)
switch.initialize()  # Creates MQTT topics and discovery
```


### 🚗 Garage Automation
- Automatic garage door control based on car presence
- Smart light control when entering/exiting
- Safety notifications for extended door opening
- Auto-close functionality after set duration
- Remote lock management

### 💡 Lighting Control
- Global light management system
- Door-activated lighting
- Group-based light control
- Motion-based automation
- Meeting status indicator integration

### 🔒 Security
- Automatic door locking system
- Configurable lock delays
- Door state monitoring
- Multi-door support
- MQTT-based state management

### 📱 Notifications
- Mobile notifications for critical events
- Configurable notification groups
- Interactive notification actions
- Garage door status alerts
- Door security notifications

## Dependencies

- AppDaemon 4.x
- Home Assistant
- MQTT Broker
- Mobile App Integration for notifications

## Installation

1. Copy all Python files to your AppDaemon apps directory
2. Configure your `apps.yaml` with appropriate settings
3. Restart AppDaemon

## Classes Overview

- `AllLights`: Global light management
- `AutoLock`: Automatic door locking system
- `GarageAndLightsAutomation`: Garage/car presence automation
- `GarageNotifyAutomation`: Garage notification system
- `GlobalNotify`: Notification management
- `GlobalStateManager`: State tracking and management
- `AutomationManager`: MQTT-based automation control

## Integration Points

- MQTT for state management and control
- Home Assistant entities for device control
- Mobile apps for notifications
- Bluetooth for car presence detection
- Android Auto for additional car presence verification
