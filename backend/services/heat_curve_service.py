from helpers import (
    parse_settings_params,
    extract_all_parameter_inputs,
    encode_temp_value,

)

from heatpump_client import (
    fetch_parameters_html,
    post_parameters_form,
)

from decimal import Decimal, ROUND_HALF_UP
from threading import RLock
from db import get_config, get_conn

_settings_lock = RLock()
COEFFICIENT_KEY = "heating_curve_shift_coefficient"
REMAINDER_KEY = "heating_curve_shift_remainder"


def _save_settings(values):
    conn = get_conn()
    try:
        with conn:
            conn.executemany("""
                INSERT INTO app_settings (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value,
                    updated_at=CURRENT_TIMESTAMP
            """, [(key, str(value)) for key, value in values.items()])
    finally:
        conn.close()


def _coefficient(value):
    value = Decimal(str(value))
    if not value.is_finite() or value < Decimal("0.1") or value % Decimal("0.1"):
        raise ValueError("Koeficient musí byť kladné číslo po 0,1.")
    return value


def load_heating_curve_coefficient():
    return float(_coefficient(get_config(COEFFICIENT_KEY, "1.0")))


def save_heating_curve_coefficient(value):
    with _settings_lock:
        value = _coefficient(value)
        _save_settings({COEFFICIENT_KEY: value, REMAINDER_KEY: 0})
        return {"ok": True, "coefficient": float(value)}



def load_heating_main_temp(default=20.0) -> float:
    value = get_config("heating_main_temp", default)

    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def save_heating_main_temp(value: float):
    _save_settings({"heating_main_temp": round(float(value), 1), REMAINDER_KEY: 0})


def shift_heat_curve(curve: dict, delta: float) -> dict:
    return {
        key: round(float(value) + delta, 1)
        for key, value in curve.items()
    }


def set_heating_main_temp(new_temp: float, build_parameters_payload):
    with _settings_lock:
        return _set_heating_main_temp(new_temp)


def _set_heating_main_temp(new_temp):
    new_temp = float(Decimal(str(new_temp)).quantize(Decimal("0.1")))
    old_temp = load_heating_main_temp()
    delta = round(new_temp - old_temp, 1)

    if delta == 0:
        return {
            "ok": True,
            "changed": False,
            "heatingMainTemp": new_temp,
            "delta": 0,
        }

    coefficient = _coefficient(get_config(COEFFICIENT_KEY, "1.0"))
    desired_shift = Decimal(str(delta)) * coefficient + Decimal(get_config(REMAINDER_KEY, "0"))
    # Pump parameters encode temperatures in half degrees. Keep the fraction
    # locally so repeated small changes neither disappear nor accumulate bias.
    applied_shift = (desired_shift / Decimal("0.5")).quantize(
        Decimal("1"), rounding=ROUND_HALF_UP
    ) * Decimal("0.5")
    shifted_curve = None
    if applied_shift:
        html = fetch_parameters_html()
        current_settings = parse_settings_params(html)
        current_form = extract_all_parameter_inputs(html)
        shifted_curve = shift_heat_curve(current_settings["heatCurve"], float(applied_shift))
        payload = build_heat_curve_payload(current_form, shifted_curve)
        post_parameters_form(payload)

    # Commit the reference and fraction together, only after the pump accepts
    # the command. A failed HTTP request leaves the previous local state intact.
    _save_settings({"heating_main_temp": new_temp, REMAINDER_KEY: desired_shift - applied_shift})

    return {
        "ok": True,
        "changed": True,
        "oldHeatingMainTemp": old_temp,
        "heatingMainTemp": new_temp,
        "delta": delta,
        "curveDelta": float(applied_shift),
        "curveChanged": bool(applied_shift),
        "heatCurve": shifted_curve,
    }

def build_heat_curve_payload(current_form: dict, shifted_curve: dict):
    form = current_form.copy()

    form["p7"] = str(encode_temp_value(shifted_curve["-20"]))
    form["p8"] = str(encode_temp_value(shifted_curve["-12"]))
    form["p9"] = str(encode_temp_value(shifted_curve["-4"]))
    form["p10"] = str(encode_temp_value(shifted_curve["4"]))
    form["p11"] = str(encode_temp_value(shifted_curve["12"]))
    form["p12"] = str(encode_temp_value(shifted_curve["20"]))

    return form

def set_heating_main_temp_reference(new_temp: float):
    with _settings_lock:
        save_heating_main_temp(new_temp)

    return {
        "ok": True,
        "heatingMainTemp": new_temp,
        "curveChanged": False,
    }
