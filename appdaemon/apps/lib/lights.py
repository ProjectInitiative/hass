"""
lib.lights — light state restoration helpers.

Moved from the legacy utils.py module during the overhaul.

Used by meeting_indicator.py to restore lights to their previous state
after a meeting indicator toggles them.
"""


def restore_light_state(app, light_state):
    """
    Restore a light to a previously-saved state by calling the appropriate
    turn_on/turn_off service with the saved attributes.

    Args:
        app:         The AppDaemon app instance.
        light_state: A state dict (from get_state(entity, attribute='all'))
                     with 'entity_id', 'state', and 'attributes' keys.
    """
    entity_id = light_state['entity_id']
    target_state = light_state['state']

    attrs = extract_light_attributes(app, [
        'brightness',
        light_state['attributes']['color_mode'],
    ], light_state['attributes'])
    app.log(f"Restoring {entity_id} to {target_state} with attrs: {attrs}")

    domain = entity_id.split('.')[0]

    if target_state == "off":
        # When restoring to "off", first turn on (to apply attrs like brightness),
        # then turn off shortly after
        app.call_service(f"{domain}/turn_on", entity_id=entity_id, **attrs)
        app.run_in(app.call_service, 0.1, service=f"{domain}/turn_off", entity_id=entity_id)
    else:
        app.call_service(f"{domain}/turn_on", entity_id=entity_id, **attrs)


def extract_light_attributes(app, keys, attrs):
    """
    Extract a subset of keys from an attributes dict, skipping None values.
    Maps 'xy' → 'xy_color' for HA compatibility.

    Args:
        app:   The AppDaemon app instance (for logging).
        keys:  List of attribute keys to extract.
        attrs: The attributes dict to extract from.

    Returns:
        A new dict with the requested keys (that exist and are non-None).
    """
    new_dict = {}
    for key in keys:
        if key == 'xy':
            key = 'xy_color'
        if key in attrs and attrs[key] is not None:
            new_dict[key] = attrs[key]
    return new_dict
