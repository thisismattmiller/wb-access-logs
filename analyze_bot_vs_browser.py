#!/usr/bin/env python3
"""
Bot vs Browser Traffic Analysis
Analyzes nginx access logs to generate per-minute breakdown of bot vs browser traffic.
Outputs a slim JSON file suitable for histogram visualization.
"""

import re
import json
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

# Known browser identifiers
BROWSER_INDICATORS = [
    'mozilla', 'chrome', 'safari', 'firefox', 'edge', 'opera', 'brave'
]

# Bot patterns (simplified version for speed)
BOT_PATTERNS = [
    r'googlebot', r'bingbot', r'yandex', r'baidu', r'duckduck',
    r'facebot', r'facebook', r'twitter', r'linkedin', r'slack', r'discord', r'whatsapp',
    r'bot[/\s\-_]', r'crawler', r'spider', r'scraper', r'fetcher',
    r'curl', r'wget', r'python', r'java/', r'go-http', r'axios', r'node',
    r'ahrefsbot', r'semrush', r'mj12bot', r'dotbot', r'petalbot',
    r'gptbot', r'chatgpt', r'claude', r'anthropic', r'ccbot', r'bytespider',
    r'archive\.org', r'wayback',
    r'uptimerobot', r'pingdom', r'newrelic', r'datadog',
    r'nmap', r'nikto', r'sqlmap', r'zgrab', r'censys', r'shodan',
]

# Compile patterns for speed
BOT_REGEX = re.compile('|'.join(BOT_PATTERNS), re.IGNORECASE)

def is_bot(user_agent):
    """Quick check if user agent is a bot."""
    if not user_agent or user_agent == '-':
        return True  # Empty UA is likely a bot

    ua_lower = user_agent.lower()

    # Check for bot patterns
    if BOT_REGEX.search(ua_lower):
        return True

    # Check if it looks like a browser
    has_browser = any(ind in ua_lower for ind in BROWSER_INDICATORS)

    if has_browser and 'mozilla/5.0' in ua_lower:
        if 'applewebkit' in ua_lower or 'gecko' in ua_lower or 'trident' in ua_lower:
            return False

    # No browser indicators = likely bot
    if not has_browser:
        return True

    return False

def parse_datetime(dt_str):
    """Parse nginx datetime format to datetime object."""
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

def analyze_bot_vs_browser(log_dir, output_file='bot_vs_browser.json'):
    """Analyze logs and generate bot vs browser traffic data."""

    # Traffic counters per minute: {minute_str: {'bot': count, 'browser': count}}
    traffic_per_minute = defaultdict(lambda: {'bot': 0, 'browser': 0})

    # Totals
    total_bot = 0
    total_browser = 0
    total_lines = 0
    parsed_lines = 0

    # Get all log files
    log_path = Path(log_dir)
    log_files = sorted([f for f in log_path.iterdir()
                       if f.is_file() and f.name.startswith('access.log')])

    if not log_files:
        print(f"No log files found in {log_dir}")
        return

    print(f"Found {len(log_files)} log files to analyze...")
    print()

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
                    parsed_lines += 1

                    dt = parse_datetime(data['datetime'])
                    if not dt:
                        continue

                    minute_dt = truncate_to_minute(dt)
                    minute_str = minute_dt.strftime('%Y-%m-%dT%H:%M:00')

                    user_agent = data['user_agent']

                    if is_bot(user_agent):
                        traffic_per_minute[minute_str]['bot'] += 1
                        total_bot += 1
                    else:
                        traffic_per_minute[minute_str]['browser'] += 1
                        total_browser += 1

        except Exception as e:
            print(f"  Error processing {log_file.name}: {e}")

    print(f"\nProcessed {parsed_lines:,} of {total_lines:,} lines")
    print(f"Bot requests: {total_bot:,} ({total_bot/(total_bot+total_browser)*100:.1f}%)")
    print(f"Browser requests: {total_browser:,} ({total_browser/(total_bot+total_browser)*100:.1f}%)")

    # Sort by time
    sorted_minutes = sorted(traffic_per_minute.keys())

    if not sorted_minutes:
        print("No data found!")
        return

    print(f"Time range: {sorted_minutes[0]} to {sorted_minutes[-1]}")
    print(f"Total minutes: {len(sorted_minutes):,}")

    # Calculate start timestamp for offset encoding
    start_dt = datetime.fromisoformat(sorted_minutes[0])
    start_ts = int(start_dt.timestamp())

    # Build slim time series: [minute_offset, bot_count, browser_count]
    slim_series = []
    for minute_str in sorted_minutes:
        minute_dt = datetime.fromisoformat(minute_str)
        offset = (int(minute_dt.timestamp()) - start_ts) // 60

        data = traffic_per_minute[minute_str]
        slim_series.append([offset, data['bot'], data['browser']])

    # Calculate statistics
    bot_counts = [d['bot'] for d in traffic_per_minute.values()]
    browser_counts = [d['browser'] for d in traffic_per_minute.values()]

    max_bot_minute = max(traffic_per_minute.items(), key=lambda x: x[1]['bot'])
    max_browser_minute = max(traffic_per_minute.items(), key=lambda x: x[1]['browser'])

    # Build output
    output_data = {
        'm': {
            'start': start_ts,
            'minutes': len(sorted_minutes),
            'interval': 60
        },
        's': {
            'total_bot': total_bot,
            'total_browser': total_browser,
            'bot_pct': round(total_bot / (total_bot + total_browser) * 100, 2),
            'browser_pct': round(total_browser / (total_bot + total_browser) * 100, 2),
            'avg_bot_per_min': round(sum(bot_counts) / len(bot_counts), 2),
            'avg_browser_per_min': round(sum(browser_counts) / len(browser_counts), 2),
            'max_bot_per_min': max(bot_counts),
            'max_browser_per_min': max(browser_counts),
            'peak_bot_minute': max_bot_minute[0],
            'peak_browser_minute': max_browser_minute[0]
        },
        # Time series: [minute_offset, bot_count, browser_count]
        'd': slim_series
    }

    # Write compact JSON
    print(f"\nWriting {output_file}...")
    with open(output_file, 'w') as f:
        json.dump(output_data, f, separators=(',', ':'))

    file_size = Path(output_file).stat().st_size / 1024
    print(f"Output file size: {file_size:.1f} KB")

    # Also write debug version
    debug_file = output_file.replace('.json', '_debug.json')
    with open(debug_file, 'w') as f:
        json.dump(output_data, f, indent=2)
    print(f"Debug version: {debug_file}")

    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total requests: {total_bot + total_browser:,}")
    print(f"Bot traffic: {total_bot:,} ({output_data['s']['bot_pct']}%)")
    print(f"Browser traffic: {total_browser:,} ({output_data['s']['browser_pct']}%)")
    print(f"Peak bot minute: {max_bot_minute[0]} ({max_bot_minute[1]['bot']} requests)")
    print(f"Peak browser minute: {max_browser_minute[0]} ({max_browser_minute[1]['browser']} requests)")

    print("\n" + "=" * 60)
    print("DATA FORMAT")
    print("=" * 60)
    print("Time series: [minute_offset, bot_count, browser_count]")
    print(f"Sample: {slim_series[0]}, {slim_series[1]}, {slim_series[2]}...")

    print("""
JAVASCRIPT USAGE:
-----------------
const data = await fetch('bot_vs_browser.json').then(r => r.json());

// Get timestamp for index
const getTime = (i) => new Date((data.m.start + data.d[i][0] * 60) * 1000);

// Get bot count for index
const getBots = (i) => data.d[i][1];

// Get browser count for index
const getBrowsers = (i) => data.d[i][2];

// Get total for index
const getTotal = (i) => data.d[i][1] + data.d[i][2];
""")

if __name__ == '__main__':
    log_directory = sys.argv[1] if len(sys.argv) > 1 else 'access_logs'
    output_file = sys.argv[2] if len(sys.argv) > 2 else 'bot_vs_browser.json'

    analyze_bot_vs_browser(log_directory, output_file)
