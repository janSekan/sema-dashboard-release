import re

def decode_heat_raw(raw: int) -> float:
    if raw > 127:
        raw -= 256
    return raw / 2

def decode_cool_raw(raw: int) -> float:
    return raw / 2

def encode_heat_value(value_c: float) -> int:
    value_c = -abs(value_c)
    raw = int(round(value_c * 2))
    if raw < 0:
        raw = 256 + raw
    return raw

def encode_cool_value(value_c: float) -> int:
    return int(round(value_c * 2))

def parse_setback_param(html: str):
    t20_match = re.search(r'<div[^>]*id="t20"[^>]*>(.*?)</div>', html, re.DOTALL)
    t21_match = re.search(r'<div[^>]*id="t21"[^>]*>(.*?)</div>', html, re.DOTALL)
    p20_match = re.search(r'<input[^>]*name="p20"[^>]*value="([^"]*)"', html)
    p21_match = re.search(r'<input[^>]*name="p21"[^>]*value="([^"]*)"', html)

    heat_raw = int(p20_match.group(1)) if p20_match else None
    cool_raw = int(p21_match.group(1)) if p21_match else None

    return {
        "setbackHeatText": t20_match.group(1).strip() if t20_match else None,
        "setbackCoolText": t21_match.group(1).strip() if t21_match else None,
        "setbackHeat": abs(decode_heat_raw(heat_raw)) if heat_raw is not None else None,
        "setbackCool": decode_cool_raw(cool_raw) if cool_raw is not None else None,
        "setbackHeatRaw": heat_raw,
        "setbackCoolRaw": cool_raw,
    }

def decode_temp_raw(raw: int) -> float:
    return raw / 2

def encode_temp_value(value_c: float) -> int:
    return int(round(value_c * 2))

def decode_percentage_raw(raw: int) -> float:
    return round(raw * 3.33)

def encode_percentage_value(value_c: float) -> int:
    return int(round(value_c / 3.33))

def decode_bivalent_temp(raw: str | int) -> float:
    value = int(raw)

    if value <= 60:
        return value / 2

    return (value - 256) / 2

def encode_bivalent_temp(temp: float) -> int:
    raw = int(round(temp * 2))

    if raw < 0:
        return 256 + raw

    return raw


def extract_input_value(html: str, name: str):
    match = re.search(rf'<input[^>]*name="{name}"[^>]*value="([^"]*)"', html)
    return match.group(1) if match else None

def parse_settings_params(html: str):
    p3 = extract_input_value(html, "p3")
    p4 = extract_input_value(html, "p4")
    p5 = extract_input_value(html, "p5")
    p7 = extract_input_value(html, "p7")
    p8 = extract_input_value(html, "p8")
    p9 = extract_input_value(html, "p9")
    p10 = extract_input_value(html, "p10")
    p11 = extract_input_value(html, "p11")
    p12 = extract_input_value(html, "p12")
    p13 = extract_input_value(html, "p13")
    p14 = extract_input_value(html, "p14")
    p15 = extract_input_value(html, "p15")
    p16 = extract_input_value(html, "p16")
    p17 = extract_input_value(html, "p17")
    p18 = extract_input_value(html, "p18")
    p19 = extract_input_value(html, "p19")
    p22 = extract_input_value(html, "p22")


    return {
        "minIndoorCool": decode_temp_raw(int(p3)) if p3 is not None else None,
        "maxIndoorHeat": decode_temp_raw(int(p4)) if p4 is not None else None,
        "minWaterTemp": decode_temp_raw(int(p14)) if p14 is not None else None,
        "maxWaterTemp": decode_temp_raw(int(p15)) if p15 is not None else None,
        "constant": int(p5) if p5 is not None else None,
        "limitWater": decode_percentage_raw(int(p13)) if p13 is not None else None,
        "limitHeat": decode_percentage_raw(int(p16)) if p16 is not None else None,
        "limitCool": decode_percentage_raw(int(p17)) if p17 is not None else None,
        "coolerTemp": decode_temp_raw(int(p18)) if p18 is not None else None,
        "bivalentTemp": decode_bivalent_temp(int(p19)) if p19 is not None else None,
        "timeLimitWater": int(p22) if p22 is not None else None,        
        "heatCurve": {
            "-20": decode_temp_raw(int(p7)) if p7 is not None else None,
            "-12": decode_temp_raw(int(p8)) if p8 is not None else None,
            "-4": decode_temp_raw(int(p9)) if p9 is not None else None,
            "4": decode_temp_raw(int(p10)) if p10 is not None else None,
            "12": decode_temp_raw(int(p11)) if p11 is not None else None,
            "20": decode_temp_raw(int(p12)) if p12 is not None else None,
        },
    }


DAY_KEYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def timer_slot_to_time(slot: int):
    if slot == 255:
        return None
    if slot == 144:
        return "24:00"

    hours = slot // 6
    minutes = (slot % 6) * 10
    return f"{hours:02d}:{minutes:02d}"

def time_to_timer_slot(value: str):
    if not value:
        return 255
    if value == "24:00":
        return 144

    h, m = map(int, value.split(":"))
    return h * 6 + (m // 10)

def parse_timer_params(html: str):
    schedule = {}

    for day_idx, day_key in enumerate(DAY_KEYS):
        day_list = []
        base = day_idx * 8

        for interval_idx in range(4):
            from_index = base + interval_idx * 2
            to_index = from_index + 1

            from_raw = extract_input_value(html, f"p{from_index}")
            to_raw = extract_input_value(html, f"p{to_index}")

            if from_raw is None or to_raw is None:
                continue

            from_raw = int(from_raw)
            to_raw = int(to_raw)

            # prázdny interval
            if from_raw == 255 or to_raw == 255:
                continue

            day_list.append({
                "from": from_raw,
                "to": to_raw,
            })

        schedule[day_key] = day_list

    return {"schedule": schedule}


def extract_all_parameter_inputs(html: str):
    matches = re.findall(r'<input[^>]*name="(p\d+)"[^>]*value="([^"]*)"', html)
    return {name: value for name, value in matches}

def extract_all_timer_inputs(html: str):
    matches = re.findall(r'<input[^>]*name="(p\d+)"[^>]*value="([^"]*)"', html)
    return {name: value for name, value in matches}

# def extract_settings_from_html(html: str):
#     return {
#         "minIndoorCool": decode_temp_raw(extract_input_value(html, "p3")),
#         "maxIndoorHeat": decode_temp_raw(extract_input_value(html, "p4")),
#         "constant": int(extract_input_value(html, "p5")),

#         "heatCurve": {
#             "-20": decode_temp_raw(extract_input_value(html, "p7")),
#             "-12": decode_temp_raw(extract_input_value(html, "p8")),
#             "-4": decode_temp_raw(extract_input_value(html, "p9")),
#             "4": decode_temp_raw(extract_input_value(html, "p10")),
#             "12": decode_temp_raw(extract_input_value(html, "p11")),
#             "20": decode_temp_raw(extract_input_value(html, "p12")),
#         },

#         "minWaterTemp": decode_temp_raw(extract_input_value(html, "p14")),
#         "maxWaterTemp": decode_temp_raw(extract_input_value(html, "p15")),
#     }

def build_parameters_payload(current_form: dict, data):
    def val(key):
        return data[key] if isinstance(data, dict) else getattr(data, key)

    form = current_form.copy()

    form["p3"] = str(encode_temp_value(val("minIndoorCool")))
    form["p4"] = str(encode_temp_value(val("maxIndoorHeat")))
    form["p5"] = str(int(val("constant")))

    curve = val("heatCurve")

    form["p7"] = str(encode_temp_value(curve["-20"]))
    form["p8"] = str(encode_temp_value(curve["-12"]))
    form["p9"] = str(encode_temp_value(curve["-4"]))
    form["p10"] = str(encode_temp_value(curve["4"]))
    form["p11"] = str(encode_temp_value(curve["12"]))
    form["p12"] = str(encode_temp_value(curve["20"]))

    form["p13"] = str(encode_percentage_value(val("limitWater")))
    form["p14"] = str(encode_temp_value(val("minWaterTemp")))
    form["p15"] = str(encode_temp_value(val("maxWaterTemp")))
    form["p16"] = str(encode_percentage_value(val("limitHeat")))
    form["p17"] = str(encode_percentage_value(val("limitCool")))
    form["p18"] = str(encode_temp_value(val("coolerTemp")))
    form["p19"] = str(encode_bivalent_temp(val("bivalentTemp")))
    form["p22"] = str(int(val("timeLimitWater")))

    return form