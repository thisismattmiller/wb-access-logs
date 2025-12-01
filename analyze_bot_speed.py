#!/usr/bin/env python3
"""
Bot Speed Analyzer
Analyzes bot_paths.json to calculate request rates and timing patterns for each bot type.
Outputs metrics like requests per minute, average time between requests, and burst rates.
Aggregates by bot type only (not by IP).
"""

import json
import sys
from datetime import datetime
from collections import defaultdict
from statistics import mean, median, stdev

def parse_timestamp(ts_str):
    """Parse ISO format timestamp."""
    try:
        # Handle timezone-aware timestamps
        if '+' in ts_str or ts_str.endswith('Z'):
            return datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
        return datetime.fromisoformat(ts_str)
    except ValueError:
        return None

def calculate_intervals(timestamps):
    """Calculate time intervals between consecutive requests in seconds."""
    if len(timestamps) < 2:
        return []

    intervals = []
    for i in range(1, len(timestamps)):
        delta = (timestamps[i] - timestamps[i-1]).total_seconds()
        if delta >= 0:
            intervals.append(delta)
    return intervals

def count_requests_per_second(timestamps):
    """Count how many requests occurred in each second (burst detection)."""
    if not timestamps:
        return {}

    requests_by_second = defaultdict(int)
    for ts in timestamps:
        second_key = ts.replace(microsecond=0)
        requests_by_second[second_key] += 1

    return dict(requests_by_second)

def format_duration(seconds):
    """Format seconds into human readable duration."""
    if seconds < 0.001:
        return f"{seconds*1000000:.0f}µs"
    elif seconds < 1:
        return f"{seconds*1000:.1f}ms"
    elif seconds < 60:
        return f"{seconds:.2f}s"
    elif seconds < 3600:
        return f"{seconds/60:.1f}min"
    elif seconds < 86400:
        return f"{seconds/3600:.1f}hr"
    else:
        return f"{seconds/86400:.1f}days"

def analyze_bot_speeds(input_file='bot_paths.json', output_file='bot_speed_analysis.json'):
    """Analyze request timing patterns for all bots (aggregated by bot type only)."""

    print(f"Loading {input_file}...")
    with open(input_file, 'r') as f:
        data = json.load(f)

    bot_paths = data.get('bot_paths', {})
    print(f"Found {len(bot_paths)} bot instances to analyze...")

    # Aggregate all timestamps by bot type (ignoring IP)
    bot_timestamps = defaultdict(list)
    bot_ips = defaultdict(set)

    for bot_id, records in bot_paths.items():
        if not records:
            continue

        bot_name, ip = bot_id.split('|', 1)
        bot_ips[bot_name].add(ip)

        for rec in records:
            ts = parse_timestamp(rec['timestamp'])
            if ts:
                bot_timestamps[bot_name].append(ts)

    print(f"Found {len(bot_timestamps)} unique bot types...")

    # Calculate stats for each bot type
    bot_stats = {}

    for bot_name, timestamps in bot_timestamps.items():
        if len(timestamps) < 2:
            continue

        # Sort all timestamps for this bot type
        timestamps.sort()

        # Calculate intervals between consecutive requests
        intervals = calculate_intervals(timestamps)
        if not intervals:
            continue

        # Count requests per second for burst detection
        rps_counts = count_requests_per_second(timestamps)
        max_concurrent = max(rps_counts.values()) if rps_counts else 1

        # Find when max concurrent occurred
        max_concurrent_timestamp = None
        for ts, count in rps_counts.items():
            if count == max_concurrent:
                max_concurrent_timestamp = ts.isoformat()
                break

        # Filter out zero intervals
        nonzero_intervals = [i for i in intervals if i > 0]
        zero_interval_count = len([i for i in intervals if i == 0])

        # Basic stats
        total_requests = len(timestamps)
        total_duration = (timestamps[-1] - timestamps[0]).total_seconds()
        requests_per_minute = (total_requests / total_duration) * 60 if total_duration > 0 else total_requests * 60

        # Interval stats
        sorted_intervals = sorted(intervals)
        burst_count = max(1, len(sorted_intervals) // 10)
        burst_intervals = sorted_intervals[:burst_count]

        # Burst RPM from nonzero intervals
        if nonzero_intervals:
            sorted_nonzero = sorted(nonzero_intervals)
            burst_nonzero = sorted_nonzero[:max(1, len(sorted_nonzero) // 10)]
            burst_rpm = 60 / mean(burst_nonzero)
        else:
            burst_rpm = max_concurrent * 60

        bot_stats[bot_name] = {
            'total_requests': total_requests,
            'unique_ips': len(bot_ips[bot_name]),
            'first_seen': timestamps[0].isoformat(),
            'last_seen': timestamps[-1].isoformat(),
            'total_duration_seconds': total_duration,
            'requests_per_minute': requests_per_minute,

            # Interval timing
            'avg_interval_seconds': mean(intervals),
            'median_interval_seconds': median(intervals),
            'min_interval_seconds': min(intervals),
            'min_nonzero_interval_seconds': min(nonzero_intervals) if nonzero_intervals else None,
            'max_interval_seconds': max(intervals),
            'stdev_interval_seconds': stdev(intervals) if len(intervals) > 1 else 0,

            # Concurrent/burst stats
            'zero_interval_count': zero_interval_count,
            'zero_interval_pct': (zero_interval_count / len(intervals)) * 100,
            'max_concurrent_requests': max_concurrent,
            'max_concurrent_timestamp': max_concurrent_timestamp,
            'burst_avg_interval_seconds': mean(burst_intervals),
            'burst_requests_per_minute': burst_rpm,

            # Percentiles
            'p50_interval_seconds': sorted_intervals[len(sorted_intervals) // 2],
            'p90_interval_seconds': sorted_intervals[int(len(sorted_intervals) * 0.9)],
            'p99_interval_seconds': sorted_intervals[int(len(sorted_intervals) * 0.99)] if len(sorted_intervals) >= 100 else sorted_intervals[-1],
            'p1_interval_seconds': sorted_intervals[int(len(sorted_intervals) * 0.01)] if len(sorted_intervals) >= 100 else sorted_intervals[0],
        }

    # Print summary report
    print("\n" + "=" * 110)
    print("BOT SPEED ANALYSIS REPORT (by bot type)")
    print("=" * 110)

    print(f"\n### ALL BOTS (sorted by max concurrent requests in same second) ###")
    print(f"{'Bot Name':<25} {'Requests':>10} {'IPs':>5} {'Avg Interval':>14} {'Min NonZero':>14} {'MaxConc':>8} {'When MaxConc':>20}")
    print("-" * 110)

    # Sort by max concurrent requests (highest first)
    sorted_bots = sorted(
        bot_stats.items(),
        key=lambda x: x[1]['max_concurrent_requests'],
        reverse=True
    )

    for bot_name, stats in sorted_bots:
        min_nz = stats['min_nonzero_interval_seconds']
        min_nz_str = format_duration(min_nz) if min_nz else "N/A"
        when = stats.get('max_concurrent_timestamp', 'N/A')
        if when and len(when) > 19:
            when = when[:19]
        print(f"{bot_name:<25} {stats['total_requests']:>10,} {stats['unique_ips']:>5} "
              f"{format_duration(stats['avg_interval_seconds']):>14} "
              f"{min_nz_str:>14} "
              f"{stats['max_concurrent_requests']:>8} "
              f"{when:>20}")

    # Top by volume
    print(f"\n### TOP 20 BY TOTAL REQUESTS ###")
    print(f"{'Bot Name':<25} {'Requests':>12} {'Duration':>14} {'Avg RPM':>12} {'MaxConc':>8}")
    print("-" * 80)

    sorted_by_volume = sorted(
        bot_stats.items(),
        key=lambda x: x[1]['total_requests'],
        reverse=True
    )[:20]

    for bot_name, stats in sorted_by_volume:
        print(f"{bot_name:<25} {stats['total_requests']:>12,} "
              f"{format_duration(stats['total_duration_seconds']):>14} "
              f"{stats['requests_per_minute']:>12.1f} "
              f"{stats['max_concurrent_requests']:>8}")

    # Export data
    print(f"\n### EXPORTING DATA ###")

    def sanitize_for_json(obj):
        if isinstance(obj, dict):
            return {k: sanitize_for_json(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [sanitize_for_json(v) for v in obj]
        elif isinstance(obj, float) and (obj == float('inf') or obj == float('-inf')):
            return None
        elif isinstance(obj, set):
            return list(obj)
        return obj

    export_data = {
        'metadata': {
            'source_file': input_file,
            'total_bot_types': len(bot_stats),
            'generated_at': datetime.now().isoformat()
        },
        'bot_stats': sanitize_for_json(bot_stats)
    }

    with open(output_file, 'w') as f:
        json.dump(export_data, f, indent=2)

    print(f"Speed analysis exported to: {output_file}")

    print("\n" + "=" * 110)
    print("END OF REPORT")
    print("=" * 110)

if __name__ == '__main__':
    input_file = sys.argv[1] if len(sys.argv) > 1 else 'bot_paths.json'
    output_file = sys.argv[2] if len(sys.argv) > 2 else 'bot_speed_analysis.json'

    analyze_bot_speeds(input_file, output_file)
