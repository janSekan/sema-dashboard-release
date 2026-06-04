from helpers import (
    parse_settings_params,
    extract_all_parameter_inputs,
    encode_temp_value,

)

from heatpump_client import (
    fetch_parameters_html,
    post_parameters_form,
)

from db import (get_config, set_config)



def load_heating_main_temp(default=20.0) -> float:
    value = get_config("heating_main_temp", default)

    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def save_heating_main_temp(value: float):
    set_config("heating_main_temp", round(float(value), 1))


def shift_heat_curve(curve: dict, delta: float) -> dict:
    return {
        key: round(float(value) + delta, 1)
        for key, value in curve.items()
    }


def set_heating_main_temp(new_temp: float, build_parameters_payload):
    old_temp = load_heating_main_temp()
    delta = round(new_temp - old_temp, 1)

    if delta == 0:
        return {
            "ok": True,
            "changed": False,
            "heatingMainTemp": new_temp,
            "delta": 0,
        }

    html = fetch_parameters_html()

    current_settings = parse_settings_params(html)
    current_form = extract_all_parameter_inputs(html)

    shifted_curve = shift_heat_curve(current_settings["heatCurve"], delta)

    payload = build_heat_curve_payload(current_form, shifted_curve)

    print("HEAT CURVE PAYLOAD:", payload)
    
    post_parameters_form(payload)

    save_heating_main_temp(new_temp)

    return {
        "ok": True,
        "changed": True,
        "oldHeatingMainTemp": old_temp,
        "heatingMainTemp": new_temp,
        "delta": delta,
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
    save_heating_main_temp(new_temp)

    return {
        "ok": True,
        "heatingMainTemp": new_temp,
        "curveChanged": False,
    }