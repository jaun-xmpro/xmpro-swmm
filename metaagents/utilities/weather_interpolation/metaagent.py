"""
Weather Interpolation MetaAgent

Jaun van Heerden
2025

This metaagent interpolates weather data from observation points to query points using
Inverse Distance Weighting (IDW).

Input: Observation point timeseries from weather_simulation_v2
Output: Interpolated timeseries for named query points

This metaagent sits between weather_simulation_v2 and weather_to_pyswmm in the pipeline.
"""

from typing import Dict, Any, List, Tuple
import json
import math

def _parse_input(data: Any) -> Dict[str, Any]:
    """Parse input, handling JSON strings"""
    if isinstance(data, str):
        return json.loads(data)
    return data


def _calculate_distance(x1: float, y1: float, x2: float, y2: float) -> float:
    """Calculate Euclidean distance between two points"""
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


def _interpolate_value(
    query_x: float,
    query_y: float,
    observation_points: List[Dict[str, Any]],
    value_index: int,
    power: float = 2.0
) -> float:
    """
    Interpolate a single value using Inverse Distance Weighting (IDW).

    Args:
        query_x, query_y: Query point coordinates
        observation_points: List of observation point dicts with x, y, and values
        value_index: Which value to interpolate from the timeseries tuple
        power: IDW power parameter (higher = more emphasis on nearby points)

    Returns:
        Interpolated value
    """
    # Check if query point matches an observation point exactly
    for obs_point in observation_points:
        if abs(obs_point['x'] - query_x) < 1e-10 and abs(obs_point['y'] - query_y) < 1e-10:
            # Exact match - return the observation value directly
            return obs_point['value']

    # Calculate weights using IDW
    total_weight = 0.0
    weighted_sum = 0.0

    for obs_point in observation_points:
        distance = _calculate_distance(query_x, query_y, obs_point['x'], obs_point['y'])

        if distance < 1e-10:  # Essentially zero distance
            return obs_point['value']

        weight = 1.0 / (distance ** power)
        weighted_sum += weight * obs_point['value']
        total_weight += weight

    return weighted_sum / total_weight


def on_create(data: Any) -> Dict[str, Any]:
    """
    Initialize interpolation metaagent.

    Args:
        data: Dict with 'config' containing:
            - interpolation_power: float (default 2.0)

    Returns:
        Status dict
    """

    return {
        'status': 'initialized',
        'message': 'Weather interpolation initialized',
    }


def on_receive(data: Any) -> Dict[str, Any]:
    """
    Interpolate weather data from observation points to query points.

    Args:
        data: Dict containing:
            - observation_timeseries: From weather_simulation_v2 output
            - query_points: List of dicts with 'name', 'x', 'y'

    Returns:
        Dict with query_timeseries in columnar format
    """


    timeseries = data.get('timeseries', {})
    timeseries_parsed = _parse_input(timeseries)
    area_timeseries = timeseries_parsed.get('area_timeseries')
    query_points = data.get('query', {})
    query_points_parsed = _parse_input(query_points)
    num_timesteps = timeseries_parsed.get('num_timesteps', None)

    # Get metadata to pass on
    start_time = timeseries_parsed.get('start_time')
    end_time = timeseries_parsed.get('end_time')
    time_delta_seconds = timeseries_parsed.get('time_delta_seconds')
    total_time_seconds = timeseries_parsed.get('total_time_seconds')
    num_timesteps = timeseries_parsed.get('num_timesteps')

    # Interpolate for each query point
    query_timeseries = {}

    # Save first as a reference
    first_obs = next(iter(area_timeseries.values()))
    columns = first_obs['columns']

    for qname, qdata in query_points_parsed.items():
        qx = qdata['x']
        qy = qdata['y']

        interpolated_timeseries = []

        # For each timestep
        for timestep_idx in range(num_timesteps):

            # Get timestamp from first area point (all have same timestamps)
            timestamp = first_obs['timeseries'][timestep_idx][0]

            # Prepare area point data for this timestep
            area_points_at_time = []
            for area_name, area_data in area_timeseries.items():
                timeseries_tuple = area_data['timeseries'][timestep_idx]
                area_points_at_time.append({
                    'name': area_name,
                    'x': area_data['x'],
                    'y': area_data['y'],
                    'data': timeseries_tuple
                })

            # Interpolate each weather parameter (skip timestamp at index 0)
            interpolated_values = [timestamp]  # Start with timestamp

            for col_idx in range(1, len(columns)):  # Skip timestamp column
                # Build area points with current parameter value
                area_points_for_param = [
                    {
                        'x': area['x'],
                        'y': area['y'],
                        'value': area['data'][col_idx]
                    }
                    for area in area_points_at_time
                ]

                # Interpolate this parameter
                interpolated_value = _interpolate_value(
                    qx, qy,
                    area_points_for_param,
                    col_idx,
                    2.0
                )
                interpolated_values.append(interpolated_value)

            # Store as tuple
            interpolated_timeseries.append(tuple(interpolated_values))

        # Store query point timeseries in columnar format
        query_timeseries[qname] = {
            'x': qx,
            'y': qy,
            'columns': columns,
            'timeseries': interpolated_timeseries
        }

    return {
        'status': 'success',
        'timeseries': query_timeseries,
        'start_time': start_time,
        'end_time': end_time,
        'time_delta_seconds': time_delta_seconds,
        'total_time_seconds': total_time_seconds,
        'num_timesteps': num_timesteps
    }


def on_destroy(data: Any = None) -> Dict[str, Any]:
    """Clean up resources"""

    return {
        'status': 'destroyed',
        'message': 'Weather interpolation destroyed'
    }
