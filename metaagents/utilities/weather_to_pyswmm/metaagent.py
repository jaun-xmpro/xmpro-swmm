"""
Weather to PySWMM Converter MetaAgent

Jaun van Heerden
2025

This metaagent converts timeseries output from the weather_simulation metaagent
to the format required by the pyswmm_simulation metaagent.

Input: Weather simulation columnar timeseries format
Output: PySWMM timeseries format with MM/DD/YYYY  HH:MM:SS     VALUE lines

The converter:
- Takes weather simulation output with area-based columnar timeseries
- Extracts precipitation data (or other specified weather parameter)
- Converts timestamps from ISO 8601 to MM/DD/YYYY  HH:MM:SS format
- Formats values as required by SWMM
- Optionally updates SWMM OPTIONS section (start/end dates and times)
- Outputs data ready for pyswmm_simulation metaagent
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from dataclasses import dataclass
import json

def _parse_input(data: Any) -> Dict[str, Any]:
    """Parse input data, handling both dict and JSON string formats"""
    if isinstance(data, str):
        return json.loads(data)
    return data


def _calculate_swmm_date_range(start_time_str: str, end_time_str: str) -> Dict[str, str]:
    """
    Calculate SWMM date range based on current time and input time difference.
    
    Args:
        start_time_str: ISO format start time
        end_time_str: ISO format end time
        
    Returns:
        Dict with start_date, start_time, end_date, end_time in SWMM format
    """
    # Parse input times
    start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
    end_time = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
    
    # Calculate duration
    duration = end_time - start_time
    
    # Apply to current time
    new_start = datetime.now(timezone.utc)
    new_end = new_start + duration
    
    return {
        'start_date': new_start.strftime('%m/%d/%Y'),
        'start_time': new_start.strftime('%H:%M:%S'),
        'end_date': new_end.strftime('%m/%d/%Y'),
        'end_time': new_end.strftime('%H:%M:%S')
    }

def _convert_timestamp_to_swmm(iso_timestamp: str) -> tuple[str, str]:
    """
    Convert ISO 8601 timestamp to SWMM format components.

    Args:
        iso_timestamp: ISO format like '2024-10-22T00:00:00+00:00' or '2024-10-22T00:00:00Z'

    Returns:
        Tuple of (date_str, time_str) like ('10/22/2024', '00:00:00')
    """
    # Handle both 'Z' and '+00:00' timezone formats
    timestamp_str = iso_timestamp.replace('Z', '+00:00')
    dt = datetime.fromisoformat(timestamp_str)

    date_str = dt.strftime('%m/%d/%Y')  # MM/DD/YYYY
    time_str = dt.strftime('%H:%M:%S')  # HH:MM:SS

    return date_str, time_str


def _format_swmm_line(date_str: str, time_str: str, value: float, decimal_places: int = 2) -> str:
    """
    Format a single SWMM timeseries data line.

    Format: 'MM/DD/YYYY  HH:MM:SS     VALUE'
    Two spaces between date and time, five spaces between time and value.

    Args:
        date_str: Date in MM/DD/YYYY format
        time_str: Time in HH:MM:SS format
        value: Numeric value
        decimal_places: Number of decimal places for value

    Returns:
        Formatted SWMM data line
    """
    value_formatted = f"{value:.{decimal_places}f}"
    return f"{date_str}  {time_str}     {value_formatted}"


def _convert_area_timeseries_to_swmm(
    area_data: Dict[str, Any],
    parameter: str,
    decimal_places: int = 2
) -> List[str]:
    """
    Convert a single area's columnar timeseries to SWMM format.

    Args:
        area_data: Dict with 'columns', 'timeseries', 'x', 'y'
        parameter: Which parameter to extract (e.g., 'precipitation')
        decimal_places: Number of decimal places for values

    Returns:
        List of SWMM-formatted data lines
    """
    columns = area_data.get('columns', [])
    timeseries = area_data.get('timeseries', [])

    # Find the index of the desired parameter
    if parameter not in columns:
        raise ValueError(f"Parameter '{parameter}' not found in columns: {columns}")

    param_idx = columns.index(parameter)

    # Convert each data point
    swmm_lines = []
    for data_tuple in timeseries:
        # data_tuple[0] is always timestamp
        # data_tuple[param_idx] is the parameter value
        iso_timestamp = data_tuple[0]
        value = data_tuple[param_idx]

        date_str, time_str = _convert_timestamp_to_swmm(iso_timestamp)
        line = _format_swmm_line(date_str, time_str, value, decimal_places)
        swmm_lines.append(line)

    return swmm_lines

def on_create(data: Any) -> Dict[str, Any]:
    """
    Initialize the converter with configuration.

    Args:
        data: Configuration dict or JSON string with optional parameters:
            - parameter: str = 'precipitation' - Which weather parameter to extract
            - value_multiplier: float = 1.0 - Multiply values by this factor
            - decimal_places: int = 2 - Number of decimal places for values
            - auto_date_range: bool = True - Auto-calculate start/end dates

    Returns:
        Status dict with configuration details
    """

    return {
        'status': 'initialized',
        'message': 'Weather to PySWMM converter initialized'
    }


def on_receive(data: Any) -> Dict[str, Any]:
    """
    Convert weather simulation timeseries to PySWMM format.

    Args:
        data: Dict or JSON string containing:
            - timeseries_by_area: Weather simulation output (required)
            - options: Optional dict to override/add to OPTIONS section
            - area_mapping: Optional dict to rename areas (e.g., {'rain1': 'RainGauge1'})

    Returns:
        Dict with:
            - status: 'success' or 'error'
            - modifications: Dict ready for pyswmm_simulation on_receive
                - timeseries: Dict of area_name -> list of SWMM data lines
                - options: Dict of SWMM OPTIONS (if auto_date_range or provided)
            - conversion_stats: Statistics about the conversion
    """

    timeseries = data.get('timeseries')
    parameter = data.get('parameter', 'precipitation')

    # Get metadata
    start_time_str = data.get('start_time')
    end_time_str = data.get('end_time')

    # # Parse the ISO timestamps
    # start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
    # end_time = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))

    # # Calculate the time difference
    # time_difference = end_time - start_time

    # # Apply to current time
    # new_start_time = datetime.now(timezone.utc)
    # new_end_time = new_start_time + time_difference

    # # Format for SWMM
    # start_date = new_start_time.strftime('%m/%d/%Y')  # "10/22/2024"
    # start_time_formatted = new_start_time.strftime('%H:%M:%S')  # "14:30:00"
    # end_date = new_end_time.strftime('%m/%d/%Y')
    # end_time_formatted = new_end_time.strftime('%H:%M:%S')

    swmm_dates = _calculate_swmm_date_range(start_time_str, end_time_str)

    swmm_timeseries = {}


    for area_name, area_data in timeseries.items():
        # Convert timeseries
        swmm_lines = _convert_area_timeseries_to_swmm(
            area_data=area_data,
            parameter=parameter
        )

        swmm_timeseries[area_name] = swmm_lines


    # Build modifications dict for pyswmm_simulation
    modifications = {
        'timeseries': swmm_timeseries,
        'options': swmm_dates
    }

    # Add OPTIONS if auto_date_range is enabled or options provided
    # if conversion_config.auto_date_range or options:
    #     # Extract date range from timeseries
    #     date_range = _extract_date_range(timeseries_by_area)

    #     # Merge with provided options (provided options take precedence)
    #     swmm_options = {**date_range, **options}
    #     modifications['options'] = swmm_options

    #     conversion_stats['date_range'] = date_range

    return {
        'status': 'success',
        'modifications': json.dumps(modifications)
    }


def on_destroy(data: Any = None) -> Dict[str, Any]:
    """
    Clean up converter resources.

    Returns:
        Status dict
    """

    return {
        'status': 'destroyed',
        'message': 'Weather to PySWMM converter destroyed'
    }
