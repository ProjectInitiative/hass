# In your Appdaemon app
# def create_entity(hass, entity_type, entity_id, attributes=None):
#     # Build service data with entity information
#     data = {
#         "entity_id": entity_id,
#     }
#     if attributes:
#         data["attributes"] = attributes

#     # Call Home Assistant service to create the entity
#     hass.call_service("homeassistant/add_entity", data=data)

def group_entities(hass, entities):

    entities = list(entities)
    groups = {}

    for i in range(len(entities) - 1):
        entity = entities[i]
        friendly_name = entity['attributes']['friendly_name'].lower()
        current_intersection = friendly_name

        # skip if already a member of a group, and add to that group
        if 'is_group_member' in entity.keys() and entity['is_group_member']:
        # if contains_substring(friendly_name, groups.keys()):
            continue

        group_intersecting_entities = []
        # intersections = set()
        for j in range(i+1, len(entities)):
            comparative_entity = entities[j]
            comparative_friendly_name = comparative_entity['attributes']['friendly_name'].lower()
            res = find_starting_strings_intersection(friendly_name, comparative_friendly_name)
            # hass.log(f"friendly_name: {friendly_name}")
            # hass.log(f"comparative_friendly_name: {comparative_friendly_name}")
            # hass.log(f"intersection: {res}")

            # if res != "":
            #     intersections.add(res)
            if res != "" and len(res) < len(current_intersection):
                # if current comparison entity matches, include in this intersection group
                if 'is_group_member' not in entity.keys():
                    entity['is_group_member'] = True
                    group_intersecting_entities.append(entity)

                comparative_entity['is_group_member'] = True
                group_intersecting_entities.append(comparative_entity)
                current_intersection = res
        # hass.log(f"intersections from this batch: {intersections}")


        groups.setdefault(current_intersection, []).extend(list(group_intersecting_entities))

        # consolidate groups
        for k in range(len(groups) - 1):
            group = list(groups.keys())[k]
            comparative_group = list(groups.keys())[k+1]

            res = find_starting_strings_intersection(group, comparative_group)
            if res != "":
                hass.log(f"group: {group} comparative_group: {comparative_group} intersection: {res}")
            if res != "" and len(res) < len(group):
                groups[res] = groups.pop(group) + groups.pop(comparative_group)
                break

        # hass.log(f"found group: {current_intersection}")

    # for group, entities in groups.items():
    #     for entity in entities:
    #         hass.log(f"found group: {group}, entity: {entity['attributes']['friendly_name']}")
            

def contains_substring(text, substrings):
  """
  Checks if a string does not contain any of the substrings in a list (case-insensitive).

  Args:
      text: The string to validate.
      substrings: A list of substrings to check for.

  Returns:
      False if the string does not contain any of the substrings, True otherwise.
  """
  lowercase_text = text.lower()
  return any(substring.lower() in lowercase_text for substring in substrings)

            
        # hass.log(f"operating on entity {friendly_name}")

def find_starting_strings_intersection(str1, str2):
  """
  Compares two strings and returns the intersection starting from the beginning,
  ensuring the intersection contains at least a full word.

  Args:
      str1: The first string.
      str2: The second string.

  Returns:
      The intersection of the two strings starting from the beginning, containing
      at least a full word, or an empty string if there's no intersection.
  """
  intersection = ""
  words1 = str1.lower().split()
  words2 = str2.lower().split()

  for i, word in enumerate(words1):
    if i >= len(words2) or word != words2[i]:
      break
    intersection += word + " "

  # Check if intersection contains at least a word (remove trailing space)
  return intersection.strip()
  return intersection[:-1] if intersection and intersection.split()[0] in words2 else ""
    
    


def call_light_state_as_service(hass, state):

        hass.light_entity = hass.get_entity(state['entity_id'])
        # new_dict = remove_keys([
        #     'context',
        #     'last_changed',
        #     'last_reported',
        #     'last_updated',
        #     'supported_features',
        #     'friendly_name',
        #     'supported_color_modes',
        #     'min_mireds',
        #     'max_mireds',
        #     'color_temp_kelvin',
        #     # 'rgb_color',
        #     'color_temp',
        #     'color_mode',
        #     'xy_color',
        #     'hs_color',
        #     'min_color_temp_kelvin',
        #     'max_color_temp_kelvin'
        # ],
        # state['attributes'])
        # hass.log(new_dict)
        attrs = extract_light_keys(hass,[
            'brightness',
            state['attributes']['color_mode']
        ],
        state['attributes'])
        hass.log(attrs)
        # attrs = { 'rgb_color': [255,0,0] }


        # hass.light_entity.set_state(**hass.state)
        entity = state['entity_id']
        state = state['state']
        hass.log(state)

        if state == "off":
            hass.call_service(f"{entity.split('.')[0]}/turn_on", entity_id=entity, **attrs)
            hass.run_in(hass.call_service, .1, service=f"{entity.split('.')[0]}/turn_{state}", entity_id=entity)
            # hass.call_service(f"{entity.split('.')[0]}/turn_{state}", entity_id=entity)
        else:
            hass.call_service(f"{entity.split('.')[0]}/turn_{state}", entity_id=entity, **attrs)
        # hass.call_service(f"{entity.split('.')[0]}/turn_{state}",**new_dict)
        # hass.light_entity.set_state(state=hass.prev_states[light]['state'], attributes=hass.prev_states[light])

def extract_light_keys(hass, keys, dict):
    new_dict = {}
    hass.log(keys)
    for key in keys:
        if key == 'xy': key = 'xy_color'
        if key in dict.keys() and dict[key] is not None:
            new_dict[key] = dict[key]
    return new_dict

def remove_keys(keys, dict):
    for key in keys:
        dict.pop(key, None)
    return dict
