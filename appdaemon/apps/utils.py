"""
utils — legacy shared utility functions.

NOTE: This module is slated for removal in Phase 3 of the overhaul.
The live functions (call_light_state_as_service, extract_light_keys) will
move into lib/ and the dead functions will be deleted. Do not add new code
here — use lib/ instead.

Currently used by:
    - meeting_indicator.py (call_light_state_as_service)
"""

def group_entities(hass, entities):
    """
    Group entities by common friendly-name prefixes.

    WARNING: This function MUTATES the input entity dicts (adds an
    'is_group_member' key). It is currently dead code (not called anywhere).
    Will be removed in Phase 3 of the overhaul.
    """
    entities = list(entities)
    groups = {}

    for i in range(len(entities) - 1):
        entity = entities[i]
        friendly_name = entity['attributes']['friendly_name'].lower()
        current_intersection = friendly_name

        # skip if already a member of a group
        if entity.get('is_group_member'):
            continue

        group_intersecting_entities = []
        for j in range(i + 1, len(entities)):
            comparative_entity = entities[j]
            comparative_friendly_name = comparative_entity['attributes']['friendly_name'].lower()
            res = find_starting_strings_intersection(friendly_name, comparative_friendly_name)

            if res != "" and len(res) < len(current_intersection):
                if not entity.get('is_group_member'):
                    entity['is_group_member'] = True
                    group_intersecting_entities.append(entity)

                comparative_entity['is_group_member'] = True
                group_intersecting_entities.append(comparative_entity)
                current_intersection = res

        groups.setdefault(current_intersection, []).extend(group_intersecting_entities)

        # consolidate groups
        for k in range(len(groups) - 1):
            group = list(groups.keys())[k]
            comparative_group = list(groups.keys())[k + 1]

            res = find_starting_strings_intersection(group, comparative_group)
            if res != "":
                hass.log(f"group: {group} comparative_group: {comparative_group} intersection: {res}")
            if res != "" and len(res) < len(group):
                groups[res] = groups.pop(group) + groups.pop(comparative_group)
                break


def contains_substring(text, substrings):
    """
    Check if a string contains any of the substrings (case-insensitive).

    Currently dead code. Will be removed in Phase 3 of the overhaul.
    """
    lowercase_text = text.lower()
    return any(substring.lower() in lowercase_text for substring in substrings)


def find_starting_strings_intersection(str1, str2):
    """
    Compare two strings and return the common prefix of full words.

    Args:
        str1: The first string.
        str2: The second string.

    Returns:
        The word-level common prefix, or an empty string if none.
    """
    words1 = str1.lower().split()
    words2 = str2.lower().split()

    intersection = []
    for i, word in enumerate(words1):
        if i >= len(words2) or word != words2[i]:
            break
        intersection.append(word)

    return " ".join(intersection)


def call_light_state_as_service(app, light_state):
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

    attrs = extract_light_keys(app, [
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


def extract_light_keys(app, keys, attrs):
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
