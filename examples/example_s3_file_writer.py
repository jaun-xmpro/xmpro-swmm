"""
Example: Writing Files to AWS S3

This example demonstrates how to:
1. Initialize S3 file writer with credentials
2. Write JSON data to S3
3. Write string content to S3
4. Use different locations and filenames

Note: You need valid AWS credentials to run this example.
"""

import sys
from pathlib import Path
import json
from datetime import datetime

# Add parent directory to path to import metaagents
sys.path.insert(0, str(Path(__file__).parent.parent))

from metaagents.aws.s3.file_writer import metaagent as s3_writer


def main():
    print("=" * 60)
    print("S3 File Writer Example")
    print("=" * 60)

    # IMPORTANT: Update these with your AWS credentials
    AWS_ACCESS_KEY_ID = "your_access_key"
    AWS_SECRET_ACCESS_KEY = "your_secret_key"
    AWS_REGION = "us-east-1"
    BUCKET = "xmtwin"

    # Step 1: Initialize S3 file writer
    print("\n1. Initializing S3 file writer...")
    result = s3_writer.on_create({
        "aws_access_key_id": AWS_ACCESS_KEY_ID,
        "aws_secret_access_key": AWS_SECRET_ACCESS_KEY,
        "region_name": AWS_REGION,
        "bucket": BUCKET
    })

    if result['status'] == 'error':
        print(f"   Error: {result['message']}")
        return

    print(f"   Status: {result['status']}")
    print(f"   Region: {result['region']}")
    print(f"   Bucket: {result['bucket']}")

    # Step 2: Write JSON data to S3
    print("\n2. Writing JSON data to S3...")

    # Create sample simulation results
    sample_data = {
        "timestamp": datetime.now().isoformat(),
        "simulation_id": "sim_001",
        "results": {
            "peak_flow": 125.5,
            "total_volume": 1500.2,
            "duration_hours": 3.5
        },
        "status": "completed"
    }

    write_result = s3_writer.on_receive({
        "content": sample_data,  # Will be auto-converted to JSON
        "location": "water_utilities/flood_management/outputs",
        "filename": "simulation_results_001.json"
    })

    if write_result['status'] == 'error':
        print(f"   Error: {write_result['message']}")
    else:
        print(f"   Status: {write_result['status']}")
        print(f"   S3 Path: {write_result['s3_path']}")
        print(f"   Size: {write_result['size']} bytes")
        print(f"   ETag: {write_result['etag']}")

    # Step 3: Write string content to a text file
    print("\n3. Writing string content to S3...")

    log_message = f"Process started at: {datetime.now().isoformat()}\nStatus: Running\nProgress: 50%"

    write_result2 = s3_writer.on_receive({
        "content": log_message,
        "location": "water_utilities/flood_management/logs",
        "filename": "process_log.txt"
    })

    if write_result2['status'] == 'error':
        print(f"   Error: {write_result2['message']}")
    else:
        print(f"   Status: {write_result2['status']}")
        print(f"   S3 Path: {write_result2['s3_path']}")
        print(f"   Size: {write_result2['size']} bytes")

    # Step 4: Write alert to different location
    print("\n4. Writing alert to different location...")

    alert_data = {
        "alert_type": "high_water_level",
        "severity": "warning",
        "location": "Station A",
        "value": 2.5,
        "threshold": 2.0,
        "timestamp": datetime.now().isoformat()
    }

    write_result3 = s3_writer.on_receive({
        "content": alert_data,
        "location": "water_utilities/flood_management/alerts",
        "filename": "alert_001.json"
    })

    if write_result3['status'] == 'error':
        print(f"   Error: {write_result3['message']}")
    else:
        print(f"   Status: {write_result3['status']}")
        print(f"   S3 Path: {write_result3['s3_path']}")

    # Step 5: Write with timestamp-based filename
    print("\n5. Writing with timestamp-based filename...")

    timestamp_filename = f"weather_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    weather_data = {
        "temperature": 22.5,
        "humidity": 65,
        "pressure": 1013.25,
        "wind_speed": 5.2,
        "rainfall": 0.0
    }

    write_result4 = s3_writer.on_receive({
        "content": weather_data,
        "location": "water_utilities/flood_management/weather",
        "filename": timestamp_filename
    })

    if write_result4['status'] == 'error':
        print(f"   Error: {write_result4['message']}")
    else:
        print(f"   Status: {write_result4['status']}")
        print(f"   S3 Path: {write_result4['s3_path']}")

    # Step 6: Write CSV content
    print("\n6. Writing CSV content...")

    csv_content = "timestamp,flow_rate,water_level\n"
    csv_content += f"{datetime.now().isoformat()},125.5,2.3\n"
    csv_content += f"{datetime.now().isoformat()},130.2,2.5\n"
    csv_content += f"{datetime.now().isoformat()},128.7,2.4\n"

    write_result5 = s3_writer.on_receive({
        "content": csv_content,
        "location": "water_utilities/flood_management/exports",
        "filename": "sensor_data.csv"
    })

    if write_result5['status'] == 'error':
        print(f"   Error: {write_result5['message']}")
    else:
        print(f"   Status: {write_result5['status']}")
        print(f"   S3 Path: {write_result5['s3_path']}")

    # Step 7: Write to nested folder structure
    print("\n7. Writing to nested folder structure...")

    date_path = datetime.now().strftime("%Y/%m/%d")

    write_result6 = s3_writer.on_receive({
        "content": {"status": "daily_report", "date": datetime.now().isoformat()},
        "location": f"water_utilities/flood_management/reports/{date_path}",
        "filename": "daily_summary.json"
    })

    if write_result6['status'] == 'error':
        print(f"   Error: {write_result6['message']}")
    else:
        print(f"   Status: {write_result6['status']}")
        print(f"   S3 Path: {write_result6['s3_path']}")

    # Cleanup
    print("\n8. Cleaning up...")
    s3_writer.on_destroy()

    print("\n" + "=" * 60)
    print("Example completed!")
    print("\n")
    print("Summary of files written:")
    print(f"   1. {write_result.get('s3_path', 'N/A')}")
    print(f"   2. {write_result2.get('s3_path', 'N/A')}")
    print(f"   3. {write_result3.get('s3_path', 'N/A')}")
    print(f"   4. {write_result4.get('s3_path', 'N/A')}")
    print(f"   5. {write_result5.get('s3_path', 'N/A')}")
    print(f"   6. {write_result6.get('s3_path', 'N/A')}")
    print("=" * 60)


if __name__ == "__main__":
    main()
