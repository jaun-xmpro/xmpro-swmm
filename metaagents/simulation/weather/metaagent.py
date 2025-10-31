"""
Weather Simulation MetaAgent V2

Jaun van Heerden
2025

This metaagent generates weather timeseries data for areas.

Key Features:
- Set default weather ranges in on_create
- Define areas with optional per-area ranges in on_receive
- Generate timeseries data over a specified time range
- Output area timeseries (no interpolation)

The separation of concerns:
- This metaagent: Generates weather data for areas
- weather_interpolation: Interpolates to query points
- weather_to_pyswmm: Converts to SWMM format
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
import json
import random


# Global state
_config: Dict[str, Any] = {}


@dataclass
class WeatherRanges:
    """Min/max ranges for random walk weather generation"""
    precipitation_min: float = 0.0
    precipitation_max: float = 50.0
    temperature_min: float = -10.0
    temperature_max: float = 40.0
    atmospheric_pressure_min: float = 980.0
    atmospheric_pressure_max: float = 1040.0
    humidity_min: float = 0.0
    humidity_max: float = 100.0
    wind_speed_min: float = 0.0
    wind_speed_max: float = 30.0
    wind_direction_min: float = 0.0
    wind_direction_max: float = 360.0

    # Random walk step sizes (how much values can change per timestep)
    precipitation_step: float = 2.0
    temperature_step: float = 0.5
    atmospheric_pressure_step: float = 1.0
    humidity_step: float = 2.0
    wind_speed_step: float = 1.0
    wind_direction_step: float = 10.0


@dataclass
class Area:
    """Weather area"""
    name: str
    x: float  # 0-1 normalized coordinate
    y: float  # 0-1 normalized coordinate
    precipitation: float = 0.0  # mm/hour - starting value
    temperature: float = 20.0  # degrees Celsius - starting value
    atmospheric_pressure: float = 1013.25  # hPa - starting value
    humidity: float = 50.0  # percentage (0-100) - starting value
    wind_speed: float = 0.0  # m/s - starting value
    wind_direction: float = 0.0  # degrees (0-360) - starting value
    weather_ranges: Optional['WeatherRanges'] = None  # Per-area weather ranges


def _parse_input(data: Any) -> Dict[str, Any]:
    """Parse input, handling JSON strings"""
    if isinstance(data, str):
        return json.loads(data)
    return data


def _parse_timestamp(timestamp_str: str) -> datetime:
    """Parse ISO timestamp"""
    return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))


def _clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp value between min and max"""
    return max(min_val, min(max_val, value))


def _random_walk_step(current: float, step_size: float, min_val: float, max_val: float) -> float:
    """
    Perform one random walk step.

    Args:
        current: Current value
        step_size: Maximum change per step
        min_val: Minimum allowed value
        max_val: Maximum allowed value

    Returns:
        New value after random walk step
    """
    # Random change: uniform distribution between -step_size and +step_size
    change = random.uniform(-step_size, step_size)
    new_value = current + change

    # Clamp to min/max bounds
    return _clamp(new_value, min_val, max_val)


def _parse_weather_ranges(ranges_data: Dict[str, Any], default_ranges: WeatherRanges) -> WeatherRanges:
    """Parse weather ranges with defaults"""
    if not ranges_data:
        return default_ranges

    return WeatherRanges(
        precipitation_min=ranges_data.get('precipitation_min', default_ranges.precipitation_min),
        precipitation_max=ranges_data.get('precipitation_max', default_ranges.precipitation_max),
        temperature_min=ranges_data.get('temperature_min', default_ranges.temperature_min),
        temperature_max=ranges_data.get('temperature_max', default_ranges.temperature_max),
        atmospheric_pressure_min=ranges_data.get('atmospheric_pressure_min', default_ranges.atmospheric_pressure_min),
        atmospheric_pressure_max=ranges_data.get('atmospheric_pressure_max', default_ranges.atmospheric_pressure_max),
        humidity_min=ranges_data.get('humidity_min', default_ranges.humidity_min),
        humidity_max=ranges_data.get('humidity_max', default_ranges.humidity_max),
        wind_speed_min=ranges_data.get('wind_speed_min', default_ranges.wind_speed_min),
        wind_speed_max=ranges_data.get('wind_speed_max', default_ranges.wind_speed_max),
        wind_direction_min=ranges_data.get('wind_direction_min', default_ranges.wind_direction_min),
        wind_direction_max=ranges_data.get('wind_direction_max', default_ranges.wind_direction_max),
        precipitation_step=ranges_data.get('precipitation_step', default_ranges.precipitation_step),
        temperature_step=ranges_data.get('temperature_step', default_ranges.temperature_step),
        atmospheric_pressure_step=ranges_data.get('atmospheric_pressure_step', default_ranges.atmospheric_pressure_step),
        humidity_step=ranges_data.get('humidity_step', default_ranges.humidity_step),
        wind_speed_step=ranges_data.get('wind_speed_step', default_ranges.wind_speed_step),
        wind_direction_step=ranges_data.get('wind_direction_step', default_ranges.wind_direction_step)
    )


def on_create(data: Any) -> Dict[str, Any]:
    """
    Initialize weather simulation with default weather ranges.

    Args:
        data: Dict with flat parameters:
            - use_random_walk: bool (default False)
            - precipitation_min: float (default 0.0)
            - precipitation_max: float (default 50.0)
            - precipitation_step: float (default 2.0)
            - temperature_min: float (default -10.0)
            - temperature_max: float (default 40.0)
            - temperature_step: float (default 0.5)
            - atmospheric_pressure_min: float (default 980.0)
            - atmospheric_pressure_max: float (default 1040.0)
            - atmospheric_pressure_step: float (default 1.0)
            - humidity_min: float (default 0.0)
            - humidity_max: float (default 100.0)
            - humidity_step: float (default 2.0)
            - wind_speed_min: float (default 0.0)
            - wind_speed_max: float (default 30.0)
            - wind_speed_step: float (default 1.0)
            - wind_direction_min: float (default 0.0)
            - wind_direction_max: float (default 360.0)
            - wind_direction_step: float (default 10.0)

    Returns:
        Status dict
    """
    global _config

    # Parse flat parameters
    use_random_walk = bool(data.get('use_random_walk', False))

    default_weather_ranges = WeatherRanges(
        precipitation_min=float(data.get('precipitation_min', 0.0)),
        precipitation_max=float(data.get('precipitation_max', 50.0)),
        precipitation_step=float(data.get('precipitation_step', 2.0)),
        temperature_min=float(data.get('temperature_min', -10.0)),
        temperature_max=float(data.get('temperature_max', 40.0)),
        temperature_step=float(data.get('temperature_step', 0.5)),
        atmospheric_pressure_min=float(data.get('atmospheric_pressure_min', 980.0)),
        atmospheric_pressure_max=float(data.get('atmospheric_pressure_max', 1040.0)),
        atmospheric_pressure_step=float(data.get('atmospheric_pressure_step', 1.0)),
        humidity_min=float(data.get('humidity_min', 0.0)),
        humidity_max=float(data.get('humidity_max', 100.0)),
        humidity_step=float(data.get('humidity_step', 2.0)),
        wind_speed_min=float(data.get('wind_speed_min', 0.0)),
        wind_speed_max=float(data.get('wind_speed_max', 30.0)),
        wind_speed_step=float(data.get('wind_speed_step', 1.0)),
        wind_direction_min=float(data.get('wind_direction_min', 0.0)),
        wind_direction_max=float(data.get('wind_direction_max', 360.0)),
        wind_direction_step=float(data.get('wind_direction_step', 10.0))
    )

    _config['default_weather_ranges'] = default_weather_ranges
    _config['use_random_walk'] = use_random_walk

    return {
        'status': 'initialized',
        'message': 'Weather simulation initialized with default ranges',
        'use_random_walk': use_random_walk
    }


def on_receive(data: Any) -> Dict[str, Any]:
    """
    Generate weather timeseries for areas.

    Args:
        data: Dict containing:
            - start_time: ISO timestamp (optional, defaults to current time)
            - time_delta: Seconds between timesteps (required)
            - total_time: Total duration in seconds (required)
            - areas: List of area dicts (required):
                - name: str (required)
                - x: float 0-1 (required)
                - y: float 0-1 (required)
                - precipitation: float (optional, default 0.0)
                - temperature: float (optional, default 20.0)
                - atmospheric_pressure: float (optional, default 1013.25)
                - humidity: float (optional, default 50.0)
                - wind_speed: float (optional, default 0.0)
                - wind_direction: float (optional, default 0.0)
                - weather_ranges: Dict (optional, uses default if not provided)

    Returns:
        Dict with area_timeseries:
            {
                "area_name": {
                    "x": float,
                    "y": float,
                    "columns": [...],
                    "timeseries": [(timestamp, precip, temp, ...)]
                }
            }
    """

    # Parse timeseries parameters
    start_time_str = data.get('start_time')
    time_delta_seconds = int(data.get('time_delta'))
    total_time_seconds = int(data.get('total_time'))
    areas_data = data.get('areas', [])
    area_data_parsed = _parse_input(areas_data)

    # Use current time if start_time not provided
    if start_time_str:
        start_time = _parse_timestamp(start_time_str)
    else:
        start_time = datetime.now(timezone.utc)

    # Calculate end time and time step
    time_step = timedelta(seconds=time_delta_seconds)
    end_time = start_time + timedelta(seconds=total_time_seconds)

    # Parse areas
    default_ranges = _config['default_weather_ranges']
    use_random_walk = bool(_config.get('use_random_walk', False))

    areas = []
    for area_data in area_data_parsed:
        # Parse per-area weather ranges if provided
        area_ranges_data = area_data.get('weather_ranges', {})
        if isinstance(area_ranges_data, str):
            area_ranges_data = json.loads(area_ranges_data)

        area_weather_ranges = _parse_weather_ranges(area_ranges_data, default_ranges)

        area = Area(
            name=area_data['name'],
            x=area_data['x'],
            y=area_data['y'],
            precipitation=area_data.get('precipitation', 0.0),
            temperature=area_data.get('temperature', 20.0),
            atmospheric_pressure=area_data.get('atmospheric_pressure', 1013.25),
            humidity=area_data.get('humidity', 50.0),
            wind_speed=area_data.get('wind_speed', 0.0),
            wind_direction=area_data.get('wind_direction', 0.0),
            weather_ranges=area_weather_ranges
        )
        areas.append(area)

    # Initialize timeseries storage for each area
    area_timeseries = {area.name: [] for area in areas}

    # Initialize current weather state for random walk (one per area)
    current_weather_state = {}
    for area in areas:
        current_weather_state[area.name] = {
            'precipitation': area.precipitation,
            'temperature': area.temperature,
            'atmospheric_pressure': area.atmospheric_pressure,
            'humidity': area.humidity,
            'wind_speed': area.wind_speed,
            'wind_direction': area.wind_direction
        }

    # Iterate through time
    current_time = start_time

    while current_time <= end_time:
        # Generate weather data for each area
        for area in areas:
            if use_random_walk and area.weather_ranges:
                # Apply random walk to current state using area-specific ranges
                state = current_weather_state[area.name]
                ranges = area.weather_ranges

                state['precipitation'] = _random_walk_step(
                    state['precipitation'],
                    ranges.precipitation_step,
                    ranges.precipitation_min,
                    ranges.precipitation_max
                )
                state['temperature'] = _random_walk_step(
                    state['temperature'],
                    ranges.temperature_step,
                    ranges.temperature_min,
                    ranges.temperature_max
                )
                state['atmospheric_pressure'] = _random_walk_step(
                    state['atmospheric_pressure'],
                    ranges.atmospheric_pressure_step,
                    ranges.atmospheric_pressure_min,
                    ranges.atmospheric_pressure_max
                )
                state['humidity'] = _random_walk_step(
                    state['humidity'],
                    ranges.humidity_step,
                    ranges.humidity_min,
                    ranges.humidity_max
                )
                state['wind_speed'] = _random_walk_step(
                    state['wind_speed'],
                    ranges.wind_speed_step,
                    ranges.wind_speed_min,
                    ranges.wind_speed_max
                )
                state['wind_direction'] = _random_walk_step(
                    state['wind_direction'],
                    ranges.wind_direction_step,
                    ranges.wind_direction_min,
                    ranges.wind_direction_max
                )

                # Create area with current state
                current_area = Area(
                    name=area.name,
                    x=area.x,
                    y=area.y,
                    precipitation=state['precipitation'],
                    temperature=state['temperature'],
                    atmospheric_pressure=state['atmospheric_pressure'],
                    humidity=state['humidity'],
                    wind_speed=state['wind_speed'],
                    wind_direction=state['wind_direction']
                )
            else:
                # Use static values from initial area
                current_area = area

            # Store as tuple
            data_tuple = (
                current_time.isoformat(),
                current_area.precipitation,
                current_area.temperature,
                current_area.atmospheric_pressure,
                current_area.humidity,
                current_area.wind_speed,
                current_area.wind_direction
            )

            area_timeseries[area.name].append(data_tuple)

        current_time += time_step

    # Format output with columnar structure
    columns = ['timestamp', 'precipitation', 'temperature', 'atmospheric_pressure',
               'humidity', 'wind_speed', 'wind_direction']

    area_timeseries_output = {}
    for area in areas:
        area_timeseries_output[area.name] = {
            'x': area.x,
            'y': area.y,
            'columns': columns,
            'timeseries': area_timeseries[area.name]
        }

    # Calculate stats
    num_timesteps = len(area_timeseries[areas[0].name])

    return {
        'status': 'success',
        'area_timeseries': area_timeseries_output,
        'start_time': start_time.isoformat(),
        'end_time': end_time.isoformat(),
        'time_delta_seconds': time_delta_seconds,
        'total_time_seconds': total_time_seconds,
        'num_timesteps': num_timesteps
    }


def on_destroy(data: Any = None) -> Dict[str, Any]:
    """Clean up resources"""
    global _config
    _config.clear()

    return {
        'status': 'destroyed',
        'message': 'Weather simulation destroyed'
    }
