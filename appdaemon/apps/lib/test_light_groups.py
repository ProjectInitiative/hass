#!/usr/bin/env python3
"""Unit tests for linked-light capability and MQTT payload helpers."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.light_groups import (  # noqa: E402
    capability_signature,
    clamp_brightness,
    intersect_capabilities,
    mqtt_color_to_service_data,
    state_payload,
)


def light(state="on", **attributes):
    return {"state": state, "attributes": attributes}


def test_onoff_group_is_safe():
    caps = intersect_capabilities([light("off", supported_color_modes=["onoff"]), light()])
    assert caps["supported_color_modes"] == {"onoff"}
    assert caps["brightness"] is False


def test_capabilities_use_intersection():
    states = [
        light(
            "on",
            supported_color_modes=["brightness", "color_temp"],
            min_mireds=153,
            max_mireds=500,
        ),
        light(
            "on",
            supported_color_modes=["brightness", "color_temp"],
            min_mireds=200,
            max_mireds=400,
        ),
    ]
    caps = intersect_capabilities(states)
    assert caps["supported_color_modes"] == {"brightness", "color_temp"}
    assert caps["color_temp"] is True
    assert caps["min_mireds"] == 200
    assert caps["max_mireds"] == 400


def test_mixed_features_do_not_get_advertised():
    caps = intersect_capabilities([
        light("on", supported_color_modes=["rgb"]),
        light("on", supported_color_modes=["color_temp"]),
    ])
    assert caps["supported_color_modes"] == {"onoff"}
    assert caps["rgb"] is False
    assert caps["color_temp"] is False


def test_effects_are_intersected():
    caps = intersect_capabilities([
        light("on", supported_color_modes=["rgb"], effect_list=["rainbow", "pulse"]),
        light("on", supported_color_modes=["rgb"], effect_list=["rainbow"]),
    ])
    assert caps["effect"] is True
    assert caps["effect_list"] == {"rainbow"}


def test_state_payload_aggregates_brightness():
    caps = intersect_capabilities([
        light("on", supported_color_modes=["brightness"], brightness=100),
        light("on", supported_color_modes=["brightness"], brightness=200),
    ])
    assert state_payload([
        light("on", supported_color_modes=["brightness"], brightness=100),
        light("on", supported_color_modes=["brightness"], brightness=200),
    ], caps) == {"state": "ON", "brightness": 150}


def test_unavailable_member_downgrades_unknown_capabilities():
    caps = intersect_capabilities([
        light("unavailable"),
        light("off", supported_color_modes=["rgb"]),
    ])
    assert caps["supported_color_modes"] == {"onoff"}


def test_state_payload_ignores_unavailable_members():
    caps = intersect_capabilities([
        light("unavailable", supported_color_modes=["rgb"]),
        light("off", supported_color_modes=["rgb"]),
    ])
    assert state_payload([
        light("unavailable", supported_color_modes=["rgb"]),
        light("off", supported_color_modes=["rgb"]),
    ], caps)["state"] == "OFF"


def test_mqtt_colors_and_brightness_are_validated():
    assert mqtt_color_to_service_data({"r": 1, "g": 2, "b": 3}) == {"rgb_color": [1, 2, 3]}
    assert mqtt_color_to_service_data({"h": 10, "s": 20}) == {"hs_color": [10.0, 20.0]}
    assert clamp_brightness(999) == 255
    assert clamp_brightness(0) == 1
    assert clamp_brightness("bad") is None


def test_mqtt_light_discovery_uses_json_schema():
    from lib.mqtt import MQTTLight

    class FakeApp:
        def get_plugin_api(self, name):
            return object()

    light_entity = MQTTLight(
        FakeApp(),
        "linked_track",
        "Track Lights",
        supported_color_modes=["brightness", "rgb"],
        brightness=True,
        effect_list=["rainbow"],
    )
    payload = light_entity.discovery_payload
    assert payload["schema"] == "json"
    assert payload["brightness"] is True
    assert payload["supported_color_modes"] == ["brightness", "rgb"]
    assert payload["effect_list"] == ["rainbow"]


def test_capability_signature_is_stable():
    caps = intersect_capabilities([light("on", supported_color_modes=["brightness"])])
    assert capability_signature(caps) == capability_signature(dict(caps))


if __name__ == "__main__":
    tests = [
        value for name, value in sorted(globals().items())
        if name.startswith("test_") and callable(value)
    ]
    failures = 0
    for test in tests:
        try:
            test()
            print(f"  PASS  {test.__name__}")
        except Exception as exc:
            failures += 1
            print(f"  FAIL  {test.__name__}: {exc}")
    print(f"{len(tests) - failures} passed, {failures} failed")
    sys.exit(1 if failures else 0)
