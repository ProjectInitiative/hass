"""Capability and state helpers for linked virtual lights.

This module is deliberately independent of AppDaemon so the safety rules for
fan-out commands can be unit tested without a Home Assistant installation.
"""

from __future__ import annotations

from typing import Any


UNAVAILABLE_STATES = {"unavailable", "unknown", "none", None}
ONOFF_MODES = {"onoff"}
# HA may describe color-capable lights as hs/xy or as an RGB family.
COLOR_MODES = {"hs", "xy", "rgb", "rgbw", "rgbww"}


def _as_modes(attributes: dict[str, Any]) -> set[str]:
    """Return the HA color modes advertised by one light.

    Older integrations do not always expose ``supported_color_modes``.  The
    state attributes are a useful fallback for those entities.
    """
    modes = attributes.get("supported_color_modes")
    if modes:
        return {str(mode) for mode in modes}

    if (
        attributes.get("rgb_color") is not None
        or attributes.get("hs_color") is not None
    ):
        return {"hs"}
    if attributes.get("xy_color") is not None:
        return {"xy"}
    if attributes.get("color_temp_kelvin") is not None or attributes.get("color_temp") is not None:
        return {"color_temp"}
    if attributes.get("brightness") is not None:
        return {"brightness"}
    return {"onoff"}


def capabilities_from_state(entity_state: dict[str, Any]) -> dict[str, Any]:
    """Extract the controllable capabilities of a HA light state."""
    attributes = entity_state.get("attributes", {}) or {}
    modes = _as_modes(attributes)
    effect_list = attributes.get("effect_list")
    if not isinstance(effect_list, list):
        effect_list = []

    return {
        "supported_color_modes": modes,
        "brightness": bool(modes - ONOFF_MODES),
        "color_temp": "color_temp" in modes,
        "rgb": bool(modes & COLOR_MODES),
        "effect": bool(effect_list),
        "effect_list": set(str(effect) for effect in effect_list),
        "min_mireds": attributes.get("min_mireds"),
        "max_mireds": attributes.get("max_mireds"),
    }


def intersect_capabilities(states: list[dict[str, Any]]) -> dict[str, Any]:
    """Return capabilities safe to send to every member of a group.

    The intersection is intentional: advertising a feature that one member
    cannot accept makes a virtual group unreliable.  An empty or unavailable
    group is still represented as a safe on/off light.
    """
    # Keep unavailable members in the capability intersection.  If an
    # unavailable entity has no attributes, its safe fallback is on/off;
    # advertising a feature supported only by currently-online members would
    # make commands unsafe when the missing member returns.
    if not states:
        return {
            "supported_color_modes": {"onoff"},
            "brightness": False,
            "color_temp": False,
            "rgb": False,
            "effect": False,
            "effect_list": set(),
            "min_mireds": None,
            "max_mireds": None,
        }

    capabilities = [capabilities_from_state(state) for state in states]
    modes = set.intersection(*(cap["supported_color_modes"] for cap in capabilities))
    if not modes:
        modes = {"onoff"}

    brightness = all(cap["brightness"] for cap in capabilities)
    color_temp = all(cap["color_temp"] for cap in capabilities)
    rgb = all(cap["rgb"] for cap in capabilities)
    effects_supported = all(cap["effect"] for cap in capabilities)
    effect_list = (
        set.intersection(*(cap["effect_list"] for cap in capabilities))
        if effects_supported
        else set()
    )

    # A color-capable light also supports brightness in HA, even when an
    # integration omits a separate "brightness" mode from its mode list.
    if not brightness and (color_temp or rgb):
        brightness = True

    min_mireds = [
        cap["min_mireds"] for cap in capabilities if cap["min_mireds"] is not None
    ]
    max_mireds = [
        cap["max_mireds"] for cap in capabilities if cap["max_mireds"] is not None
    ]

    return {
        "supported_color_modes": modes,
        "brightness": brightness,
        "color_temp": color_temp,
        "rgb": rgb,
        "effect": bool(effect_list),
        "effect_list": effect_list,
        # The virtual range is the overlap of the member ranges.  HA uses
        # mireds, where a larger value is a warmer color temperature.
        "min_mireds": max(min_mireds) if min_mireds else None,
        "max_mireds": min(max_mireds) if max_mireds else None,
    }


def capability_signature(capabilities: dict[str, Any]) -> tuple:
    """Stable, hashable representation used to detect discovery changes."""
    return (
        tuple(sorted(capabilities["supported_color_modes"])),
        capabilities["brightness"],
        capabilities["color_temp"],
        capabilities["rgb"],
        capabilities["effect"],
        tuple(sorted(capabilities["effect_list"])),
        capabilities["min_mireds"],
        capabilities["max_mireds"],
    )


def clamp_brightness(value: Any) -> int | None:
    """Convert an MQTT brightness value to HA's 1..255 range."""
    try:
        return max(1, min(255, int(float(value))))
    except (TypeError, ValueError):
        return None


def mired_to_kelvin(value: Any) -> int | None:
    """Convert an MQTT/HA mired value to the current HA service field."""
    try:
        mireds = int(float(value))
        if mireds <= 0:
            return None
        return round(1_000_000 / mireds)
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def mqtt_color_to_service_data(color: Any) -> dict[str, Any]:
    """Translate MQTT JSON light color fields to HA light service fields."""
    if not isinstance(color, dict):
        return {}

    if all(key in color for key in ("r", "g", "b")):
        try:
            return {
                "rgb_color": [int(color["r"]), int(color["g"]), int(color["b"])],
            }
        except (TypeError, ValueError):
            return {}

    if "h" in color and "s" in color:
        try:
            return {"hs_color": [float(color["h"]), float(color["s"])]}
        except (TypeError, ValueError):
            return {}

    if "x" in color and "y" in color:
        try:
            return {"xy_color": [float(color["x"]), float(color["y"])]}
        except (TypeError, ValueError):
            return {}

    return {}


def state_payload(
    entity_states: list[dict[str, Any]], capabilities: dict[str, Any]
) -> dict[str, Any]:
    """Build the MQTT JSON state payload for a group.

    State is ON if any available member is ON.  For attributes, brightness is
    averaged across ON members and color/effect are taken from the first ON
    member; this gives Home Assistant a useful deterministic value while the
    next group command still normalizes all members.
    """
    available = [
        state for state in entity_states
        if state.get("state") not in UNAVAILABLE_STATES
    ]
    on_states = [state for state in available if state.get("state") == "on"]
    payload: dict[str, Any] = {"state": "ON" if on_states else "OFF"}
    if not on_states:
        return payload

    attrs_list = [state.get("attributes", {}) or {} for state in on_states]
    if capabilities["brightness"]:
        brightness = [attrs.get("brightness") for attrs in attrs_list]
        brightness = [value for value in brightness if isinstance(value, (int, float))]
        if brightness:
            payload["brightness"] = round(sum(brightness) / len(brightness))

    attrs = attrs_list[0]
    if capabilities["color_temp"]:
        color_temp = attrs.get("color_temp")
        if color_temp is None and attrs.get("color_temp_kelvin"):
            color_temp = round(1_000_000 / attrs["color_temp_kelvin"])
        if color_temp is not None:
            payload["color_temp"] = color_temp

    if capabilities["rgb"]:
        color_data = mqtt_color_from_attributes(attrs)
        if color_data:
            payload["color"] = color_data

    if capabilities["effect"] and attrs.get("effect") in capabilities["effect_list"]:
        payload["effect"] = attrs["effect"]

    if attrs.get("color_mode"):
        payload["color_mode"] = attrs["color_mode"]
    return payload


def mqtt_color_from_attributes(attributes: dict[str, Any]) -> dict[str, Any]:
    """Translate common HA light attributes to MQTT JSON color fields."""
    rgb = attributes.get("rgb_color")
    if isinstance(rgb, (list, tuple)) and len(rgb) >= 3:
        return {"r": rgb[0], "g": rgb[1], "b": rgb[2]}

    hs = attributes.get("hs_color")
    if isinstance(hs, (list, tuple)) and len(hs) >= 2:
        return {"h": hs[0], "s": hs[1]}

    xy = attributes.get("xy_color")
    if isinstance(xy, (list, tuple)) and len(xy) >= 2:
        return {"x": xy[0], "y": xy[1]}

    return {}
