"""Slow, read-only HA configuration cache; never fetch from an HTTP handler."""
import asyncio
import logging
import math
from db import get_config
from heatpump_client import fetch_parameters_html, fetch_timer_html
from helpers import parse_settings_params, parse_setback_param, parse_timer_params, timer_slot_to_time, extract_all_timer_inputs
from telemetry import utc_now

LOG = logging.getLogger(__name__)
MAX_AGE = 900
FIELDS = {
    'min_indoor_cool': 'minIndoorCool', 'max_indoor_heat': 'maxIndoorHeat',
    'min_water_temp': 'minWaterTemp', 'max_water_temp': 'maxWaterTemp',
    'regulation_constant': 'constant', 'limit_water_percent': 'limitWater',
    'limit_heat_percent': 'limitHeat', 'limit_cool_percent': 'limitCool',
    'cooling_water_temp': 'coolerTemp', 'bivalent_temp': 'bivalentTemp',
    'dhw_time_limit_minutes': 'timeLimitWater',
}
CURVE = dict(curve_minus20='-20', curve_minus12='-12', curve_minus4='-4',
             curve_plus4='4', curve_plus12='12', curve_plus20='20')
KEYS = (*FIELDS, *CURVE, 'reference_temp', 'setback_heat', 'setback_cool')


def numeric(value):
    if type(value) in (int, float) and math.isfinite(value):
        return value
    return None


def empty_configuration():
    return dict(available=False, observed_at=None, max_age_seconds=MAX_AGE,
                values={key: None for key in KEYS}, schedule=None)


def collect_configuration():
    result = empty_configuration()
    try:
        html = fetch_parameters_html()
        params = parse_settings_params(html)
        offsets = parse_setback_param(html)
        values = {key: numeric(params.get(field)) for key, field in FIELDS.items()}
        values.update({key: numeric(params['heatCurve'].get(point)) for key, point in CURVE.items()})
        if not any(value is not None for value in values.values()):
            raise ValueError('No known parameter fields')
        for key in ('limit_water_percent', 'limit_heat_percent', 'limit_cool_percent'):
            if values[key] is not None and not 0 <= values[key] <= 100:
                values[key] = None
        values.update(setback_heat=numeric(offsets.get('setbackHeat')),
                      setback_cool=numeric(offsets.get('setbackCool')))
        try:
            raw = get_config('heating_main_temp', None)
            values['reference_temp'] = numeric(float(raw)) if raw is not None else None
        except Exception:
            # No settings/credentials or exception contents in logs.
            values['reference_temp'] = None
        result.update(available=True, values=values)
    except Exception:
        LOG.warning('HA configuration parameters unavailable')
    if result['available']:
        try:
            timer_html = fetch_timer_html()
            inputs = extract_all_timer_inputs(timer_html)
            slots = [int(inputs[f'p{index}']) for index in range(56)]
            for index in range(0, 56, 2):
                start, end = slots[index:index + 2]
                if (start, end) != (255, 255) and not 0 <= start < end <= 144:
                    raise ValueError('Incomplete or invalid timer interval')
            schedule = parse_timer_params(timer_html)['schedule']
            result['schedule'] = {day: [
                {'from': timer_slot_to_time(item['from']), 'to': timer_slot_to_time(item['to'])}
                for item in intervals if 0 <= item['from'] < item['to'] <= 144
            ] for day, intervals in schedule.items()}
        except Exception:
            LOG.warning('HA setback schedule unavailable')
    result['observed_at'] = utc_now()
    return result


class ConfigurationCollector:
    def __init__(self, store):
        self.store = store
        self.snapshot = empty_configuration()

    async def run(self):
        while True:
            try:
                enabled = await asyncio.to_thread(self.store.read)
                if enabled.get('token_hash') and enabled.get('scope') == 'read':
                    self.snapshot = await asyncio.to_thread(collect_configuration)
                    await asyncio.sleep(300)
                else:
                    self.snapshot = empty_configuration()
                    await asyncio.sleep(5)
            except asyncio.CancelledError:
                raise
            except Exception:
                self.snapshot = empty_configuration()
                LOG.warning('HA configuration cache unavailable')
                await asyncio.sleep(30)
