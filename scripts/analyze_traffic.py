#!/usr/bin/env python3
"""
Traffic Analysis Script
Analyzes nginx access logs to generate traffic per minute data for visualization.
Outputs a JSON file suitable for rendering a line graph/histogram.
"""

import re
import json
import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# Nginx combined log format regex
LOG_PATTERN = re.compile(
    r'(?P<ip>\d+\.\d+\.\d+\.\d+)\s+'
    r'-\s+-\s+'
    r'\[(?P<datetime>[^\]]+)\]\s+'
    r'"(?P<method>\w+)\s+(?P<url>[^\s]+)\s+[^"]*"\s+'
    r'(?P<status>\d+)\s+'
    r'(?P<size>\d+|-)\s+'
    r'"(?P<referer>[^"]*)"\s+'
    r'"(?P<user_agent>[^"]*)"'
)

def parse_datetime(dt_str):
    """Parse nginx datetime format: 10/Oct/2025:00:00:12 -0400"""
    try:
        dt = datetime.strptime(dt_str, '%d/%b/%Y:%H:%M:%S %z')
        return dt
    except ValueError:
        try:
            dt = datetime.strptime(dt_str.split()[0], '%d/%b/%Y:%H:%M:%S')
            return dt
        except ValueError:
            return None

def truncate_to_minute(dt):
    """Truncate datetime to minute precision."""
    return dt.replace(second=0, microsecond=0)

def analyze_traffic(log_dir, output_file='traffic_per_minute.json'):
    """Analyze all log files and generate traffic per minute data."""

    # Traffic counters per minute
    requests_per_minute = defaultdict(int)
    bytes_per_minute = defaultdict(int)
    status_per_minute = defaultdict(lambda: defaultdict(int))  # minute -> status_code -> count

    # Get all log files
    log_path = Path(log_dir)
    log_files = sorted([f for f in log_path.iterdir()
                       if f.is_file() and f.name.startswith('access.log')])

    if not log_files:
        print(f"No log files found in {log_dir}")
        return

    print(f"Found {len(log_files)} log files to analyze...")
    print()

    total_lines = 0
    parsed_lines = 0

    for log_file in log_files:
        file_size = log_file.stat().st_size / (1024 * 1024)
        print(f"Processing {log_file.name} ({file_size:.1f} MB)...")

        try:
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    total_lines += 1

                    match = LOG_PATTERN.match(line.strip())
                    if not match:
                        continue

                    data = match.groupdict()

                    dt = parse_datetime(data['datetime'])
                    if not dt:
                        continue

                    parsed_lines += 1

                    # Truncate to minute
                    minute_key = truncate_to_minute(dt)
                    minute_str = minute_key.isoformat()

                    # Count requests
                    requests_per_minute[minute_str] += 1

                    # Count bytes
                    size = data['size']
                    if size != '-':
                        bytes_per_minute[minute_str] += int(size)

                    # Count by status code
                    status = data['status']
                    status_per_minute[minute_str][status] += 1

        except Exception as e:
            print(f"  Error processing {log_file.name}: {e}")

    print(f"\nProcessed {parsed_lines:,} of {total_lines:,} lines")

    # Sort by time and build output
    sorted_minutes = sorted(requests_per_minute.keys())

    if not sorted_minutes:
        print("No data found!")
        return

    print(f"Time range: {sorted_minutes[0]} to {sorted_minutes[-1]}")
    print(f"Total minutes: {len(sorted_minutes):,}")

    # Calculate statistics
    request_counts = list(requests_per_minute.values())
    avg_rpm = sum(request_counts) / len(request_counts)
    max_rpm = max(request_counts)
    min_rpm = min(request_counts)

    # Find peak minute
    peak_minute = max(requests_per_minute.items(), key=lambda x: x[1])

    print(f"\nTraffic Statistics:")
    print(f"  Average requests/minute: {avg_rpm:.1f}")
    print(f"  Max requests/minute: {max_rpm:,} (at {peak_minute[0]})")
    print(f"  Min requests/minute: {min_rpm:,}")
    print(f"  Total requests: {sum(request_counts):,}")

    # Build time series data
    time_series = []
    for minute_str in sorted_minutes:
        entry = {
            'timestamp': minute_str,
            'requests': requests_per_minute[minute_str],
            'bytes': bytes_per_minute[minute_str],
            'status_codes': dict(status_per_minute[minute_str])
        }
        time_series.append(entry)

    # Group status codes for summary
    status_totals = defaultdict(int)
    for minute_str in sorted_minutes:
        for status, count in status_per_minute[minute_str].items():
            status_totals[status] += count

    # Build output data
    export_data = {
        'metadata': {
            'source_directory': log_dir,
            'total_lines': total_lines,
            'parsed_lines': parsed_lines,
            'total_minutes': len(sorted_minutes),
            'start_time': sorted_minutes[0],
            'end_time': sorted_minutes[-1],
            'generated_at': datetime.now().isoformat()
        },
        'statistics': {
            'total_requests': sum(request_counts),
            'total_bytes': sum(bytes_per_minute.values()),
            'avg_requests_per_minute': round(avg_rpm, 2),
            'max_requests_per_minute': max_rpm,
            'min_requests_per_minute': min_rpm,
            'peak_minute': peak_minute[0],
            'peak_requests': peak_minute[1],
            'status_code_totals': dict(status_totals)
        },
        'time_series': time_series
    }

    # Write output
    with open(output_file, 'w') as f:
        json.dump(export_data, f, indent=2)

    print(f"\nExported to: {output_file}")
    print(f"File size: {os.path.getsize(output_file) / (1024*1024):.2f} MB")

    # Print summary report
    print("\n" + "=" * 60)
    print("TRAFFIC ANALYSIS SUMMARY")
    print("=" * 60)
    print(f"\nStatus Code Distribution:")
    for status, count in sorted(status_totals.items(), key=lambda x: x[1], reverse=True):
        pct = (count / sum(request_counts)) * 100
        print(f"  {status}: {count:>12,} ({pct:>5.1f}%)")

if __name__ == '__main__':
    # Default paths relative to scripts/ directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    default_log_dir = os.path.join(script_dir, '..', 'access_logs')
    default_output = os.path.join(script_dir, '..', 'data', 'traffic_per_minute.json')

    log_directory = sys.argv[1] if len(sys.argv) > 1 else default_log_dir
    output_file = sys.argv[2] if len(sys.argv) > 2 else default_output

    if not os.path.isdir(log_directory):
        print(f"Error: Directory '{log_directory}' not found")
        sys.exit(1)

    analyze_traffic(log_directory, output_file)
