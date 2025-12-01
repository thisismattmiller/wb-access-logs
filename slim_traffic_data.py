#!/usr/bin/env python3
"""
Slim Traffic Data Converter
Converts the rich traffic_per_minute_geo.json into a minimal format suitable for visualization.

Optimizations:
1. Use arrays instead of objects for time series (position-based)
2. Use country codes only (not full names) - lookup table provided separately
3. Only include top N countries per minute (rest grouped as "other")
4. Remove redundant data (bytes, detailed status codes per minute)
5. Use Unix timestamps instead of ISO strings
6. Compress country data to just [code, count] pairs
"""

import json
import sys
from datetime import datetime

def parse_iso_timestamp(ts_str):
    """Parse ISO timestamp to Unix timestamp (seconds)."""
    # Handle format like "2025-09-27T00:00:00"
    dt = datetime.fromisoformat(ts_str)
    return int(dt.timestamp())

def slim_traffic_data(input_file='traffic_per_minute_geo.json',
                      output_file='traffic_slim.json',
                      top_countries=5):
    """Convert rich traffic data to slim format."""

    print(f"Loading {input_file}...")
    with open(input_file, 'r') as f:
        data = json.load(f)

    original_size = len(json.dumps(data))
    print(f"Original size: {original_size / (1024*1024):.2f} MB")

    metadata = data['metadata']
    statistics = data['statistics']
    time_series = data['time_series']

    print(f"Processing {len(time_series)} time points...")

    # Build country code to name lookup (for reference)
    country_lookup = {}
    for code, info in statistics.get('country_totals', {}).items():
        country_lookup[code] = info['name']

    # Determine top countries overall (for consistent ordering)
    top_overall = sorted(
        statistics.get('country_totals', {}).items(),
        key=lambda x: x[1]['count'],
        reverse=True
    )[:top_countries]
    top_country_codes = [code for code, _ in top_overall]

    print(f"Top {top_countries} countries: {', '.join(top_country_codes)}")

    # Build slim time series
    # Format: [timestamp, requests, [country_counts...], other_count]
    # country_counts are in the same order as top_country_codes
    slim_series = []

    start_ts = parse_iso_timestamp(time_series[0]['timestamp'])

    for entry in time_series:
        ts = parse_iso_timestamp(entry['timestamp'])
        # Use offset from start in minutes to save space
        minute_offset = (ts - start_ts) // 60

        requests = entry['requests']

        # Get counts for top countries
        country_counts = []
        other_count = 0

        for code in top_country_codes:
            if code in entry['countries']:
                country_counts.append(entry['countries'][code]['count'])
            else:
                country_counts.append(0)

        # Sum up "other" countries
        for code, info in entry['countries'].items():
            if code not in top_country_codes:
                other_count += info['count']

        # Format: [minute_offset, requests, c1, c2, c3, c4, c5, other]
        slim_entry = [minute_offset, requests] + country_counts + [other_count]
        slim_series.append(slim_entry)

    # Build slim status codes (overall only, not per minute)
    status_totals = statistics.get('status_code_totals', {})

    # Build output
    slim_data = {
        # Minimal metadata
        'm': {
            'start': start_ts,  # Unix timestamp of first minute
            'minutes': len(time_series),
            'interval': 60,  # seconds per data point
        },
        # Statistics summary
        's': {
            'total': statistics['total_requests'],
            'avg': statistics['avg_requests_per_minute'],
            'max': statistics['max_requests_per_minute'],
            'min': statistics['min_requests_per_minute'],
            'peak_offset': (parse_iso_timestamp(statistics['peak_minute']) - start_ts) // 60,
        },
        # Country lookup (code -> name)
        'countries': country_lookup,
        # Top countries in order (for decoding series data)
        'top': top_country_codes,
        # Status code totals
        'status': status_totals,
        # Country totals (slim: code -> count)
        'country_totals': {
            code: info['count']
            for code, info in statistics.get('country_totals', {}).items()
        },
        # Time series: [minute_offset, requests, c1, c2, c3, c4, c5, other]
        'd': slim_series
    }

    # Write output
    print(f"Writing {output_file}...")

    # Use compact JSON (no indentation, minimal whitespace)
    with open(output_file, 'w') as f:
        json.dump(slim_data, f, separators=(',', ':'))

    new_size = len(json.dumps(slim_data, separators=(',', ':')))
    print(f"New size: {new_size / (1024*1024):.2f} MB")
    print(f"Reduction: {(1 - new_size/original_size) * 100:.1f}%")

    # Also write a pretty version for debugging
    debug_file = output_file.replace('.json', '_debug.json')
    with open(debug_file, 'w') as f:
        json.dump(slim_data, f, indent=2)

    print(f"Debug version written to: {debug_file}")

    # Print sample of output format
    print("\n" + "=" * 60)
    print("OUTPUT FORMAT")
    print("=" * 60)
    print(f"\nTop countries (in order): {slim_data['top']}")
    print(f"\nTime series format: [minute_offset, requests, {', '.join(top_country_codes)}, other]")
    print(f"\nSample entries:")
    for i, entry in enumerate(slim_series[:3]):
        print(f"  {entry}")
    print("  ...")

    print("\n" + "=" * 60)
    print("USAGE IN JAVASCRIPT")
    print("=" * 60)
    print("""
// Load the data
const data = await fetch('traffic_slim.json').then(r => r.json());

// Get timestamp for a data point
function getTimestamp(index) {
    return new Date((data.m.start + data.d[index][0] * 60) * 1000);
}

// Get requests for a data point
function getRequests(index) {
    return data.d[index][1];
}

// Get country breakdown for a data point
function getCountryBreakdown(index) {
    const entry = data.d[index];
    const result = {};
    data.top.forEach((code, i) => {
        result[code] = entry[2 + i];
    });
    result['other'] = entry[entry.length - 1];
    return result;
}

// Get country name from code
function getCountryName(code) {
    return data.countries[code] || code;
}
""")

if __name__ == '__main__':
    input_file = sys.argv[1] if len(sys.argv) > 1 else 'traffic_per_minute_geo.json'
    output_file = sys.argv[2] if len(sys.argv) > 2 else 'traffic_slim.json'
    top_countries = int(sys.argv[3]) if len(sys.argv) > 3 else 5

    slim_traffic_data(input_file, output_file, top_countries)
