#!/usr/bin/env python3
"""Build and deploy the adapted matt8707/hass-config dashboard for Home Assistant 2026.11."""

import asyncio
import base64
import json
import os
import subprocess
import sys
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
HA_WS_URL = os.environ.get("HOMEASSISTANT_WS_URL", "ws://10.10.1.10/api/websocket")
DASHBOARD_URL_PATH = "hass-config"
DASHBOARD_TITLE = "Hass Config"
DASHBOARD_ICON = "mdi:tablet-dashboard"


def get_ha_token() -> str:
    env_tok = os.environ.get("HOMEASSISTANT_TOKEN")
    if env_tok:
        return env_tok
    user = subprocess.check_output(["whoami"], text=True).strip()
    for svc in ("HOMEASSISTANT_MCP_TOKEN", "HOMEASSISTANTTOKEN"):
        res = subprocess.run(
            ["security", "find-generic-password", "-a", user, "-s", svc, "-w"],
            capture_output=True,
            text=True,
        )
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip()
    raise RuntimeError("Could not find Home Assistant token in Keychain or environment.")


def load_b64_data_uri(rel_path: str, mime: str) -> str:
    raw = (ROOT / rel_path).read_bytes()
    return f"data:{mime};base64,{base64.b64encode(raw).decode('ascii')}"


def load_icon_templates() -> dict:
    with open(ROOT / "button_card_templates" / "icons.yaml", "r", encoding="utf-8") as f:
        icons = yaml.safe_load(f)
    # Add custom lock SVG matching Mattias's 50x50 aesthetic
    icons["icon_lock"] = {
        "styles": {"custom_fields": {"icon": [{"width": "72%"}, {"margin-left": "-10%"}]}},
        "custom_fields": {
            "icon": """[[[
  const locked = entity && entity.state === 'locked';
  const color = locked ? '#9da0a2' : '#3182b7';
  const shackle = locked
    ? 'M16 22v-6a9 9 0 0 1 18 0v6'
    : 'M16 22v-6a9 9 0 0 1 17.5-3';
  return `<svg viewBox="0 0 50 50">
    <path d="${shackle}" fill="none" stroke="${color}" stroke-width="4.2" stroke-linecap="round"/>
    <rect x="11" y="22" width="28" height="22" rx="5" fill="${color}"/>
    <circle cx="25" cy="31.5" r="2.8" fill="#1c2021"/>
    <path d="M25 33v4.5" stroke="#1c2021" stroke-width="2.4" stroke-linecap="round"/>
  </svg>`;
]]]"""
        },
    }
    return icons


def grid_card_mod() -> dict:
    return {
        "style": {
            ".": """
              hui-grid-card {
                padding-bottom: 1vw;
              }
            """,
            "$": """
              h1 {
                font-size: 2.3vw !important;
                line-height: 1.1 !important;
                font-weight: 600 !important;
                color: rgba(255, 255, 255, 0.82) !important;
                padding: 0.2vw 0 1.4vw 0 !important;
                margin: 0 !important;
                letter-spacing: -0.02vw !important;
                width: 100%;
              }
              @media screen and (max-width: 1200px) {
                h1 {
                  font-size: 3.3vw !important;
                  padding: 0.4vw 0 1.8vw 0 !important;
                }
              }
              @media screen and (max-width: 800px) {
                h1 {
                  font-size: 5.5vw !important;
                  line-height: 1.2 !important;
                  padding: 2vw 0 2.5vw 0 !important;
                }
              }
            """,
        }
    }


def popup_bubble_styles() -> str:
    return """
      .bubble-pop-up-container {
        background: rgba(26, 30, 32, 0.96) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
      }
      .bubble-header-container {
        background: rgba(200, 218, 222, 0.05) !important;
        border-bottom: 1px solid rgba(0, 0, 0, 0.28) !important;
      }
      ha-card {
        --ha-card-background: rgba(255, 255, 255, 0.04);
        --ha-card-border-width: 0px;
        --ha-card-border-radius: 14px;
      }
    """


def build_templates(loader_uri: str) -> dict:
    icons = load_icon_templates()

    templates = {
        "settings": {
            "variables": {
                "translate_unknown": "Desconhecido",
                "translate_idle": "Ocioso",
                "translate_home": "Em casa",
                "translate_not_home": "Fora",
                "translate_on": "Ligado",
                "translate_off": "Desligado",
                "translate_cool": "Resfriando",
                "translate_heat": "Aquecendo",
                "translate_dry": "Desumidif.",
                "translate_auto": "Auto",
                "translate_fan_only": "Ventilar",
                "translate_playing": "Tocando",
                "translate_paused": "Pausado",
                "translate_standby": "Standby",
                "translate_locked": "Trancada",
                "translate_unlocked": "Destrancada",
            }
        },
        "extra_styles": {
            "extra_styles": """[[[
  var light_color = 'var(--button-card-light-color, #3182b7)';
  if (entity) {
      if (entity.entity_id.split('.')[0] === 'light' && variables.state_on) {
          let theme_var = 'hsl(204, 58%, 38%)',
              is_color_temp = entity.attributes.color_mode === 'color_temp';
          if (is_color_temp && entity.attributes.brightness) {
              let regex_pattern = /(\\d+)(?!.*\\d)/g,
                  match = theme_var.match(regex_pattern),
                  brightness = entity.attributes.brightness / 2.54;
              if (match) {
                  let lightness = parseFloat(match[0]),
                      calc_lightness = brightness * 20 / 100 + (lightness - 10);
                  light_color = theme_var.replace(regex_pattern, calc_lightness);
              }
          }
      }
  }
  let tpl = Array.isArray(this._config?.template)
      ? this._config.template
      : [this._config?.template || ''];
  return `
    :host {
      --state-icon-color: #9da0a2;
      --state-icon-active-color: #3182b7;
      --button-card-font-size: 1.32vw;
      --button-card-font-weight: 500;
      --button-card-letter-spacing: -0.02vw;
      --button-card-border-radius: 10%;
      --footer-card-font-size: 1.15vw;
      --footer-card-icon-size: 1.45vw;
      --footer-card-padding-v: 0.7vw;
      --footer-card-padding-h: 1.15vw;
      --footer-card-border-radius: 0.65vw;
      --footer-notify-font-size: 0.85vw;
      --footer-notify-box-size: 1.75vw;
      --footer-notify-top: -0.75vw;
      --footer-notify-right: -0.75vw;
      --card-portrait: 1.4;
      --card-phone: 2.25;
      --ha-card-border-width: 0px;
      --ha-card-box-shadow: none;
      font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", Roboto, system-ui, sans-serif;
    }

    svg {
      --light-color: ${
        variables.state_on && entity?.attributes?.brightness
            ? light_color
            : variables.state_on
                ? '#3182b7'
                : '#9da0a2'
      };
    }

    .light-color {
      fill: var(--light-color);
      transition: all 0.25s ease-out;
    }

    #container {
      text-align: left !important;
      z-index: 1;
    }

    #card {
      padding: 10.9% 9.9% 8.9% 10.9%;
      box-shadow: none !important;
      border-width: 0 !important;
    }

    #state::first-letter {
      text-transform: uppercase;
    }

    #name, #state {
      font-size: var(--button-card-font-size);
      font-weight: var(--button-card-font-weight);
      letter-spacing: var(--button-card-letter-spacing);
    }

    @media screen and (max-width: 1200px) {
      #name, #state {
        font-size: calc(var(--button-card-font-size) * var(--card-portrait));
      }
    }
    @media screen and (max-width: 800px) {
      #name, #state {
        font-size: calc(var(--button-card-font-size) * var(--card-phone));
      }
    }

    ${tpl.includes('light') ? `
      #circle_slider {
        opacity: 0;
        appearance: none;
        transform: rotate(270deg);
        width: 90%;
        position: absolute;
        pointer-events: none;
        cursor: grab;
        left: 26%;
        margin-top: 13%;
      }
      #circle_slider::-webkit-slider-thumb {
        pointer-events: initial;
        appearance: none;
        width: 3vw;
        height: 3vw;
        border-radius: 50%;
      }
    ` : ''}

    ${tpl.includes('conditional_media') ? `
      :host {
        --blur-intensity: blur(4.5px) brightness(0.75);
      }
      @media screen and (max-width: 800px) {
        :host {
          --blur-intensity: blur(2.5px) brightness(0.75);
        }
      }
      #container {
        overflow: hidden;
      }
      .marquee {
        animation: marquee 20s linear infinite;
      }
      @keyframes marquee {
        from { transform: translateX(0%); }
        to { transform: translateX(-50%); }
      }
    ` : ''}

    ${tpl.includes('footer') ? `
      :host {
        --footer-portrait: 1.4;
        --footer-phone: 2.7;
      }
      #name {
        font-size: var(--footer-card-font-size);
        padding: var(--footer-card-padding-v) var(--footer-card-padding-h);
        letter-spacing: 0.04vw;
      }
      ha-icon {
        width: var(--footer-card-icon-size);
        vertical-align: -12%;
        padding-right: 0.25vw;
        opacity: 0.55;
      }
      #card {
        padding: 0 !important;
        border-radius: var(--footer-card-border-radius) !important;
        background: rgba(115, 115, 115, 0.14) !important;
        border: 1px solid rgba(155, 165, 170, 0.18) !important;
      }
      #card:hover {
        background: rgba(150, 160, 165, 0.24) !important;
      }
      #notify {
        font-size: var(--footer-notify-font-size);
        width: var(--footer-notify-box-size);
        height: var(--footer-notify-box-size);
        line-height: var(--footer-notify-box-size);
        top: var(--footer-notify-top);
        right: var(--footer-notify-right);
      }
      @media screen and (max-width: 1200px) {
        #name {
          font-size: calc(var(--footer-card-font-size) * var(--footer-portrait));
          padding: calc(var(--footer-card-padding-v) * var(--footer-portrait)) calc(var(--footer-card-padding-h) * var(--footer-portrait));
        }
        ha-icon {
          width: calc(var(--footer-card-icon-size) * var(--footer-portrait));
        }
        #card {
          border-radius: calc(var(--footer-card-border-radius) * var(--footer-portrait)) !important;
          margin: 0.4vw 0.5vw;
        }
        #notify {
          font-size: calc(var(--footer-notify-font-size) * var(--footer-portrait));
          width: calc(var(--footer-notify-box-size) * var(--footer-portrait));
          height: calc(var(--footer-notify-box-size) * var(--footer-portrait));
          line-height: calc(var(--footer-notify-box-size) * var(--footer-portrait));
        }
      }
      @media screen and (max-width: 800px) {
        #name {
          font-size: calc(var(--footer-card-font-size) * var(--footer-phone));
          padding: calc(var(--footer-card-padding-v) * var(--footer-phone)) calc(var(--footer-card-padding-h) * var(--footer-phone));
        }
        ha-icon {
          width: calc(var(--footer-card-icon-size) * var(--footer-phone));
        }
        #card {
          border-radius: calc(var(--footer-card-border-radius) * var(--footer-phone)) !important;
          margin: 1vw;
        }
        #notify {
          font-size: calc(var(--footer-notify-font-size) * var(--footer-phone));
          width: calc(var(--footer-notify-box-size) * var(--footer-phone));
          height: calc(var(--footer-notify-box-size) * var(--footer-phone));
          line-height: calc(var(--footer-notify-box-size) * var(--footer-phone));
          top: -1.6vw;
          right: -1.6vw;
        }
      }
    ` : ''}
  `;
]]]"""
        },
        "base": {
            "template": ["settings", "extra_styles"],
            "variables": {
                "state_on": "[[[ return ['on', 'home', 'cool', 'heat', 'dry', 'auto', 'fan_only', 'playing', 'unlocked'].indexOf(!entity || entity.state) !== -1; ]]]",
                "state": "[[[ return !entity || entity.state; ]]]",
                "entity_id": "[[[ return !entity || entity.entity_id; ]]]",
                "entity_picture": "[[[ return !entity || entity.attributes.entity_picture; ]]]",
                "timeout": "[[[ return !entity || Date.now() - Date.parse(entity.last_changed); ]]]",
            },
            "aspect_ratio": "1/1",
            "show_state": True,
            "show_icon": False,
            "state_display": """[[[
  const stateDict = {
    'on': variables.translate_on,
    'off': variables.translate_off,
    'cool': variables.translate_cool,
    'heat': variables.translate_heat,
    'dry': variables.translate_dry,
    'auto': variables.translate_auto,
    'fan_only': variables.translate_fan_only,
    'playing': variables.translate_playing,
    'paused': variables.translate_paused,
    'idle': variables.translate_idle,
    'standby': variables.translate_standby,
    'locked': variables.translate_locked,
    'unlocked': variables.translate_unlocked,
  };
  if (variables.state === true) return variables.translate_unknown;
  return stateDict[variables.state] ?? variables.state;
]]]""",
            "tap_action": {
                "card_bounce": """[[[
  if (this.getElementsByTagName("style").length === 0) {
      let mq = window.matchMedia('(max-width: 800px)').matches;
      let style = document.createElement('style');
      style.innerHTML = `
          @keyframes card_bounce {
              0%   { transform: scale(1); }
              10%  { transform: scale(${ mq ? '0.92' : '0.94' }); }
              25%  { transform: scale(1); }
              30%  { transform: scale(${ mq ? '0.96' : '0.98' }); }
              100% { transform: scale(1); }
          }
      `;
      this.appendChild(style);
  }
  let duration = 800;
  this.style.animation = `card_bounce ${duration}ms cubic-bezier(0.22, 1, 0.36, 1)`;
  window.setTimeout(() => { this.style.animation = "none"; }, duration + 100);
]]]""",
                "action": "toggle",
                "haptic": "medium",
            },
            "double_tap_action": {"action": "more-info", "haptic": "success"},
            "hold_action": {"action": "more-info"},
            "styles": {
                "grid": [
                    {"grid-template-areas": '"icon circle"\n"n n"\n"s s"'},
                    {"grid-template-columns": "repeat(2, 1fr)"},
                    {"grid-template-rows": "auto repeat(2, min-content)"},
                    {"gap": "1.3%"},
                    {"align-items": "start"},
                ],
                "name": [{"justify-self": "start"}, {"line-height": "121%"}],
                "state": [{"justify-self": "start"}, {"line-height": "115%"}],
                "card": [
                    {"border-radius": "var(--button-card-border-radius, 10%)"},
                    {"border-width": 0},
                    {"-webkit-tap-highlight-color": "rgba(0,0,0,0)"},
                    {"transition": "background-color 0.25s ease, color 0.25s ease"},
                    {"--mdc-ripple-color": "[[[ return variables.state_on ? 'rgb(0, 0, 0)' : '#97989c'; ]]]"},
                    {"color": "[[[ return variables.state_on ? '#4b5254' : '#97989c'; ]]]"},
                    {"background-color": "[[[ return variables.state_on ? 'rgba(255, 255, 255, 0.85)' : 'rgba(115, 115, 115, 0.25)'; ]]]"},
                ],
            },
        },
        "loader": {
            "custom_fields": {
                "loader": f'<img src="{loader_uri}" width="100%">'
            },
            "tap_action": {
                "loader": """[[[
  if (entity) {
      let elt = this.shadowRoot,
          loader = (id, style) => {
            let el = elt?.getElementById(id);
            if (el) {
              el.style.display = style;
              window.setTimeout(() => {
                let l = elt?.getElementById('loader');
                if (l) l.style.display = 'none';
              }, 8000);
            }
          };
      loader('circle', 'none');
      loader('loader', 'initial');
  }
]]]"""
            },
            "styles": {
                "custom_fields": {
                    "loader": [
                        {"display": "none"},
                        {"top": "-6%"},
                        {"right": "-3.5%"},
                        {"width": "52%"},
                        {"position": "absolute"},
                        {"opacity": 0.5},
                        {"pointer-events": "none"},
                        {"filter": "[[[ return variables.state_on ? 'none' : 'invert(1)'; ]]]"},
                    ]
                }
            },
        },
        "circle": {
            "styles": {
                "card": [
                    {"--c-stroke-color-on": "#b0b0b0"},
                    {"--c-stroke-color-off": "none"},
                    {"--c-fill-color-on": "none"},
                    {"--c-fill-color-off": "rgba(255,255,255,0.04)"},
                    {"--c-stroke-width": 2.3},
                    {"--c-stroke-width-dragging": 4},
                    {"--c-font-color": "#97989c"},
                    {"--c-font-size": "13.5px"},
                    {"--c-unit-font-size": "9.5px"},
                    {"--c-font-weight": 700},
                    {"--c-letter-spacing": "-0.02rem"},
                ],
                "custom_fields": {
                    "circle": [
                        {"display": "initial"},
                        {"width": "88%"},
                        {"margin": "-3% 2% 0 0"},
                        {"justify-self": "end"},
                        {"opacity": 1},
                    ]
                },
            },
            "custom_fields": {
                "circle": """[[[
  if (entity) {
      let r = 22.1,
          c = r * 2 * Math.PI,
          tspan = '<tspan dx=".2" dy="-.4">',
          domain = entity.entity_id.split('.')[0],
          state = variables.state_on,
          input = variables.circle_input,
          unit = variables.circle_input_unit || ' ';

      let circle = (st, val, u, pct) => {
          let showSlider = domain === 'light' && typeof val === 'number' && !Number.isNaN(val);
          let dashPct = typeof pct === 'number' && !Number.isNaN(pct)
              ? Math.max(0, Math.min(100, pct))
              : (typeof val === 'number' && !Number.isNaN(val) ? Math.max(0, Math.min(100, val)) : 100);
          return `
            <svg viewBox="0 0 50 50">
              <style>
                circle {
                  transform: rotate(-90deg);
                  transform-origin: 50% 50%;
                  stroke-dasharray: ${c};
                  stroke-dashoffset: ${c - dashPct / 100 * c};
                  stroke-width: var(--c-stroke-width);
                  stroke: ${st ? 'var(--c-stroke-color-on)' : 'var(--c-stroke-color-off)'};
                  fill: ${st ? 'var(--c-fill-color-on)' : 'var(--c-fill-color-off)'};
                }
                text {
                  font-size: var(--c-font-size);
                  font-weight: var(--c-font-weight);
                  letter-spacing: var(--c-letter-spacing);
                  fill: ${st ? '#4b5254' : 'var(--c-font-color)'};
                }
                tspan {
                  font-size: var(--c-unit-font-size);
                }
                #circle_value, tspan {
                  text-anchor: middle;
                  dominant-baseline: central;
                }
              </style>
              <circle id="circle_stroke" cx="25" cy="25" r="${r}"/>
              <text id="circle_value" x="50%" y="52%">${val}${tspan}${u}</tspan></text>
            </svg>
            ${showSlider ? `<input id="circle_slider" type="range" min="0" max="100" value="${val}">` : ''}
          `;
      };

      if (domain === 'light' && state && typeof input === 'number' && !Number.isNaN(input)) {
          setTimeout(() => {
              let elt = this.shadowRoot,
                  circle_slider = elt?.getElementById('circle_slider'),
                  circle_value = elt?.getElementById('circle_value'),
                  circle_stroke = elt?.getElementById('circle_stroke');
              if (!circle_slider || !circle_value || !circle_stroke) return;
              circle_slider.style.top = `${(circle_slider.value - 50) / 1.66 - 1}%`;
              ['click', 'input', 'mousedown', 'mouseup', 'touchstart', 'touchend'].forEach((ev) => {
                  circle_slider.addEventListener(ev, function(event) {
                      if (event.target === this) {
                          event.stopPropagation();
                          circle_value.innerHTML = `${this.value}${tspan}${unit}</tspan>`;
                          circle_stroke.style.strokeDashoffset = c - this.value / 100 * c;
                          circle_stroke.style.strokeWidth = 'var(--c-stroke-width-dragging)';
                          if (event.type === 'mouseup' || event.type === 'touchend') {
                              hass.callService('light', 'turn_on', {
                                  entity_id: entity.entity_id,
                                  brightness_pct: this.value
                              });
                          }
                      }
                  }, { passive: true });
              });
          }, 0);
          return circle(state, input, unit, input);
      } else if (domain === 'person') {
          let fmt = ms => {
              let s = ms / 1e3, m = ms / 6e4, h = ms / 36e5, d = ms / 864e5;
              return s < 60 ? parseInt(s) + 's' : m < 60 ? parseInt(m) + 'm' : h < 24 ? parseInt(h) + 'h' : parseInt(d) + 'd';
          };
          let diff = fmt(Math.max(0, Date.now() - Date.parse(entity.last_changed)));
          return circle(state, diff, ' ', 100);
      } else if (domain === 'climate' && input != null && input !== '') {
          return circle(state, input, unit, 100);
      } else if (variables.circle_always && input != null && input !== '') {
          return circle(state, input, unit, 100);
      } else if (variables.state_on && domain !== 'light' && input != null && input !== '') {
          return circle(state, input, unit, 100);
      }
  }
]]]"""
            },
        },
        "light": {
            "template": ["base", "circle", "loader"],
            "variables": {
                "circle_input": """[[[
  if (entity) {
      let child = entity.attributes.entity_id,
          raw = child && states[child[0]]?.attributes?.brightness != null
              ? states[child[0]].attributes.brightness
              : entity.attributes.brightness;
      if (raw == null) return undefined;
      let brightness = Math.round(raw / 2.54);
      return brightness === 0 && entity.state !== 'off' ? 1 : brightness;
  }
]]]""",
                "circle_input_unit": "%",
            },
        },
        "person": {
            "template": ["base", "circle"],
            "state_display": """[[[
  if (entity) {
      return variables.state === 'home'
          ? variables.translate_home
          : variables.state === 'not_home'
              ? variables.translate_not_home
              : variables.state;
  }
  return variables.translate_unknown;
]]]""",
            "triggers_update": ["sensor.time_date"],
            "tap_action": {"action": "more-info"},
            "styles": {
                "custom_fields": {
                    "icon": [
                        {"clip-path": "circle()"},
                        {"width": "82%"},
                        {"pointer-events": "none"},
                        {"display": "grid"},
                    ]
                }
            },
            "custom_fields": {
                "icon": """[[[
  if (entity && variables.entity_picture) {
      return `<img src="${variables.entity_picture}" width="100%">`;
  }
  const initials = (entity?.attributes?.friendly_name || '?')
      .split(' ').map(w => w[0]).slice(0, 2).join('').toUpperCase();
  const bg = variables.state_on ? '#3182b7' : 'rgba(157,160,162,0.22)';
  const fg = variables.state_on ? '#ffffff' : '#d2d6d8';
  return `<svg viewBox="0 0 50 50">
    <circle cx="25" cy="25" r="25" fill="${bg}"/>
    <text x="50%" y="53%" text-anchor="middle" dominant-baseline="central"
      font-size="18" font-weight="600" fill="${fg}">${initials}</text>
  </svg>`;
]]]"""
            },
        },
        "base_media": {
            "template": ["settings"],
            "variables": {
                "media_on": "[[[ return !entity || ['playing', 'paused', 'on'].indexOf(entity.state) !== -1; ]]]",
                "media_off": "[[[ return !entity || ['off', 'idle', 'standby', 'unknown', 'unavailable'].indexOf(entity.state) !== -1; ]]]",
            },
            "tap_action": {
                "action": "[[[ return variables.media_on ? 'perform-action' : 'more-info'; ]]]",
                "perform_action": "media_player.media_play_pause",
                "data": {"entity_id": "[[[ return variables.entity_id; ]]]"},
            },
            "double_tap_action": {"action": "more-info"},
            "styles": {
                "card": [
                    {
                        "color": """[[[
  return variables.media_on && !variables.entity_picture
      ? '#4b5254'
      : variables.media_off ? '#97989c' : '#efefef';
]]]"""
                    },
                    {
                        "text-shadow": """[[[
  return variables.media_off || !variables.entity_picture
      ? 'none'
      : '1px 1px 5px rgba(18, 22, 23, 0.9)';
]]]"""
                    },
                ]
            },
        },
        "media": {
            "template": ["base", "base_media"],
            "styles": {
                "custom_fields": {
                    "icon": [
                        {"width": "70%"},
                        {"margin-left": "2%"},
                        {"fill": "#9da0a2"},
                        {
                            "display": """[[[
  return variables.media_off || !variables.entity_picture ? 'initial' : 'none';
]]]"""
                        },
                    ]
                },
                "card": [
                    {"background-color": "none"},
                    {"background-size": "cover"},
                    {"background-position": "center"},
                    {
                        "background-image": """[[[
  return variables.media_on && !variables.entity_picture
      ? 'linear-gradient(0deg, rgba(255, 255, 255, 0.85) 0%, rgba(255, 255, 255, 0.85) 100%)'
      : variables.media_off
          ? 'linear-gradient(0deg, rgba(115, 115, 115, 0.25) 0%, rgba(115, 115, 115, 0.25) 100%)'
          : `linear-gradient(0deg, rgba(0,0,0,.82) 0%, rgba(0,0,0,0) 100%), url(${variables.entity_picture})`;
]]]"""
                    },
                ],
            },
        },
        "conditional_media": {
            "aspect_ratio": "1000/996",
            "template": ["base", "base_media", "icon_play_pause"],
            "triggers_update": [
                "media_player.tv_sala_androidtv",
                "media_player.sala_echo_show_8",
                "media_player.suite_echo_dot_suite",
                "media_player.google_home_escritorio",
                "media_player.tv_samsung_suite",
                "media_player.todo_lugar",
            ],
            "variables": {
                "active_player": """[[[
  const players = [
    'media_player.tv_sala_androidtv',
    'media_player.sala_echo_show_8',
    'media_player.suite_echo_dot_suite',
    'media_player.google_home_escritorio',
    'media_player.tv_samsung_suite',
    'media_player.todo_lugar'
  ];
  for (const p of players) {
    if (states[p] && ['playing', 'paused'].includes(states[p].state)) return states[p];
  }
  for (const p of players) {
    if (states[p] && states[p].state === 'on') return states[p];
  }
  return states['media_player.tv_sala_androidtv'] || entity;
]]]""",
                "state_on": "[[[ return ['playing', 'paused', 'on'].includes(variables.active_player?.state); ]]]",
                "media_on": "[[[ return ['playing', 'paused', 'on'].includes(variables.active_player?.state); ]]]",
                "media_off": "[[[ return !['playing', 'paused', 'on'].includes(variables.active_player?.state); ]]]",
                "entity_picture": "[[[ return variables.active_player?.attributes?.entity_picture; ]]]",
            },
            "name": "[[[ return variables.active_player?.attributes?.friendly_name || 'Mídia'; ]]]",
            "state_display": """[[[
  const p = variables.active_player;
  if (!p) return 'Ocioso';
  const artist = p.attributes?.media_artist;
  const title = p.attributes?.media_title;
  const app = p.attributes?.app_name;
  if (artist && title) return `${artist} - ${title}`;
  if (title) return title;
  if (app) return app;
  if (p.state === 'on') return 'Ligada';
  if (p.state === 'playing') return 'Tocando';
  if (p.state === 'paused') return 'Pausado';
  return 'Nada tocando · Deslize →';
]]]""",
            "tap_action": {
                "action": "perform-action",
                "perform_action": "media_player.media_play_pause",
                "data": {"entity_id": "[[[ return variables.active_player?.entity_id || 'media_player.tv_sala_androidtv'; ]]]"},
            },
            "double_tap_action": {"action": "more-info"},
            "styles": {
                "grid": [{"gap": "0.65%"}],
                "name": [{"padding": "0.2vw"}, {"margin": "-0.2vw"}],
                "state": [{"padding-bottom": "5.25%"}, {"max-width": "unset"}, {"overflow": "hidden"}, {"text-overflow": "ellipsis"}],
                "card": [
                    {"padding": "5.75% 5.25% 0 5.75%"},
                    {"border-radius": "calc(var(--button-card-border-radius, 10%) / 2)"},
                    {"background": "rgba(115, 115, 115, 0.25) center center/cover no-repeat"},
                    {
                        "background-image": """[[[
  const pic = variables.entity_picture;
  if (pic) return `linear-gradient(0deg, rgba(16,20,22,0.88) 0%, rgba(16,20,22,0.52) 28%, rgba(0,0,0,0.08) 55%, rgba(0,0,0,0.2) 100%), url("${pic}")`;
  if (variables.state_on) return 'linear-gradient(0deg, rgba(16,20,22,0.72) 0%, rgba(16,20,22,0.25) 32%, transparent 55%), radial-gradient(circle at 20% 20%, rgba(49,130,183,0.42), rgba(26,34,38,0.88))';
  return 'linear-gradient(0deg, rgba(16,20,22,0.68) 0%, rgba(16,20,22,0.22) 32%, transparent 55%), radial-gradient(circle at 80% 20%, rgba(82,102,112,0.28), rgba(28,32,34,0.65))';
]]]"""
                    },
                    {"color": "#efefef"},
                    {"text-shadow": "1px 1px 5px rgba(18, 22, 23, 0.9)"},
                ],
                "custom_fields": {
                    "icon": [
                        {"width": "28%"},
                        {"fill": "[[[ return variables.state_on ? 'rgba(255, 255, 255, 0.85)' : '#9da0a2'; ]]]"},
                    ],
                },
            },
        },
        "sidebar": {
            "show_state": False,
            "show_icon": False,
            "triggers_update": [
                "sensor.time_date",
                "weather.openweathermap",
                "light.sala_central",
                "light.sala_led_sofa",
                "light.sala_spot_sofa",
                "light.sala_mesa_jantar",
                "light.sala_entrada",
                "light.sala_banh_social",
                "light.cozinha_central",
                "light.cozinha_bancada",
                "light.cozinha_lavanderia",
                "light.escritorio_spot_escritorio_led",
                "light.suite_ventilador",
                "light.suite_closet",
                "light.quarto_suite_banheiro_espelho",
                "light.hall_light_switch_top",
                "light.hall_light_switch_bottom",
                "climate.escritorio_ar_condicionado",
                "switch.suite_ac",
                "switch.sala_ac",
                "fan.suite_ventilador_2",
                "media_player.tv_sala_androidtv",
                "media_player.tv_samsung_suite",
                "switch.escritorio_computador",
                "switch.escritorio_monitor",
                "vacuum.escritorio_eufy_x10_pro",
                "lock.kuanttum_delta_pro_operate_lock",
                "input_boolean.modo_visitas",
                "input_boolean.faxina",
                "input_boolean.vacation_mode",
                "sensor.sala_varanda_escritorio_power",
                "sensor.daily_energy",
                "sensor.monthly_energy_cost",
                "sensor.0xa4c1388ad4a9a0b6_battery",
                "sensor.0xa4c13818e2a13578_battery",
                "sensor.0xa4c138f397b856f0_battery",
                "sensor.0x00158d00048740a5_battery",
                "sensor.0x00158d000244775f_battery",
                "sensor.0x00158d0005bd5c27_battery",
                "sensor.0x00158d0004110926_battery",
                "sensor.0x00158d00041d46d5_battery",
                "sensor.0x00158d00045b039a_battery",
                "sensor.0x00158d00047bba26_battery",
                "sensor.0x00158d00054d601a_battery",
                "sensor.0x00158d00045d75bf_battery",
                "sensor.0x00158d00044ea7ba_battery",
            ],
            "tap_action": {"action": "none"},
            "name": """[[[
  const now = new Date();
  const hh = String(now.getHours()).padStart(2, '0');
  const mm = String(now.getMinutes()).padStart(2, '0');
  const days = ['Domingo', 'Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado'];
  const months = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'];
  const dateStr = `${days[now.getDay()]}<br>${now.getDate()} de ${months[now.getMonth()]}`;

  const h = now.getHours();
  let greet = 'Boa noite 😌';
  if (h < 6) greet = 'Boa madrugada 😴';
  else if (h < 12) greet = 'Bom dia ☕';
  else if (h < 18) greet = 'Boa tarde 😎';

  const lightIds = [
    'light.sala_central', 'light.sala_led_sofa', 'light.sala_spot_sofa',
    'light.sala_mesa_jantar', 'light.sala_entrada', 'light.sala_banh_social',
    'light.cozinha_central', 'light.cozinha_bancada', 'light.cozinha_lavanderia',
    'light.escritorio_spot_escritorio_led', 'light.suite_ventilador',
    'light.suite_closet', 'light.quarto_suite_banheiro_espelho',
    'light.hall_light_switch_top', 'light.hall_light_switch_bottom'
  ];
  const devIds = [
    ['climate.escritorio_ar_condicionado', 'AC Escritório'],
    ['switch.suite_ac', 'AC Suíte'],
    ['switch.sala_ac', 'AC Sala'],
    ['fan.suite_ventilador_2', 'Ventilador'],
    ['media_player.tv_sala_androidtv', 'TV Sala'],
    ['media_player.tv_samsung_suite', 'TV Suíte'],
    ['switch.escritorio_computador', 'PC'],
    ['switch.escritorio_monitor', 'Monitor']
  ];

  const lightsOn = lightIds.filter(id => states[id]?.state === 'on');
  const devsOn = devIds
    .filter(([id]) => ['on', 'cool', 'heat', 'dry', 'auto', 'fan_only', 'playing'].includes(states[id]?.state))
    .map(([, label]) => label);

  let activeParts = [];
  if (lightsOn.length === 1) {
    activeParts.push(states[lightsOn[0]]?.attributes?.friendly_name || '1 luz');
  } else if (lightsOn.length > 1) {
    activeParts.push(`${lightsOn.length} luzes`);
  }
  activeParts = activeParts.concat(devsOn);
  let activeStr = activeParts.length === 0
    ? `<font color="#6a7377">Tudo desligado</font>`
    : activeParts.length === 1
      ? `${activeParts[0]} ligado`
      : `${activeParts.slice(0, -1).join(', ')} e ${activeParts[activeParts.length - 1]} ligados`;

  const w = states['weather.openweathermap'];
  const condMap = {
    'sunny': 'Ensolarado', 'clear-night': 'Céu limpo', 'cloudy': 'Nublado',
    'partlycloudy': 'Parc. nublado', 'rainy': 'Chuva', 'pouring': 'Chuva forte',
    'lightning-rainy': 'Tempestade', 'fog': 'Neblina', 'windy': 'Ventando'
  };
  let weatherStr = '';
  if (w && w.state !== 'unavailable') {
    const t = Math.round(w.attributes.temperature);
    const feels = w.attributes.apparent_temperature != null ? Math.round(w.attributes.apparent_temperature) : t;
    const hum = w.attributes.humidity;
    const cond = condMap[w.state] || w.state;
    weatherStr = `${cond} · ${t}°C (sensação ${feels}°C) · ${hum}%`;
  }

  const vac = states['vacuum.escritorio_eufy_x10_pro'];
  let vacStr = '';
  if (vac?.state === 'cleaning') vacStr = '<b>🤖 Eufy X10 aspirando</b>';
  else if (vac?.state === 'returning') vacStr = '<b>🤖 Eufy X10 voltando à base</b>';

  let modeParts = [];
  if (states['lock.kuanttum_delta_pro_operate_lock']?.state === 'unlocked') modeParts.push('🔓 Porta destrancada');
  if (states['input_boolean.modo_visitas']?.state === 'on') modeParts.push('👥 Modo Visitas');
  if (states['input_boolean.faxina']?.state === 'on') modeParts.push('🧹 Modo Faxina');
  if (states['input_boolean.vacation_mode']?.state === 'on') modeParts.push('✈️ Modo Férias');
  const modeStr = modeParts.length ? `<b>${modeParts.join(' · ')}</b>` : '';

  const pwr = parseFloat(states['sensor.sala_varanda_escritorio_power']?.state);
  const cost = parseFloat(states['sensor.monthly_energy_cost']?.state);
  const daily = parseFloat(states['sensor.daily_energy']?.state);
  let energyStr = '';
  if (!Number.isNaN(pwr)) {
    energyStr = `⚡ ${Math.round(pwr)} W`;
    if (!Number.isNaN(daily)) energyStr += ` · ${daily.toFixed(1)} kWh hoje`;
    if (!Number.isNaN(cost)) energyStr += ` · R$ ${Math.round(cost)}/mês`;
  }

  const batSensors = [
    ['sensor.0xa4c1388ad4a9a0b6_battery', 'Suíte'],
    ['sensor.0xa4c13818e2a13578_battery', 'Escritório'],
    ['sensor.0xa4c138f397b856f0_battery', 'Cozinha'],
    ['sensor.0x00158d00048740a5_battery', 'Varanda'],
    ['sensor.0x00158d000244775f_battery', 'Banh. Social'],
    ['sensor.0x00158d0005bd5c27_battery', 'Sensor Sala'],
    ['sensor.0x00158d0004110926_battery', 'Sensor Varanda'],
    ['sensor.0x00158d00041d46d5_battery', 'Porta Sala'],
    ['sensor.0x00158d00045b039a_battery', 'Despensa'],
    ['sensor.0x00158d00047bba26_battery', 'Sensor Cozinha'],
    ['sensor.0x00158d00054d601a_battery', 'Porta Banh. Suíte'],
    ['sensor.0x00158d00045d75bf_battery', 'Sensor Closet'],
    ['sensor.0x00158d00044ea7ba_battery', 'Portão Cachorros']
  ];
  const lowBat = [];
  for (const [eid, label] of batSensors) {
    const v = parseFloat(states[eid]?.state);
    if (!Number.isNaN(v) && v <= 15) lowBat.push(`${label} ${Math.round(v)}%`);
  }
  const batStr = lowBat.length ? `⚠️ Bateria baixa: ${lowBat.slice(0, 3).join(', ')}` : '';

  const blocks = [
    `<span class="time">${hh}<span class="time-colon">:</span>${mm}</span>`,
    `<font color="#6a7377"><b>${dateStr}</b></font>`,
    `<b>${greet}</b>`,
    `<b>${activeStr}</b>`,
    weatherStr,
    vacStr,
    modeStr,
    energyStr,
    batStr
  ].filter(Boolean);

  return blocks.map(b => `<p>${b}</p>`).join('');
]]]""",
            "extra_styles": """
              :host {
                --custom-layout-card-padding: 3.3vw;
                --sidebar-time-font-size: 5.0vw;
                --sidebar-time-line-height: 4.3vw;
                --sidebar-font-size: 1.32vw;
                --sidebar-line-height: 1.9vw;
                --ha-card-background: none;
                --ha-card-box-shadow: none;
                --ha-card-border-width: 0px;
              }
              #card {
                padding: 0;
                border-width: 0;
                background: none !important;
                box-shadow: none !important;
                font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", Roboto, system-ui, sans-serif;
              }
              #container {
                display: flex !important;
              }
              #name {
                padding: 1.5vw 2.2vw 0 var(--custom-layout-card-padding);
                white-space: normal;
                text-align: left;
                width: 100%;
              }
              .time {
                font-size: var(--sidebar-time-font-size);
                font-weight: 300;
                line-height: var(--sidebar-time-line-height);
                letter-spacing: 0.08vw;
                margin-left: -0.25vw;
                color: rgba(255, 255, 255, 0.85);
              }
              .time-colon {
                position: relative;
                top: -0.09em;
              }
              p {
                font-size: var(--sidebar-font-size);
                line-height: var(--sidebar-line-height);
                font-weight: 300;
                letter-spacing: 0.04vw;
                color: #7c868a;
                margin: 0.85vw 0;
              }
              b {
                font-weight: 600;
              }
              p > b {
                color: rgba(255, 255, 255, 0.82);
              }
              @media screen and (max-width: 1200px) {
                .time {
                  font-size: calc(var(--sidebar-time-font-size) * 1.35);
                  line-height: calc(var(--sidebar-time-line-height) * 1.35);
                }
                p {
                  font-size: calc(var(--sidebar-font-size) * 1.35);
                  line-height: calc(var(--sidebar-line-height) * 1.35);
                }
              }
              @media screen and (max-width: 800px) {
                .time {
                  font-size: calc(var(--sidebar-time-font-size) * 2.5);
                  line-height: calc(var(--sidebar-time-line-height) * 2.5);
                }
                p {
                  font-size: calc(var(--sidebar-font-size) * 2.4);
                  line-height: calc(var(--sidebar-line-height) * 2.4);
                }
                #name {
                  padding: 1vw 1vw 0 1vw;
                }
              }
            """,
        },
        "footer": {
            "template": ["settings", "extra_styles"],
            "variables": {"notify": "[[[ return false; ]]]"},
            "size": "2vw",
            "show_icon": False,
            "color": "#9da0a2",
            "custom_fields": {
                "notify": """[[[
  if (Number.isInteger(variables.notify) && variables.notify > 0) {
      return variables.notify;
  } else if (variables.notify === true) {
      return '<span style="font-weight: 900;">!</span>';
  }
]]]"""
            },
            "styles": {
                "card": [
                    {"color": "#b4b7bb"},
                    {"width": "fit-content"},
                    {"transition": "background 0.2s ease"},
                    {"overflow": "visible"},
                    {"--mdc-ripple-color": "rgba(0, 0, 0, 0.8)"},
                ],
                "custom_fields": {
                    "notify": [
                        {
                            "display": """[[[
  if (Number.isInteger(variables.notify)) return variables.notify > 0 ? 'initial' : 'none';
  return variables.notify ? 'initial' : 'none';
]]]"""
                        },
                        {"position": "absolute"},
                        {"font-weight": 700},
                        {"color": "#f0f0f0"},
                        {"background": "#9e3636"},
                        {"border-radius": "50%"},
                        {"text-align": "center"},
                        {"text-overflow": "unset"},
                        {"z-index": 2},
                    ]
                },
            },
            "tap_action": {"haptic": "medium"},
            "hold_action": {"action": "none"},
            "double_tap_action": {"action": "none"},
        },
    }

    templates.update(icons)
    return templates


def build_popups() -> list:
    p_style = popup_bubble_styles()

    def make_popup(hash_id: str, title: str, icon: str, cards: list) -> dict:
        return {
            "type": "custom:bubble-card",
            "card_type": "pop-up",
            "hash": hash_id,
            "name": title,
            "icon": icon,
            "view_layout": {"grid-area": "popups"},
            "width_desktop": "540px",
            "bg_color": "rgba(28, 32, 34, 0.96)",
            "bg_opacity": 96,
            "bg_blur": 8,
            "shadow_opacity": 40,
            "background_update": False,
            "performance_mode": True,
            "styles": p_style,
            "cards": cards,
        }

    return [
        # 1. Popup Sala (todas as luzes + AC + TV)
        make_popup(
            "#popup-sala",
            "Sala",
            "mdi:sofa",
            [
                {
                    "type": "entities",
                    "title": "Iluminação da Sala",
                    "show_header_toggle": True,
                    "entities": [
                        {"entity": "light.sala_central", "name": "Central Sala"},
                        {"entity": "light.sala_led_sofa", "name": "LED Sofá"},
                        {"entity": "light.sala_spot_sofa", "name": "Spot Sofá"},
                        {"entity": "light.sala_mesa_jantar", "name": "Mesa de Jantar"},
                        {"entity": "light.sala_entrada", "name": "Entrada Sala"},
                        {"entity": "light.sala_banh_social", "name": "Banheiro Social"},
                    ],
                },
                {
                    "type": "entities",
                    "title": "Dispositivos & Presença",
                    "show_header_toggle": False,
                    "entities": [
                        {"entity": "media_player.tv_sala_androidtv", "name": "TV Sala"},
                        {"entity": "switch.sala_ac", "name": "AC Sala"},
                        {"entity": "media_player.sala_echo_show_8", "name": "Echo Show 8"},
                        {"entity": "binary_sensor.0x00158d0005bd5c27_occupancy", "name": "Presença Sala"},
                    ],
                },
            ],
        ),
        # 2. Popup Escritório
        make_popup(
            "#popup-escritorio",
            "Escritório",
            "mdi:desk",
            [
                {
                    "type": "custom:mushroom-climate-card",
                    "entity": "climate.escritorio_ar_condicionado",
                    "name": "Ar-Condicionado Escritório",
                    "show_temperature_control": True,
                    "hvac_modes": ["off", "cool", "dry", "fan_only", "auto"],
                    "collapsible_controls": False,
                },
                {
                    "type": "entities",
                    "title": "Equipamentos & Energia",
                    "show_header_toggle": False,
                    "entities": [
                        {"entity": "light.escritorio_spot_escritorio_led", "name": "Spot LED Escritório"},
                        {"entity": "switch.escritorio_computador", "name": "Computador"},
                        {"entity": "sensor.escritorio_computador_power", "name": "Potência PC"},
                        {"entity": "switch.escritorio_monitor", "name": "Monitor"},
                        {"entity": "sensor.monitor_energy_power", "name": "Potência Monitor"},
                        {"entity": "sensor.escritorio_ar_condicionado_real_time_power", "name": "Potência AC"},
                        {"entity": "sensor.escritorio_potencia_total", "name": "Potência Total Escritório"},
                        {"entity": "sensor.0xa4c13818e2a13578_temperature", "name": "Temperatura"},
                        {"entity": "sensor.0xa4c13818e2a13578_humidity", "name": "Umidade"},
                    ],
                },
            ],
        ),
        # 3. Popup Suíte
        make_popup(
            "#popup-suite",
            "Suíte",
            "mdi:bed",
            [
                {
                    "type": "entities",
                    "title": "Iluminação & Clima",
                    "show_header_toggle": False,
                    "entities": [
                        {"entity": "light.suite_ventilador", "name": "Luz Suíte"},
                        {"entity": "light.suite_closet", "name": "Closet"},
                        {"entity": "light.quarto_suite_banheiro_espelho", "name": "Espelho Banheiro"},
                        {"entity": "switch.suite_ac", "name": "AC Suíte (Tomada)"},
                        {"entity": "sensor.suite_ac_energy_power", "name": "Potência AC Suíte"},
                        {"entity": "fan.suite_ventilador_2", "name": "Ventilador Suíte"},
                        {"entity": "media_player.tv_samsung_suite", "name": "TV Samsung Suíte"},
                        {"entity": "sensor.0xa4c1388ad4a9a0b6_temperature", "name": "Temperatura Suíte"},
                        {"entity": "sensor.0xa4c1388ad4a9a0b6_humidity", "name": "Umidade Suíte"},
                    ],
                },
                {
                    "type": "grid",
                    "columns": 2,
                    "square": False,
                    "cards": [
                        {
                            "type": "custom:mushroom-entity-card",
                            "entity": "script.ligar_desligar_ac_quarto",
                            "name": "Ligar / Desligar AC",
                            "icon": "mdi:snowflake",
                            "tap_action": {"action": "perform-action", "perform_action": "script.ligar_desligar_ac_quarto"},
                        },
                        {
                            "type": "custom:mushroom-entity-card",
                            "entity": "input_boolean.suite_ac_sleep_mode",
                            "name": "Modo Sleep",
                            "icon": "mdi:weather-night",
                            "tap_action": {"action": "toggle"},
                        },
                        {
                            "type": "custom:mushroom-entity-card",
                            "entity": "timer.suite_ac",
                            "name": "Timer AC Suíte",
                            "icon": "mdi:timer-outline",
                        },
                        {
                            "type": "custom:mushroom-entity-card",
                            "entity": "timer.suite_fan",
                            "name": "Timer Ventilador",
                            "icon": "mdi:fan-clock",
                        },
                    ],
                },
            ],
        ),
        # 4. Popup Cozinha & Varanda
        make_popup(
            "#popup-cozinha",
            "Cozinha & Varanda",
            "mdi:countertop",
            [
                {
                    "type": "entities",
                    "title": "Luzes & Tomadas",
                    "show_header_toggle": True,
                    "entities": [
                        {"entity": "light.cozinha_central", "name": "Central Cozinha"},
                        {"entity": "light.cozinha_bancada", "name": "Bancada"},
                        {"entity": "light.cozinha_lavanderia", "name": "Lavanderia"},
                        {"entity": "light.hall_light_switch_top", "name": "Corredor"},
                        {"entity": "light.hall_light_switch_bottom", "name": "Varanda"},
                        {"entity": "switch.varanda_churrasqueira", "name": "Churrasqueira"},
                    ],
                },
                {
                    "type": "entities",
                    "title": "Sensores",
                    "show_header_toggle": False,
                    "entities": [
                        {"entity": "sensor.0xa4c138f397b856f0_temperature", "name": "Temperatura Cozinha"},
                        {"entity": "sensor.0xa4c138f397b856f0_humidity", "name": "Umidade Cozinha"},
                        {"entity": "sensor.0x00158d00048740a5_temperature", "name": "Temperatura Varanda"},
                        {"entity": "binary_sensor.hlk_ld2410_2302_occupancy", "name": "Presença Cozinha"},
                        {"entity": "binary_sensor.0x00158d0004110926_occupancy", "name": "Presença Varanda"},
                    ],
                },
            ],
        ),
        # 5. Footer Popup: Sistema & Infra
        make_popup(
            "#popup-sistema",
            "Sistema & Servidor",
            "mdi:server",
            [
                {
                    "type": "custom:mini-graph-card",
                    "name": "CPU & Memória (24h)",
                    "hours_to_show": 24,
                    "points_per_hour": 2,
                    "line_width": 2,
                    "animate": True,
                    "entities": [
                        {"entity": "sensor.system_monitor_processor_use", "name": "CPU", "color": "#3182b7"},
                        {"entity": "sensor.system_monitor_memory_usage", "name": "RAM", "color": "#8b6bd6"},
                    ],
                },
                {
                    "type": "entities",
                    "title": "Host & Serviços",
                    "show_header_toggle": False,
                    "entities": [
                        {"entity": "sensor.system_monitor_processor_use", "name": "Uso de CPU"},
                        {"entity": "sensor.system_monitor_processor_temperature", "name": "Temperatura CPU"},
                        {"entity": "sensor.system_monitor_memory_usage", "name": "Uso de Memória"},
                        {"entity": "sensor.system_monitor_disk_usage", "name": "Uso de Disco"},
                        {"entity": "sensor.system_monitor_disk_free", "name": "Disco Livre"},
                        {"entity": "sensor.system_monitor_last_boot", "name": "Último Boot"},
                        {"entity": "binary_sensor.zigbee2mqtt_bridge_connection_state", "name": "Zigbee2MQTT"},
                        {"entity": "binary_sensor.pihole_status", "name": "Pi-hole"},
                        {"entity": "sensor.fast_com_download", "name": "Velocidade Internet"},
                        {"entity": "sensor.backup_last_successful_automatic_backup", "name": "Último Backup"},
                    ],
                },
            ],
        ),
        # 6. Footer Popup: Energia & River2 UPS
        make_popup(
            "#popup-energia",
            "Energia & UPS",
            "mdi:lightning-bolt",
            [
                {
                    "type": "custom:mini-graph-card",
                    "name": "Potência Instantânea (24h)",
                    "hours_to_show": 24,
                    "points_per_hour": 2,
                    "line_width": 2,
                    "animate": True,
                    "entities": [
                        {"entity": "sensor.sala_varanda_escritorio_power", "name": "Sala/Var/Escr", "color": "#3182b7"},
                        {"entity": "sensor.escritorio_potencia_total", "name": "Escritório", "color": "#e5a93c"},
                    ],
                },
                {
                    "type": "entities",
                    "title": "Consumo & Fatura",
                    "show_header_toggle": False,
                    "entities": [
                        {"entity": "sensor.sala_varanda_escritorio_power", "name": "Potência Sala/Varanda/Escritório"},
                        {"entity": "sensor.escritorio_potencia_total", "name": "Potência Total Escritório"},
                        {"entity": "sensor.daily_energy", "name": "Consumo Hoje"},
                        {"entity": "sensor.weekly_energy", "name": "Consumo Semana"},
                        {"entity": "sensor.monthly_energy", "name": "Consumo Mês"},
                        {"entity": "sensor.monthly_energy_cost", "name": "Custo Atual Mês"},
                        {"entity": "sensor.projecao_consumo_mensal", "name": "Projeção Mensal (kWh)"},
                        {"entity": "sensor.projecao_custo_mensal", "name": "Projeção Mensal (R$)"},
                    ],
                },
                {
                    "type": "entities",
                    "title": "EcoFlow River 2 (Nobreak)",
                    "show_header_toggle": False,
                    "entities": [
                        {"entity": "sensor.river2_battery_level", "name": "Bateria River 2"},
                        {"entity": "sensor.river2_total_in_power", "name": "Entrada (W)"},
                        {"entity": "sensor.river2_total_out_power", "name": "Saída (W)"},
                        {"entity": "sensor.river2_battery_temperature", "name": "Temperatura Bateria"},
                    ],
                },
            ],
        ),
        # 7. Footer Popup: Aspirador Eufy X10 Pro
        make_popup(
            "#popup-aspirador",
            "Eufy X10 Pro",
            "mdi:robot-vacuum-variant",
            [
                {
                    "type": "custom:mushroom-vacuum-card",
                    "entity": "vacuum.escritorio_eufy_x10_pro",
                    "name": "Eufy X10 Pro",
                    "commands": ["start_pause", "stop", "return_home", "locate"],
                    "icon_animation": True,
                },
                {
                    "type": "custom:mushroom-entity-card",
                    "entity": "script.eufy_x10_varrer_e_passar_pano",
                    "name": "Varrer Casa Toda + Passar Pano",
                    "icon": "mdi:broom",
                    "tap_action": {"action": "perform-action", "perform_action": "script.eufy_x10_varrer_e_passar_pano"},
                },
                {
                    "type": "picture-entity",
                    "entity": "camera.escritorio_eufy_x10_pro_map",
                    "show_name": False,
                    "show_state": False,
                },
                {
                    "type": "entities",
                    "show_header_toggle": False,
                    "entities": [
                        {"entity": "sensor.escritorio_eufy_x10_pro_battery", "name": "Bateria"},
                        {"entity": "select.escritorio_eufy_x10_pro_cleaning_mode", "name": "Modo de Limpeza"},
                        {"entity": "select.escritorio_eufy_x10_pro_cleaning_intensity", "name": "Intensidade"},
                        {"entity": "sensor.escritorio_eufy_x10_pro_cleaning_area", "name": "Última Área"},
                        {"entity": "sensor.escritorio_eufy_x10_pro_cleaning_time", "name": "Último Tempo"},
                    ],
                },
            ],
        ),
        # 8. Footer Popup: Clima & Ambientes
        make_popup(
            "#popup-clima",
            "Clima & Ambientes",
            "mdi:thermometer",
            [
                {
                    "type": "weather-forecast",
                    "entity": "weather.openweathermap",
                    "name": "Tempo Agora",
                    "show_current": True,
                    "show_forecast": False,
                },
                {
                    "type": "custom:mini-graph-card",
                    "name": "Temperaturas (24h)",
                    "hours_to_show": 24,
                    "points_per_hour": 1,
                    "line_width": 2,
                    "entities": [
                        {"entity": "sensor.0xa4c13818e2a13578_temperature", "name": "Escritório", "color": "#3182b7"},
                        {"entity": "sensor.0xa4c1388ad4a9a0b6_temperature", "name": "Suíte", "color": "#5ec49f"},
                        {"entity": "sensor.0xa4c138f397b856f0_temperature", "name": "Cozinha", "color": "#e5a93c"},
                        {"entity": "sensor.0x00158d00048740a5_temperature", "name": "Varanda", "color": "#e06c75"},
                    ],
                },
                {
                    "type": "entities",
                    "title": "Sensores por Ambiente",
                    "show_header_toggle": False,
                    "entities": [
                        {"entity": "sensor.0xa4c13818e2a13578_temperature", "name": "Escritório (Temp)"},
                        {"entity": "sensor.0xa4c13818e2a13578_humidity", "name": "Escritório (Umidade)"},
                        {"entity": "sensor.0xa4c1388ad4a9a0b6_temperature", "name": "Suíte (Temp)"},
                        {"entity": "sensor.0xa4c1388ad4a9a0b6_humidity", "name": "Suíte (Umidade)"},
                        {"entity": "sensor.0xa4c138f397b856f0_temperature", "name": "Cozinha (Temp)"},
                        {"entity": "sensor.0x00158d00048740a5_temperature", "name": "Varanda (Temp)"},
                        {"entity": "sensor.0x00158d000244775f_temperature", "name": "Banheiro Social (Temp)"},
                    ],
                },
            ],
        ),
        # 9. Footer Popup: Câmeras & Segurança
        make_popup(
            "#popup-cameras",
            "Câmeras & Segurança",
            "mdi:shield-home",
            [
                {
                    "type": "picture-entity",
                    "entity": "camera.sala_fluent",
                    "name": "Câmera Sala",
                    "camera_view": "auto",
                },
                {
                    "type": "entities",
                    "title": "Segurança & Modos da Casa",
                    "show_header_toggle": False,
                    "entities": [
                        {"entity": "lock.kuanttum_delta_pro_operate_lock", "name": "Fechadura Kuanttum"},
                        {"entity": "alarm_control_panel.home_alarm", "name": "Alarme"},
                        {"entity": "input_boolean.modo_visitas", "name": "Modo Visitas"},
                        {"entity": "input_boolean.faxina", "name": "Modo Faxina"},
                        {"entity": "input_boolean.vacation_mode", "name": "Modo Férias"},
                        {"entity": "input_boolean.sensor_movimento_banheiro_social", "name": "Sensor Banheiro Social"},
                    ],
                },
            ],
        ),
        # 10. Footer Popup: Atualizações
        make_popup(
            "#popup-updates",
            "Atualizações",
            "mdi:arrow-up-bold-circle-outline",
            [
                {
                    "type": "entities",
                    "title": "Home Assistant",
                    "show_header_toggle": False,
                    "entities": [
                        {"entity": "update.home_assistant_core_update", "name": "Core"},
                        {"entity": "update.home_assistant_supervisor_update", "name": "Supervisor"},
                        {"entity": "update.home_assistant_operating_system_update", "name": "Operating System"},
                        {"entity": "update.zigbee2mqtt_update", "name": "Zigbee2MQTT"},
                    ],
                },
                {
                    "type": "custom:auto-entities",
                    "card": {"type": "entities", "title": "Atualizações Disponíveis", "show_header_toggle": False},
                    "filter": {
                        "include": [{"domain": "update", "state": "on"}],
                    },
                    "sort": {"method": "friendly_name"},
                },
            ],
        ),
    ]


def build_dashboard_config() -> dict:
    bg_uri = load_b64_data_uri("www/background.png", "image/png")
    loader_uri = load_b64_data_uri("www/loader.svg", "image/svg+xml")
    templates = build_templates(loader_uri)

    g_mod = grid_card_mod()

    config = {
        "title": DASHBOARD_TITLE,
        "button_card_templates": templates,
        "views": [
            {
                "path": "home",
                "title": "Home",
                "icon": "mdi:home-outline",
                "type": "custom:grid-layout",
                "background": f'center / cover no-repeat fixed url("{bg_uri}")',
                "layout": {
                    "margin": 0,
                    "grid-gap": "3.0vw",
                    "grid-template-columns": "1.15fr 1fr 1fr 1fr 0px",
                    "grid-template-rows": "0px repeat(2, fit-content(100%)) auto 0px",
                    "grid-template-areas": (
                        '"sidebar  .        .           .        ."\n'
                        '"sidebar  sala     escritorio  suite    ."\n'
                        '"sidebar  media    cozinha     casa     ."\n'
                        '"sidebar  footer   footer      footer   ."\n'
                        '"popups   popups   popups      popups   ."'
                    ),
                    "mediaquery": {
                        "(max-width: 1200px)": {
                            "grid-gap": "3.0vw",
                            "grid-template-columns": "1.1fr 1fr 1fr 0px",
                            "grid-template-rows": "0px repeat(3, fit-content(100%)) auto 0px",
                            "grid-template-areas": (
                                '"sidebar  .           .        ."\n'
                                '"sidebar  sala        suite    ."\n'
                                '"sidebar  escritorio  cozinha  ."\n'
                                '"sidebar  media       casa     ."\n'
                                '"sidebar  footer      footer   ."\n'
                                '"popups   popups      popups   ."'
                            ),
                        },
                        "(max-width: 800px)": {
                            "grid-gap": "4.8vw",
                            "grid-template-columns": "0px repeat(2, 1fr) 0px",
                            "grid-template-rows": "0px repeat(5, fit-content(100%)) auto 0px",
                            "grid-template-areas": (
                                '".       .           .        ."\n'
                                '".       sidebar     sidebar  ."\n'
                                '".       sala        suite    ."\n'
                                '".       escritorio  cozinha  ."\n'
                                '".       media       casa     ."\n'
                                '".       footer      footer   ."\n'
                                '"popups  popups      popups   ."'
                            ),
                        },
                    },
                },
                "cards": [
                    # ==================== SIDEBAR ====================
                    {
                        "type": "vertical-stack",
                        "view_layout": {"grid-area": "sidebar"},
                        "card_mod": {
                            "style": """
                              ha-card, #root {
                                background-color: rgba(0, 0, 0, 0.10);
                                border-radius: 0;
                                border-right: 1px solid rgba(255, 255, 255, 0.06);
                                min-height: 100vh;
                              }
                              @media screen and (max-width: 800px) {
                                ha-card, #root {
                                  background-color: transparent;
                                  border-right: none;
                                  min-height: auto;
                                }
                              }
                            """
                        },
                        "cards": [
                            {
                                "type": "custom:button-card",
                                "entity": "weather.openweathermap",
                                "template": "sidebar",
                            }
                        ],
                    },
                    # ==================== SALA ====================
                    {
                        "type": "grid",
                        "title": "Sala",
                        "view_layout": {"grid-area": "sala"},
                        "columns": 2,
                        "card_mod": g_mod,
                        "cards": [
                            {
                                "type": "custom:button-card",
                                "entity": "light.sala_central",
                                "name": "Central",
                                "double_tap_action": {"action": "navigate", "navigation_path": "#popup-sala"},
                                "template": ["light", "icon_hue"],
                            },
                            {
                                "type": "custom:button-card",
                                "entity": "light.sala_led_sofa",
                                "name": "LED Sofá",
                                "double_tap_action": {"action": "navigate", "navigation_path": "#popup-sala"},
                                "template": ["light", "icon_shade"],
                            },
                            {
                                "type": "custom:button-card",
                                "entity": "media_player.tv_sala_androidtv",
                                "name": "TV Sala",
                                "state_display": "[[[ return variables.state === 'playing' || variables.state === 'on' ? 'Ligada' : 'Desligada'; ]]]",
                                "double_tap_action": {"action": "navigate", "navigation_path": "#popup-sala"},
                                "template": ["base", "icon_tv", "loader"],
                            },
                            {
                                "type": "custom:button-card",
                                "entity": "light.sala_mesa_jantar",
                                "name": "Jantar",
                                "double_tap_action": {"action": "navigate", "navigation_path": "#popup-sala"},
                                "template": ["light", "icon_spot"],
                            },
                        ],
                    },
                    # ==================== ESCRITÓRIO ====================
                    {
                        "type": "grid",
                        "title": "Escritório",
                        "view_layout": {"grid-area": "escritorio"},
                        "columns": 2,
                        "card_mod": g_mod,
                        "cards": [
                            {
                                "type": "custom:button-card",
                                "entity": "light.escritorio_spot_escritorio_led",
                                "name": "Spot LED",
                                "double_tap_action": {"action": "navigate", "navigation_path": "#popup-escritorio"},
                                "template": ["light", "icon_spot"],
                            },
                            {
                                "type": "custom:button-card",
                                "entity": "climate.escritorio_ar_condicionado",
                                "name": "Ar-Cond.",
                                "tap_action": {"action": "toggle"},
                                "double_tap_action": {"action": "navigate", "navigation_path": "#popup-escritorio"},
                                "template": ["base", "icon_climate", "circle", "loader"],
                                "variables": {
                                    "circle_input": """[[[
  if (entity) {
      const t = entity.state !== 'off' && entity.attributes.temperature != null
          ? entity.attributes.temperature
          : entity.attributes.current_temperature;
      return t != null ? Math.round(t).toString() : '';
  }
]]]""",
                                    "circle_input_unit": "°C",
                                },
                            },
                            {
                                "type": "custom:button-card",
                                "entity": "switch.escritorio_computador",
                                "name": "Computador",
                                "triggers_update": ["sensor.escritorio_computador_power"],
                                "double_tap_action": {"action": "navigate", "navigation_path": "#popup-escritorio"},
                                "template": ["base", "icon_imac", "circle", "loader"],
                                "variables": {
                                    "circle_input": """[[[
  const p = parseFloat(states['sensor.escritorio_computador_power']?.state);
  return !Number.isNaN(p) ? Math.round(p).toString() : '';
]]]""",
                                    "circle_input_unit": "W",
                                },
                            },
                            {
                                "type": "custom:button-card",
                                "entity": "switch.escritorio_monitor",
                                "name": "Monitor",
                                "triggers_update": ["sensor.monitor_energy_power"],
                                "double_tap_action": {"action": "navigate", "navigation_path": "#popup-escritorio"},
                                "template": ["base", "icon_monitors", "circle", "loader"],
                                "variables": {
                                    "circle_input": """[[[
  const p = parseFloat(states['sensor.monitor_energy_power']?.state);
  return !Number.isNaN(p) ? Math.round(p).toString() : '';
]]]""",
                                    "circle_input_unit": "W",
                                },
                            },
                        ],
                    },
                    # ==================== SUÍTE ====================
                    {
                        "type": "grid",
                        "title": "Suíte",
                        "view_layout": {"grid-area": "suite"},
                        "columns": 2,
                        "card_mod": g_mod,
                        "cards": [
                            {
                                "type": "custom:button-card",
                                "entity": "light.suite_ventilador",
                                "name": "Luz Suíte",
                                "double_tap_action": {"action": "navigate", "navigation_path": "#popup-suite"},
                                "template": ["light", "icon_lamp"],
                            },
                            {
                                "type": "custom:button-card",
                                "entity": "switch.suite_ac",
                                "name": "AC Suíte",
                                "triggers_update": ["sensor.0xa4c1388ad4a9a0b6_temperature"],
                                "double_tap_action": {"action": "navigate", "navigation_path": "#popup-suite"},
                                "template": ["base", "icon_climate", "circle", "loader"],
                                "variables": {
                                    "circle_always": True,
                                    "circle_input": """[[[
  const t = parseFloat(states['sensor.0xa4c1388ad4a9a0b6_temperature']?.state);
  return !Number.isNaN(t) ? Math.round(t).toString() : '';
]]]""",
                                    "circle_input_unit": "°C",
                                },
                            },
                            {
                                "type": "custom:button-card",
                                "entity": "fan.suite_ventilador_2",
                                "name": "Ventilador",
                                "double_tap_action": {"action": "navigate", "navigation_path": "#popup-suite"},
                                "template": ["base", "icon_fan2", "loader"],
                            },
                            {
                                "type": "custom:button-card",
                                "entity": "media_player.tv_samsung_suite",
                                "name": "TV Suíte",
                                "double_tap_action": {"action": "navigate", "navigation_path": "#popup-suite"},
                                "template": ["base", "icon_tv", "loader"],
                            },
                        ],
                    },
                    # ==================== MÍDIA (SWIPE CARD) ====================
                    {
                        "type": "grid",
                        "title": "Mídia",
                        "view_layout": {"grid-area": "media"},
                        "columns": 1,
                        "card_mod": g_mod,
                        "cards": [
                            {
                                "type": "custom:swipe-card",
                                "parameters": {
                                    "speed": 550,
                                    "spaceBetween": 28,
                                    "threshold": 5,
                                },
                                "cards": [
                                    {
                                        "type": "custom:button-card",
                                        "entity": "media_player.tv_sala_androidtv",
                                        "template": ["conditional_media"],
                                    },
                                    {
                                        "type": "grid",
                                        "columns": 2,
                                        "cards": [
                                            {
                                                "type": "custom:button-card",
                                                "entity": "media_player.tv_sala_androidtv",
                                                "name": "TV Sala",
                                                "template": ["media", "icon_tv"],
                                            },
                                            {
                                                "type": "custom:button-card",
                                                "entity": "media_player.sala_echo_show_8",
                                                "name": "Echo Show",
                                                "template": ["media", "icon_nest_mini"],
                                            },
                                            {
                                                "type": "custom:button-card",
                                                "entity": "media_player.suite_echo_dot_suite",
                                                "name": "Echo Suíte",
                                                "template": ["media", "icon_nest_mini"],
                                            },
                                            {
                                                "type": "custom:button-card",
                                                "entity": "media_player.google_home_escritorio",
                                                "name": "Escritório",
                                                "template": ["media", "icon_spotify"],
                                            },
                                        ],
                                    },
                                ],
                            }
                        ],
                    },
                    # ==================== COZINHA & CASA ====================
                    {
                        "type": "grid",
                        "title": "Cozinha",
                        "view_layout": {"grid-area": "cozinha"},
                        "columns": 2,
                        "card_mod": g_mod,
                        "cards": [
                            {
                                "type": "custom:button-card",
                                "entity": "light.cozinha_central",
                                "name": "Cozinha",
                                "double_tap_action": {"action": "navigate", "navigation_path": "#popup-cozinha"},
                                "template": ["light", "icon_hue"],
                            },
                            {
                                "type": "custom:button-card",
                                "entity": "light.cozinha_bancada",
                                "name": "Bancada",
                                "double_tap_action": {"action": "navigate", "navigation_path": "#popup-cozinha"},
                                "template": ["light", "icon_spot"],
                            },
                            {
                                "type": "custom:button-card",
                                "entity": "light.hall_light_switch_bottom",
                                "name": "Varanda",
                                "double_tap_action": {"action": "navigate", "navigation_path": "#popup-cozinha"},
                                "template": ["light", "icon_shade"],
                            },
                            {
                                "type": "custom:button-card",
                                "entity": "light.sala_banh_social",
                                "name": "Banh. Social",
                                "double_tap_action": {"action": "navigate", "navigation_path": "#popup-sala"},
                                "template": ["light", "icon_bathroom"],
                            },
                        ],
                    },
                    # ==================== CASA & PESSOAS ====================
                    {
                        "type": "grid",
                        "title": "Casa",
                        "view_layout": {"grid-area": "casa"},
                        "columns": 2,
                        "card_mod": g_mod,
                        "cards": [
                            {
                                "type": "custom:button-card",
                                "entity": "person.edgard_mello",
                                "name": "Edgard",
                                "template": ["person"],
                            },
                            {
                                "type": "custom:button-card",
                                "entity": "person.ana_maria",
                                "name": "Ana Maria",
                                "template": ["person"],
                            },
                            {
                                "type": "custom:button-card",
                                "entity": "lock.kuanttum_delta_pro_operate_lock",
                                "name": "Fechadura",
                                "tap_action": {"action": "more-info"},
                                "double_tap_action": {"action": "navigate", "navigation_path": "#popup-cameras"},
                                "template": ["base", "icon_lock"],
                            },
                            {
                                "type": "custom:button-card",
                                "entity": "input_boolean.modo_visitas",
                                "name": "Modo Visitas",
                                "double_tap_action": {"action": "navigate", "navigation_path": "#popup-cameras"},
                                "template": ["base", "icon_home", "loader"],
                            },
                        ],
                    },
                    # ==================== FOOTER ====================
                    {
                        "type": "horizontal-stack",
                        "view_layout": {"grid-area": "footer"},
                        "card_mod": {
                            "style": {
                                "$": """
                                  #root {
                                    flex-wrap: wrap;
                                    justify-content: flex-start;
                                    gap: 0.9vw;
                                    overflow: visible;
                                    padding-bottom: 1.8vw;
                                  }
                                  @media screen and (min-width: 1200px) {
                                    #root {
                                      flex-wrap: nowrap;
                                      justify-content: space-between;
                                    }
                                  }
                                  @media screen and (max-width: 800px) {
                                    #root {
                                      justify-content: center;
                                      padding-top: 2vw;
                                      padding-bottom: 4vw;
                                    }
                                  }
                                """
                            }
                        },
                        "cards": [
                            {
                                "type": "custom:button-card",
                                "name": '<ha-icon icon="mdi:server"></ha-icon> Sistema',
                                "tap_action": {"action": "navigate", "navigation_path": "#popup-sistema"},
                                "triggers_update": [
                                    "sensor.system_monitor_processor_use",
                                    "sensor.system_monitor_memory_usage",
                                    "sensor.system_monitor_disk_usage",
                                    "binary_sensor.zigbee2mqtt_bridge_connection_state",
                                    "binary_sensor.pihole_status",
                                ],
                                "variables": {
                                    "notify": """[[[
  const cpu = parseFloat(states['sensor.system_monitor_processor_use']?.state) || 0;
  const mem = parseFloat(states['sensor.system_monitor_memory_usage']?.state) || 0;
  const dsk = parseFloat(states['sensor.system_monitor_disk_usage']?.state) || 0;
  const z2m = states['binary_sensor.zigbee2mqtt_bridge_connection_state']?.state;
  const ph = states['binary_sensor.pihole_status']?.state;
  return cpu >= 85 || mem >= 90 || dsk >= 85 || z2m === 'off' || ph === 'off';
]]]"""
                                },
                                "template": "footer",
                            },
                            {
                                "type": "custom:button-card",
                                "name": '<ha-icon icon="mdi:lightning-bolt"></ha-icon> Energia',
                                "tap_action": {"action": "navigate", "navigation_path": "#popup-energia"},
                                "triggers_update": [
                                    "sensor.river2_battery_level",
                                ],
                                "variables": {
                                    "notify": """[[[
  const bat = parseFloat(states['sensor.river2_battery_level']?.state);
  return !Number.isNaN(bat) && bat <= 25;
]]]"""
                                },
                                "template": "footer",
                            },
                            {
                                "type": "custom:button-card",
                                "name": '<ha-icon icon="mdi:robot-vacuum-variant"></ha-icon> Aspirador',
                                "tap_action": {"action": "navigate", "navigation_path": "#popup-aspirador"},
                                "triggers_update": ["vacuum.escritorio_eufy_x10_pro"],
                                "variables": {
                                    "notify": "[[[ return ['cleaning', 'error'].includes(states['vacuum.escritorio_eufy_x10_pro']?.state); ]]]"
                                },
                                "template": "footer",
                            },
                            {
                                "type": "custom:button-card",
                                "name": '<ha-icon icon="mdi:thermometer"></ha-icon> Clima',
                                "tap_action": {"action": "navigate", "navigation_path": "#popup-clima"},
                                "template": "footer",
                            },
                            {
                                "type": "custom:button-card",
                                "name": '<ha-icon icon="mdi:cctv"></ha-icon> Câmeras',
                                "tap_action": {"action": "navigate", "navigation_path": "#popup-cameras"},
                                "triggers_update": ["lock.kuanttum_delta_pro_operate_lock"],
                                "variables": {
                                    "notify": "[[[ return states['lock.kuanttum_delta_pro_operate_lock']?.state === 'unlocked'; ]]]"
                                },
                                "template": "footer",
                            },
                            {
                                "type": "custom:button-card",
                                "name": '<ha-icon icon="mdi:arrow-up-bold-circle-outline"></ha-icon> Updates',
                                "tap_action": {"action": "navigate", "navigation_path": "#popup-updates"},
                                "triggers_update": [
                                    "update.home_assistant_core_update",
                                    "update.home_assistant_supervisor_update",
                                    "update.home_assistant_operating_system_update",
                                    "update.zigbee2mqtt_update",
                                    "update.home_assistant_mini_display",
                                    "update.binance_integration_for_home_assistant_update",
                                    "update.pihole_image_update_available",
                                    "update.uptime_kuma_image_update_available",
                                    "update.traefik_image_update_available",
                                    "update.cloudflared_image_update_available",
                                    "update.portainer_image_update_available",
                                    "update.sonarr_image_update_available",
                                    "update.radarr_image_update_available",
                                    "update.bazarr_image_update_available",
                                    "update.transmission_image_update_available",
                                    "update.qbittorrent_image_update_available",
                                    "update.beszel_hub_image_update_available",
                                    "update.beszel_agent_image_update_available",
                                    "update.postgres_image_update_available",
                                    "update.redis_image_update_available",
                                    "update.0xa4c138f397b856f0",
                                    "update.0xa4c13818e2a13578",
                                ],
                                "variables": {
                                    "notify": """[[[
  const ids = [
    'update.home_assistant_core_update',
    'update.home_assistant_supervisor_update',
    'update.home_assistant_operating_system_update',
    'update.zigbee2mqtt_update',
    'update.home_assistant_mini_display',
    'update.binance_integration_for_home_assistant_update',
    'update.pihole_image_update_available',
    'update.uptime_kuma_image_update_available',
    'update.traefik_image_update_available',
    'update.cloudflared_image_update_available',
    'update.portainer_image_update_available',
    'update.sonarr_image_update_available',
    'update.radarr_image_update_available',
    'update.bazarr_image_update_available',
    'update.transmission_image_update_available',
    'update.qbittorrent_image_update_available',
    'update.beszel_hub_image_update_available',
    'update.beszel_agent_image_update_available',
    'update.postgres_image_update_available',
    'update.redis_image_update_available',
    'update.0xa4c138f397b856f0',
    'update.0xa4c13818e2a13578',
  ];
  let count = 0;
  for (const eid of ids) {
    if (states[eid]?.state === 'on') count++;
  }
  return count;
]]]"""
                                },
                                "template": "footer",
                            },
                        ],
                    },
                    # ==================== POPUPS (BUBBLE CARD) ====================
                    *build_popups(),
                ],
            }
        ],
    }

    return config


async def deploy_to_ha(config: dict) -> None:
    import websockets

    token = get_ha_token()
    async with websockets.connect(HA_WS_URL, max_size=50 * 1024 * 1024) as ws:
        await ws.recv()
        await ws.send(json.dumps({"type": "auth", "access_token": token}))
        auth = json.loads(await ws.recv())
        if auth.get("type") != "auth_ok":
            raise RuntimeError(f"HA WebSocket auth failed: {auth}")

        req_id = 1

        async def call(msg_type: str, **kwargs):
            nonlocal req_id
            i = req_id
            req_id += 1
            await ws.send(json.dumps({"id": i, "type": msg_type, **kwargs}))
            while True:
                msg = json.loads(await ws.recv())
                if msg.get("id") == i:
                    return msg

        # 1. Check if dashboard already exists
        dashboards = (await call("lovelace/dashboards/list")).get("result", [])
        exists = any(d.get("url_path") == DASHBOARD_URL_PATH for d in dashboards)

        if not exists:
            res = await call(
                "lovelace/dashboards/create",
                url_path=DASHBOARD_URL_PATH,
                title=DASHBOARD_TITLE,
                icon=DASHBOARD_ICON,
                require_admin=False,
                show_in_sidebar=True,
                mode="storage",
            )
            if not res.get("success"):
                raise RuntimeError(f"Failed to create dashboard: {res}")
            print(f"Created dashboard '{DASHBOARD_TITLE}' at /{DASHBOARD_URL_PATH}")
        else:
            print(f"Dashboard '/{DASHBOARD_URL_PATH}' already exists — updating config...")

        # 2. Save dashboard Lovelace config
        res = await call("lovelace/config/save", url_path=DASHBOARD_URL_PATH, config=config)
        if not res.get("success"):
            raise RuntimeError(f"Failed to save dashboard config: {res}")
        print(f"Saved Lovelace config to /{DASHBOARD_URL_PATH} successfully!")

        # 3. Verify read-back
        verify = await call("lovelace/config", url_path=DASHBOARD_URL_PATH)
        if not verify.get("success"):
            raise RuntimeError(f"Failed to verify dashboard config: {verify}")
        views = verify["result"].get("views", [])
        tpls = verify["result"].get("button_card_templates", {})
        print(
            f"Verified! Views: {len(views)}, Cards in view 0: {len(views[0].get('cards', []))}, "
            f"Templates: {len(tpls)}"
        )


def main():
    cfg = build_dashboard_config()

    out_yaml = ROOT / "dashboards" / "hass-config-edgard.yaml"
    out_yaml.parent.mkdir(parents=True, exist_ok=True)
    with open(out_yaml, "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f, sort_keys=False, allow_unicode=True, width=120)
    print(f"Wrote adapted dashboard YAML to {out_yaml} ({out_yaml.stat().st_size} bytes)")

    if "--deploy" in sys.argv:
        asyncio.run(deploy_to_ha(cfg))


if __name__ == "__main__":
    main()
