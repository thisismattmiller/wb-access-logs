#!/usr/bin/env python3
"""
Nginx Access Log Analyzer
Analyzes access log files and generates a report with:
- Hits per day
- Total requests
- User agent statistics
- HTTP status code distribution
- Top requested URLs
- Top IP addresses
"""

import re
import os
import sys
from collections import Counter, defaultdict
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

def parse_log_line(line):
    """Parse a single log line and return a dict of fields."""
    match = LOG_PATTERN.match(line)
    if match:
        return match.groupdict()
    return None

def parse_datetime(dt_str):
    """Parse nginx datetime format: 10/Oct/2025:00:00:12 -0400"""
    try:
        return datetime.strptime(dt_str.split()[0], '%d/%b/%Y:%H:%M:%S')
    except ValueError:
        return None

def get_browser_name(user_agent):
    """Extract simplified browser name from user agent."""
    ua_lower = user_agent.lower()

    # Check for bots first
    if 'bot' in ua_lower or 'crawler' in ua_lower or 'spider' in ua_lower:
        if 'googlebot' in ua_lower:
            return 'Googlebot'
        elif 'bingbot' in ua_lower:
            return 'Bingbot'
        elif 'yandex' in ua_lower:
            return 'YandexBot'
        elif 'baidu' in ua_lower:
            return 'Baiduspider'
        else:
            return 'Other Bot'

    # Check browsers
    if 'chrome' in ua_lower and 'edg' in ua_lower:
        return 'Edge'
    elif 'chrome' in ua_lower and 'brave' in ua_lower:
        return 'Brave'
    elif 'chrome' in ua_lower and 'opr' in ua_lower:
        return 'Opera'
    elif 'chrome' in ua_lower:
        return 'Chrome'
    elif 'firefox' in ua_lower:
        return 'Firefox'
    elif 'safari' in ua_lower and 'chrome' not in ua_lower:
        return 'Safari'
    elif 'msie' in ua_lower or 'trident' in ua_lower:
        return 'Internet Explorer'
    elif 'curl' in ua_lower:
        return 'curl'
    elif 'wget' in ua_lower:
        return 'wget'
    elif 'python' in ua_lower:
        return 'Python'
    elif user_agent == '-' or not user_agent:
        return 'Empty/None'
    else:
        return 'Other'

def format_number(n):
    """Format number with thousands separators."""
    return f"{n:,}"

def format_bytes(b):
    """Format bytes into human readable format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if b < 1024:
            return f"{b:.2f} {unit}"
        b /= 1024
    return f"{b:.2f} PB"

def analyze_logs(log_dir):
    """Analyze all log files in the directory."""
    # Counters
    total_requests = 0
    hits_per_day = Counter()
    status_codes = Counter()
    user_agents = Counter()
    browsers = Counter()
    top_urls = Counter()
    top_ips = Counter()
    methods = Counter()
    total_bytes = 0
    bytes_per_day = defaultdict(int)

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
        file_size = log_file.stat().st_size
        print(f"Processing {log_file.name} ({format_bytes(file_size)})...")

        try:
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    parsed = parse_log_line(line.strip())
                    if not parsed:
                        continue

                    total_requests += 1

                    # Extract date
                    dt = parse_datetime(parsed['datetime'])
                    if dt:
                        date_str = dt.strftime('%Y-%m-%d')
                        hits_per_day[date_str] += 1

                        # Track bytes per day
                        size = parsed['size']
                        if size != '-':
                            bytes_per_day[date_str] += int(size)

                    # Status codes
                    status_codes[parsed['status']] += 1

                    # User agents (full)
                    user_agents[parsed['user_agent']] += 1

                    # Browsers (simplified)
                    browser = get_browser_name(parsed['user_agent'])
                    browsers[browser] += 1

                    # URLs
                    top_urls[parsed['url']] += 1

                    # IPs
                    top_ips[parsed['ip']] += 1

                    # Methods
                    methods[parsed['method']] += 1

                    # Total bytes
                    size = parsed['size']
                    if size != '-':
                        total_bytes += int(size)
        except Exception as e:
            print(f"  Error processing {log_file.name}: {e}")

    # Print report
    print("\n" + "=" * 80)
    print("NGINX ACCESS LOG ANALYSIS REPORT")
    print("=" * 80)

    # Summary
    print("\n### SUMMARY ###")
    print(f"Total Requests: {format_number(total_requests)}")
    print(f"Total Data Transferred: {format_bytes(total_bytes)}")
    print(f"Date Range: {min(hits_per_day.keys())} to {max(hits_per_day.keys())}")
    print(f"Total Days: {len(hits_per_day)}")
    print(f"Average Requests/Day: {format_number(total_requests // len(hits_per_day) if hits_per_day else 0)}")

    # Hits per day
    print("\n### HITS PER DAY ###")
    for date in sorted(hits_per_day.keys()):
        hits = hits_per_day[date]
        bytes_day = bytes_per_day[date]
        bar = '█' * min(50, hits // 50000)
        print(f"{date}: {format_number(hits):>12} requests  {format_bytes(bytes_day):>12}  {bar}")

    # HTTP Status Codes
    print("\n### HTTP STATUS CODES ###")
    for status, count in status_codes.most_common():
        pct = (count / total_requests) * 100
        print(f"  {status}: {format_number(count):>12} ({pct:>5.1f}%)")

    # HTTP Methods
    print("\n### HTTP METHODS ###")
    for method, count in methods.most_common():
        pct = (count / total_requests) * 100
        print(f"  {method}: {format_number(count):>12} ({pct:>5.1f}%)")

    # Browser Statistics
    print("\n### BROWSER STATISTICS ###")
    for browser, count in browsers.most_common(15):
        pct = (count / total_requests) * 100
        print(f"  {browser:<20}: {format_number(count):>12} ({pct:>5.1f}%)")

    # Top URLs
    print("\n### TOP 20 REQUESTED URLS ###")
    for url, count in top_urls.most_common(20):
        pct = (count / total_requests) * 100
        url_display = url[:70] + '...' if len(url) > 70 else url
        print(f"  {format_number(count):>10} ({pct:>5.2f}%): {url_display}")

    # Top IPs
    print("\n### TOP 20 IP ADDRESSES ###")
    for ip, count in top_ips.most_common(20):
        pct = (count / total_requests) * 100
        print(f"  {ip:<18}: {format_number(count):>10} ({pct:>5.2f}%)")

    # Top User Agents (full)
    print("\n### TOP 20 USER AGENTS ###")
    for ua, count in user_agents.most_common(20):
        pct = (count / total_requests) * 100
        ua_display = ua[:80] + '...' if len(ua) > 80 else ua
        print(f"  {format_number(count):>10} ({pct:>5.2f}%): {ua_display}")

    print("\n" + "=" * 80)
    print("END OF REPORT")
    print("=" * 80)

if __name__ == '__main__':
    # Default paths relative to scripts/ directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    default_log_dir = os.path.join(script_dir, '..', 'access_logs')

    log_directory = sys.argv[1] if len(sys.argv) > 1 else default_log_dir

    if not os.path.isdir(log_directory):
        print(f"Error: Directory '{log_directory}' not found")
        sys.exit(1)

    analyze_logs(log_directory)
