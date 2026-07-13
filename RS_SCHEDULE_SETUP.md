# Republic Services Pickup Schedule - Setup

## Quick Setup

### Step 1: Create the address entity in Home Assistant

Add this to your `configuration.yaml` (or use the HA UI to create an input text entity):

```yaml
input_text:
  rs_address:
    name: "Republic Services Address"
    initial: "[YOUR_ADDRESS_HERE]"
```

Or via the HA UI:
- Settings → Devices & Services → Helpers → + Create Helper → Text → Name it "RS Address", set the initial value

### Step 2: Configure secrets.yaml

Copy the example and set your address:
```bash
cp secrets.yaml.example secrets.yaml
```

### Step 3: Install dependencies

```bash
cd appdaemon
pip install -r requirements.txt
```

### Step 4: Restart AppDaemon

The app will auto-register since it's in `apps.yaml`.

## What gets created

AppDaemon will publish MQTT Discovery messages that create these sensors in HA:

| Entity ID | Description |
|---|---|
| `sensor.republic_services_trash_next_pickup` | Date of next trash pickup |
| `sensor.republic_services_recycling_next_pickup` | Date of next recycling pickup |
| `sensor.republic_services_schedule_status` | Human-readable status |

### Example automation

Notify when trash is tomorrow:
```yaml
alias: "Trash reminder"
trigger:
  - platform: time
    at: "17:00:00"
condition:
  - condition: template
    value_template: >
      {{ as_timestamp(states('sensor.republic_services_trash_next_pickup'))
         - as_timestamp(now()) | int < 86400 * 2 }}
action:
  - service: notify.mobile_app_pixel_10_pro_xl
    data:
      message: "Trash pickup is tomorrow!"
```

## How it works

1. On startup and daily at 6:00 AM, the app queries the Republic Services public API
2. No account/login needed — the API is fully public
3. The address is read from `input_text.rs_address` entity (preferred) or `secrets.yaml`
4. Pickup dates are published as MQTT entities via Home Assistant's discovery mechanism
5. You can change the address from the HA UI and the app auto-refreshes

## Troubleshooting

- Check AppDaemon logs for "Fetching Republic Services schedule" messages
- Verify the address entity exists: `states.input_text.rs_address`
- The API returns a 404 if Republic Services doesn't serve your address — check that at republicservices.com/schedule first
