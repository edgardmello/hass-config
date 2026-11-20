# Home Assistant 2026.11 Compatibility Upgrade

Fork of [`matt8707/hass-config`](https://github.com/matt8707/hass-config) upgraded from Home Assistant `2023.12.0` to **`2026.11.2`**, plus an adapted self-contained Lovelace dashboard deployed for Edgard's Home Assistant instance.

## Breaking Changes & Modernizations Applied

### 1. Core & Configuration (`configuration.yaml`, `.HA_VERSION`)
- Updated `.HA_VERSION` from `2023.12.0` to `2026.11.2`.
- Removed deprecated/removed `homeassistant.temperature_unit` (now governed by `unit_system: metric`).
- Removed legacy YAML `sensor: - platform: time_date`; templates now read `now()` directly.

### 2. Weather Forecast Migration (`sidebar.yaml`)
- Replaced removed `state_attr(entity, 'forecast')[0]['precipitation']` (removed in HA `2024.3`) with a trigger-based template sensor calling `action: weather.get_forecasts` (`type: hourly`, `response_variable: hourly_forecast`).
- Replaced `sensor.date` lookups with native `now().day` / `now().weekday()`.
- Added `| reject('none')`, `as_datetime(default=none)`, and `is_number(...)` guards so missing/unavailable entities never raise template errors.

### 3. Legacy Template Platform & System Monitor Removals (`packages/*.yaml`)
- **HA `2026.6` removal of legacy `switch: - platform: template`**:
  - Migrated `packages/climate_electrolux.yaml`, `packages/computer_imac.yaml`, and `packages/studio_monitors.yaml` to modern `template: - switch:` syntax (`unique_id`, `default_entity_id`, `name`, `state`, `icon`, `turn_on`, `turn_off`).
- **HA `2024.9` removal of YAML `sensor: - platform: systemmonitor`**:
  - Removed deprecated YAML block from `packages/synology_nas.yaml` (System Monitor is now configured via UI Config Flow).
- **Modern `template:` sensor metadata**:
  - Promoted `name`, `icon`, `unit_of_measurement`, and `device_class` out of `attributes:` to top-level keys in `computer_imac.yaml`, `router_unifi.yaml`, `synology_nas.yaml`, `tablet_galaxy_tab.yaml`, `vacuum_roborock_s55.yaml`, and `version_updates.yaml`.
  - Fixed `timestamp_local(default)` -> `timestamp_local(none)` and numeric-only `sum` in `version_updates.yaml`.
- **HA `2024.8` / `2024.10` modern Automation & Script syntax**:
  - Migrated `trigger:` -> `triggers:`, `platform:` -> `trigger:`, `condition:` -> `conditions:`, `action:` -> `actions:`, and `service:` -> `action:` across all package automations, scripts, and template selects (preserving `event_data.service` on `call_service` event triggers).

### 4. Lovelace, Templates, Popups & Theme (`button_card_templates/`, `popup/`, `themes/tablet.yaml`, `ui-lovelace.yaml`)
- Migrated Lovelace actions from `action: call-service` / `service:` / `service_data:` to `action: perform-action` / `perform_action:` / `data:`.
- Fixed non-dimmable (`onoff`) lights displaying `NaN%` in `circle.yaml` and `light.yaml`, and guarded shadow DOM element lookups in `circle.yaml`, `loader.yaml`, and `lock.yaml`.
- Fixed strict JS variable naming (`let await = ...`) and added optional chaining on `swipeCard?.swiper` and `triggers_update` in `media.yaml`.
- Added safe null checks in `extra_styles.yaml`, `person.yaml` (with inline SVG avatar fallback), and `updates.yaml`.
- Updated `themes/tablet.yaml` for HA `2025/2026` frontend (`ha-wa-dialog`, `--ha-dialog-surface-background`, `hui-view-container`, and Swipe Card v3 `.swiper` selector).

## Adapted Dashboard (`dashboards/build_edgard_dashboard.py`)

Generates [`dashboards/hass-config-edgard.yaml`](dashboards/hass-config-edgard.yaml) and deploys it directly to Home Assistant at `/hass-config` (`Hass Config`):
- Uses Mattias's exact dark mesh background (`www/background.png`), animated SVG icons (`button_card_templates/icons.yaml`), inline SVG loader (`www/loader.svg`), responsive `custom:grid-layout`, left live sidebar, 6 room/feature grids (`Sala`, `Escritório`, `Suíte`, `Mídia` swipe card, `Cozinha`, `Casa`), and bottom notification footer bar.
- Self-contained CSS variables & `card_mod` styling (works out-of-the-box without manually installing `tablet.yaml` into `/config/themes/`).
- Uses native **Bubble Card** popups (`#popup-sala`, `#popup-escritorio`, `#popup-suite`, `#popup-cozinha`, `#popup-sistema`, `#popup-energia`, `#popup-aspirador`, `#popup-clima`, `#popup-cameras`, `#popup-updates`) — zero `browser_mod` dependency.
- Re-deploy anytime with:
  ```bash
  uv run --with pyyaml --with websockets python3 dashboards/build_edgard_dashboard.py --deploy
  ```
