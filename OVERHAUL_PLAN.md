# AppDaemon Overhaul Plan

Branch: `refactor/overhaul` (to be created from `main`)

Guiding principles (confirmed with owner):
- **Preserve behavior & intent.** No functional changes to what automations do — only to how the code is structured. Garage auto-open/close, water shutoff, blind schedules, etc. keep working identically.
- **Introduce a `lib/` shared package** under `appdaemon/apps/lib/`. Consumers import from it; dead/duplicated helpers move there or get deleted.
- **Consolidate & redesign shared libraries** to be more functional for the consuming apps (not a 1:1 port of the existing mess).
- **Keep AppDaemon container install working:** `requirements.txt` remains the source of truth for `pip install`. Tooling config (ruff/black) is optional and additive.

---

## Repository shape (target)

```
appdaemon/apps/
  lib/
    __init__.py
    base.py          # BaseApp(hass.Hass) — common lifecycle, arg helpers, accessors
    notify.py        # thin, consistent wrapper over the global_notify backend
    mqtt.py          # MQTTDiscoveryEntity + topic/availability conventions (one way)
    time_utils.py    # parse_time, is_time_between (overnight-aware), seconds_until, parse_iso
    scheduling.py    # (optional) consolidated scheduler helpers absorbed from cron_scheduler/timer
  area_handler.py    # keep (modern, clean) — minor touch-ups only
  simple_state_linker.py
  all_lights.py
  auto_lock.py
  automation_manager.py
  blind_schedule.py
  door_light_automation.py
  doorbell_notification.py
  entity_monitor.py
  fan_auto_off.py
  garage_automation.py
  garage_notify_automation.py
  garage_utils.py
  global_notify.py   # backend, kept; signature normalized
  meeting_indicator.py
  republic_services_schedule.py
  water_sensor_monitor.py
  testbutton_notification.py

docs/
  generate_docs.py   # fix map drift, skip dead modules
integrations/esphome/  # untouched
requirements.txt     # single source of truth for container install
appdaemon/requirements.txt  # REMOVE (merged into root requirements.txt)
.ruff.toml           # optional lint/format config (does not affect install)
```

Deleted:
- `hello.py` (tutorial leftover)
- `state_manager.py` (41-line stub, not enabled, references utils pointlessly)
- `cron_scheduler.py` (dead; useful bits absorbed into `lib/time_utils.py` / `lib/scheduling.py`)
- `utils.py` (dead/mutating helpers removed; survivors move into `lib/`)

---

## Per-app behavior contract (what we MUST preserve)

| App | Behavior to preserve |
|-----|----------------------|
| garage_automation | Open garage+lights on arrival (phone home + in car); close on departure (phone away + in car) |
| garage_notify_automation | 30-min pre-notify, 50-min final notify, auto-close at 60 min, action buttons, remote lock/unlock 10 min window |
| garage_utils | close/open garage door + lights; check door state after 20s; notify on failure |
| auto_lock | Lock doors 10 min (configurable via MQTT) after closing; disable-able via MQTT enable_topic |
| door_light_automation | Turn on mapped lights when a door opens AT NIGHT; turn off after timeout |
| water_sensor_monitor | On leak: shut main valve (unless excluded), send critical + optional TTS |
| blind_schedule | Light-level + time triggers, per-blind overrides, group/individual, debounce |
| fan_auto_off | Time-limit and/or cutoff-time shutoff, optional enforcement window |
| entity_monitor | Notify when an entity goes unavailable OR not seen within check_interval |
| all_lights | Virtual MQTT switch toggling all (non-bedroom) lights |
| republic_services | Daily 6AM refresh; MQTT discovery for trash/recycling/status; 9AM day-before reminder; today-pickup notify |
| meeting_indicator | Button toggle → yellow meeting lights → restore previous state |
| global_notify | iOS/Android/other groups; normal + critical + TTS paths |
| area_handler | Cache HA areas/devices; fire EVENT_AREAS_UPDATED; helpers |
| simple_state_linker | Sync grouped entities with grace-period lock |
| automation_manager | Expose HA automations as MQTT switches |
| doorbell / testbutton | Keep as-is structurally (small) |

---

## Phases

Each phase is independently committable. Nothing breaks mid-stream.

### Phase 0 — Branch & baseline
- [ ] `git checkout -b refactor/overhaul`
- [ ] Capture current behavior snapshot (manual smoke test notes) so we can verify after.

### Phase 1 — Shared foundation (`lib/`)
- [ ] Create `appdaemon/apps/lib/` package.
- [ ] `lib/base.py` → `BaseApp(hass.Hass)`:
  - Common `initialize()` template (log startup, parse/validate args).
  - Typed arg helpers: `self.arg(name, default=...)`, `self.required_arg(name)`.
  - Lazy, cached accessors: `self.notifier` (resolves `global_notify`), `self.area_handler`, `self.garage_utils`.
  - Consistent logging prefix.
- [ ] `lib/notify.py` — see "Notifications proposal" below.
- [ ] `lib/mqtt.py`:
  - `MQTTDiscoveryEntity` base (absorbs `automation_manager`'s `MQTTSwitch`/`MQTTNumber` + `all_lights` + `republic_services` publishing).
  - Standard topic convention: `homeassistant/<type>/<object_id>/{config,state,availability,attributes,set}`.
  - LWT/availability helper; discovery payload builder with `device` + `origin` blocks.
  - One `listen_command(cb, topic)` helper (kills the 3 different listen patterns).
- [ ] `lib/time_utils.py`:
  - `parse_time(str|time) -> time` (HH:MM[::SS], AD `parse_time` passthrough).
  - `is_time_between(check, start, end)` overnight-aware (single source — currently in cron_scheduler + fan_auto_off + timer).
  - `seconds_until(now, target_time)` (aware datetimes only; replaces pytz localize).
  - `parse_iso(s) -> aware datetime` (replaces the `strptime(...)+replace('Z','+00:00')` pattern in 3 files).
  - `zoneinfo` only — no `pytz`.

### Phase 2 — Fix active bugs (preserve intent, fix implementation)
- [ ] `door_light_automation.turn_off_lights`: restore the commented-out turn_off loop so door lights actually turn off after timeout.
- [ ] `entity_monitor`: fix config key (`enable_last_seen` everywhere — both apps.yaml and code).
- [ ] `republic_services_schedule`: dedupe double imports; fix 9AM/5PM log mismatch; drop unused `trash_next`/`recycling_next` in `_schedule_reminders`.
- [ ] `all_lights`: publish OFF when no light is on at startup; refresh entity list on switch toggle (or re-query state in `set_state` instead of caching).
- [ ] `utils.py` bugs: remove mutating `group_entities` behavior, fix unreachable code in `find_starting_strings_intersection`, fix `call_light_state_as_service` param shadowing.

### Phase 3 — Kill dead code & consolidate
- [ ] Delete `hello.py`, `state_manager.py`, `cron_scheduler.py` (absorb useful bits into `lib/time_utils.py`).
- [ ] Remove `utils` `global: true` from apps.yaml (no class → meaningless); replace `import utils` with `from lib import ...`.
- [ ] Delete `utils.py` after survivors move.
- [ ] Strip comment graveyards in `utils.py` (gone), `republic_services_schedule.py`, `meeting_indicator.py`, `all_lights.py`.
- [ ] Remove commented apps.yaml blocks: `global_state_manager`, `state_manager`, `virtual_switch`, `light_group_controller`, `advanced_timer`.
- [ ] Merge `appdaemon/requirements.txt` into root `requirements.txt`; drop `deepdiff` (unused), drop `pytz`; keep `croniter`, `requests`.
- [ ] Update README to reflect actual active apps (remove GlobalStateManager/MQTTSwitch API docs that are effectively unused).

### Phase 4 — Unify MQTT & notifications onto `lib/`
- [ ] Migrate `all_lights`, `auto_lock`, `automation_manager`, `republic_services` onto `lib/mqtt.py` (one topic convention, one listen pattern, one discovery builder).
- [ ] Migrate all 5 notifier callers onto the normalized `lib/notify.py` surface (see below).

### Phase 5 — Async + timezone modernization
- [ ] Replace `datetime.now()` (naive) with `self.datetime()` / `get_now()` across `republic_services`, `entity_monitor`.
- [ ] Drop `pytz` (gone with requirements cleanup).
- [ ] `fan_auto_off` → use `lib/time_utils` (delete its local copies).
- [ ] Leave `area_handler` + `simple_state_linker` as-is (already modern async).

### Phase 6 — Repo hygiene
- [ ] Fix `docs/generate_docs.py`: sync `SHORT_NAME_MAP`/`DESCRIPTIONS` with active modules; skip dead ones; delete stale `docs/*.md` for removed apps.
- [ ] Add `.ruff.toml` (lint + format config — does NOT affect container install).
- [ ] Tidy `.gitignore`.
- [ ] Add `pytest` unit tests for `lib/time_utils` and the RS schedule date math (the `test_rs_schedule.py` logic is testable without HA).

### Phase 7 — DESIGN.md (SOP + library catalog) ⭐ NEW
Write `appdaemon/apps/DESIGN.md` — the new-developer (and future-LLM) entry point. This is what prevents regression to the old "cobbled together" pattern.

Contents:

**1. Architecture overview**
- Repo layout (what lives in `lib/` vs `apps/`).
- The app lifecycle: apps inherit `BaseApp`, config comes from `apps.yaml`, global services (`global_notify`, `area_handler`) accessed via `BaseApp` accessors — never via raw `get_app()`.
- Dependency graph: `lib/` ← consumers; `global_notify`/`area_handler` as foundational services with priorities; which apps depend on which.

**2. SOP: adding a new automation (step-by-step checklist)**
```markdown
1. Pick a module name (snake_case). Create `appdaemon/apps/<name>.py`.
2. class <Name>(BaseApp) — do NOT extend hass.Hass directly.
3. Implement initialize(): read args via self.arg(...) / self.required_arg(...).
4. Need notifications? Use self.notifier.send(...). Do NOT call get_app("global_notify").
5. Need MQTT discovery? Use lib/mqtt.py MQTTDiscoveryEntity. Do NOT hand-roll topics.
6. Need time logic? Use lib/time_utils.py. Do NOT reimplement is_time_between/seconds_until.
7. Add an entry to apps.yaml (copy the template from §4 below).
8. If the app has configurable behavior, document the args block inline in apps.yaml.
9. Run docs/generate_docs.py to regenerate docs.
10. Reload AppDaemon; smoke-test; commit.
```

**3. Library catalog (what `lib/` provides)**
A table per module:
```markdown
| Module | Provides | Example |
|--------|----------|---------|
| lib.base | BaseApp, self.notifier, self.area_handler, self.arg() | ... |
| lib.notify | Notifier (send/send_critical/send_tts) | self.notifier.send(message=...) |
| lib.mqtt | MQTTDiscoveryEntity, listen_command, standard topic conventions | ... |
| lib.time_utils | parse_time, is_time_between, seconds_until, parse_iso | is_time_between(now, "21:00", "06:00") |
```

**4. apps.yaml template**
A copy-paste-ready skeleton with the convention (module, class, dependencies, the standard args layout).

**5. Conventions (the rules that prevent rot)**
- All apps extend `BaseApp`, never `hass.Hass` directly.
- Notifications: only via `self.notifier`. Never `get_app("global_notify")`.
- MQTT: only via `lib/mqtt.py`. One topic convention. Never hand-rolled discovery.
- Time: only via `lib/time_utils.py`. Never `pytz`, never naive `datetime.now()`.
- Args: use `self.arg()` / `self.required_arg()`. Never raw `self.args["..."]` for required config.
- No commented-out code; no dead imports. Ruff catches both.
- Behavior changes: preserve intent. If you're changing WHAT an automation does, that's a separate decision from refactoring HOW it's written.

**6. Anti-patterns to avoid** (explicitly listing the old habits so they're recognized):
- `import utils` (use `from lib import ...`).
- `self.get_app("global_notify")` scattered (use `self.notifier`).
- `datetime.now()` naive (use `self.datetime()`).
- `pytz` (use `zoneinfo` via `lib/time_utils`).
- `get_plugin_api("MQTT")` + hand-rolled topics (use `lib/mqtt.py`).
- Copy-pasting `is_time_between` / `seconds_until` (use `lib/time_utils`).
- Commented-out apps.yaml blocks (delete them; git remembers).

---

## Notifications — current state (the inconsistency we're fixing)

`global_notify.py` (the backend) is well-designed. The problem is the callers:

| App | How it gets the notifier | How it calls |
|-----|--------------------------|--------------|
| garage_utils | inline `self.get_app("global_notify")` | `.notify(group="all", title=, message=)` — group kw |
| garage_notify_automation | stored `self.notify_app` | `.notify("all", message=, title=, data=)` — group positional |
| water_sensor_monitor | stored `self.notifier` | `.send_critical(group_name=, message=, title=)` |
| entity_monitor | stored `self.notify_app` | `.notify("all", message=, title=, data=)` |
| republic_services | stored `self.notify_app` | `.notify("family", message=, title=)` |

Problems:
1. `group` is positional in some callers, keyword in others — easy to misuse.
2. The accessor (`get_app("global_notify")`) is repeated/cached 5 different ways.
3. Group names (`"all"`, `"family"`) hardcoded per-caller.
4. Method names differ (`notify` vs `send_critical` vs `send_tts_android`) with inconsistent kw names (`group` vs `group_name`).

### Notifications — proposed change (OPEN for confirmation)

**Keep `global_notify` as the backend** (iOS/Android/other + critical + TTS logic is good). On top of it:

**Option A (CONFIRMED): keyword-only signatures + a single entry point.**
- Normalize all three methods to **keyword-only** args via `*`:
  ```python
  def send(self, *, group, message, title=None, data=None): ...
  def send_critical(self, *, group, message, title="Critical Alert", data=None): ...
  def send_tts(self, *, group, text, title="TTS Alert", volume_max=False, data=None): ...
  ```
  - Consistent kw name `group` (not `group_name`).
  - Consistent kw name `data` (not `additional_data`).
  - `text` for TTS (not `tts_text`).
  - Keyword-only → no more positional/keyword ambiguity. A wrong call fails loudly.
- Provide `lib/notify.py` `Notifier` as the **single accessor** used by all apps:
  ```python
  class Notifier:
      def __init__(self, app):
          self._app = app
          self._backend = None
      @property
      def backend(self):
          if self._backend is None:
              self._backend = self._app.get_app("global_notify")
          return self._backend
      def send(self, *, group=None, message, title=None, data=None):
          self.backend.send(group=group or self._default_group, message=message, title=title, data=data)
      # send_critical, send_tts same shape...
  ```
  - `group=None` → falls back to a `default_notification_group` configured once in `global_notify`'s apps.yaml (e.g. `family`). So simple alerts: `self.notifier.send(message=..., title=...)`.
  - All apps get `self.notifier` from `BaseApp` — no more `get_app("global_notify")` scattered around.
- `global_notify` keeps its three públicas methods (`send`/`send_critical`/`send_tts`), now with uniform keyword-only signatures. Backward-compat: keep `notify()` as a deprecated alias of `send()` during the transition (or just rename callers — there are only 5).

**Option B (minimal): keep method names exactly, only enforce keyword-only + centralize accessor.** Lower churn, same backend, just stops the inconsistency.

Option A is cleaner (single mental model: "everything goes through `self.notifier.send(...)`"); Option B is lower-risk.

**→ CONFIRMED: Option A.**

---

## pyproject.toml — decision

Owner unsure because AppDaemon container auto-installs from `requirements.txt`.

**Decision: keep `requirements.txt` as the install source of truth** (container keeps working unchanged). Tooling config goes in a standalone `.ruff.toml` (no `pyproject.toml` needed). If owner later wants `pyproject.toml` for packaging, we can add it then — it won't change how the container installs.

---

## Phase execution order & safety

Phases 1 → 2 → 3 → 4 → 5 → 6.

- Phases 1–2 add value immediately (shared lib + bug fixes) and don't change behavior.
- Phase 3 deletes dead code (low risk — nothing imports the dead modules).
- Phase 4 is the biggest mechanical churn (MQTT + notify migration) — verify each app after migration.
- Phase 5 is touches-but-doesn't-change-behavior.
- Phase 6 is cosmetic + tooling.

After each phase: reload AppDaemon, smoke-test the affected apps, commit.

---

## Decisions confirmed
1. ✅ Scope change — `lib/` package approved.
2. ✅ Nothing off-limits — preserve behavior/intent strictly.
3. ✅ Shared library — consolidate/redesign for consumers (not 1:1 port).
4. ✅ DESIGN.md (SOP + library catalog) — Phase 7.
5. ✅ Notifications → **Option A**: single `self.notifier.send(...)` entry point,
   keyword-only signatures, default group configured once in `global_notify`'s apps.yaml.
   `global_notify` backend keeps its three internal behaviors (normal/critical/TTS)
   but exposes them through one uniform keyword-only surface via `lib/notify.py`.
6. ✅ Tooling → `.ruff.toml` standalone, no `pyproject.toml`.
   `requirements.txt` remains the single install source of truth for the container.
