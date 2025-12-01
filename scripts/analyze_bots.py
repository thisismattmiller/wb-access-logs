#!/usr/bin/env python3
"""
Bot Activity Analyzer
Analyzes nginx access logs to identify and track bot behavior.
Outputs chronological paths for each bot for later visualization.
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

# Known browser identifiers (if present WITHOUT bot indicators, it's likely a browser)
BROWSER_INDICATORS = [
    'mozilla', 'chrome', 'safari', 'firefox', 'edge', 'opera', 'brave'
]

# Known bot patterns - ORDER MATTERS! More specific patterns should come before generic ones
BOT_PATTERNS = [
    # Search engine bots
    (r'googlebot', 'Googlebot'),
    (r'adsbot-google', 'Google AdsBot'),
    (r'bingbot', 'Bingbot'),
    (r'yandexbot', 'YandexBot'),
    (r'baiduspider', 'Baiduspider'),
    (r'duckduckbot', 'DuckDuckBot'),
    (r'duckassistbot', 'DuckDuckGo Assistant'),
    (r'slurp', 'Yahoo Slurp'),
    (r'sogou', 'Sogou Spider'),
    (r'exabot', 'Exabot'),
    (r'qwantbot', 'Qwant Bot'),
    (r'mojeekbot', 'Mojeek Bot'),
    (r'yodaobot', 'Yodao Bot'),
    (r'yisou', 'Yisou Spider'),

    # Social media / messaging bots
    (r'facebot', 'Facebook Bot'),
    (r'facebookexternalhit', 'Facebook External Hit'),
    (r'meta-externalagent', 'Meta External Agent'),
    (r'meta-webindexer', 'Meta Web Indexer'),
    (r'twitterbot', 'Twitter Bot'),
    (r'linkedinbot', 'LinkedIn Bot'),
    (r'slackbot', 'Slackbot'),
    (r'telegrambot', 'Telegram Bot'),
    (r'whatsapp', 'WhatsApp'),
    (r'discordbot', 'Discord Bot'),
    (r'pinterest', 'Pinterest Bot'),
    (r'tiktokspider', 'TikTok Spider'),

    # SEO / Analytics bots
    (r'ia_archiver', 'Alexa Crawler'),
    (r'mj12bot', 'Majestic Bot'),
    (r'ahrefsbot', 'Ahrefs Bot'),
    (r'semrushbot', 'SEMrush Bot'),
    (r'dotbot', 'Moz DotBot'),
    (r'rogerbot', 'Moz RogerBot'),
    (r'screaming frog', 'Screaming Frog'),
    (r'megaindex', 'MegaIndex Bot'),
    (r'blexbot', 'BLEXBot'),
    (r'linkdexbot', 'Linkdex Bot'),
    (r'gigabot', 'Gigabot'),
    (r'seznambot', 'Seznam Bot'),
    (r'petalbot', 'PetalBot'),
    (r'applebot', 'Applebot'),
    (r'dataforseobot', 'DataForSEO Bot'),
    (r'surdotlybot', 'Surdotly Bot'),
    (r'awariobot', 'Awario Bot'),
    (r'bitsightbot', 'BitSight Bot'),
    (r'semanticscholar', 'Semantic Scholar Bot'),

    # AI/LLM bots
    (r'gptbot', 'GPTBot'),
    (r'chatgpt', 'ChatGPT'),
    (r'claudebot', 'ClaudeBot'),
    (r'anthropic', 'Anthropic Bot'),
    (r'ccbot', 'Common Crawl'),
    (r'cohere-ai', 'Cohere AI'),
    (r'perplexitybot', 'Perplexity Bot'),
    (r'bytespider', 'ByteSpider'),

    # Archive bots
    (r'archive\.org_bot', 'Internet Archive'),
    (r'wayback', 'Wayback Machine'),
    (r'intelx\.io_bot', 'IntelX Archive'),

    # Specific named crawlers (before generic patterns)
    (r'genomecrawler', 'Nokia Genome Crawler'),
    (r'barkrowler', 'Babbar Barkrowler'),
    (r'ev-crawler', 'Headline EV Crawler'),
    (r'proximic', 'Comscore Proximic'),
    (r'websuse', 'Websuse Crawler'),
    (r'semantic-visions', 'Semantic Visions Crawler'),
    (r'msiecrawler', 'MSIE Crawler'),
    (r'linkupbot', 'Linkup Bot'),
    (r'brightbot', 'Brightbot'),
    (r'monsido', 'Monsido Bot'),
    (r'thinkbot', 'Thinkbot'),
    (r'veryhip', 'VeryHip Bot'),
    (r'orbbot', 'Orbbot'),
    (r'iboubot', 'Ibou Bot'),
    (r'makemerry', 'MakeMerry Bot'),
    (r'opengraphbot', 'OpenGraph Bot'),
    (r'tinyurl', 'TinyURL Bot'),
    (r'backlinkspider', 'Backlink Spider'),
    (r'statusnest', 'StatusNest Spider'),
    (r'everyfeed', 'Everyfeed Spider'),
    (r'loli_spider', 'Loli Spider'),
    (r'addbot', 'Addshore Addbot'),
    (r'aliyunsecbot', 'Aliyun Security Bot'),
    (r'flyrbot', 'Flyr Bot'),

    # Specific tools and clients
    (r'drupal', 'Drupal'),
    (r'feedburner', 'FeedBurner'),
    (r'hatena', 'Hatena'),
    (r'instapaper', 'Instapaper'),
    (r'feedly', 'Feedly'),
    (r'newsblur', 'NewsBlur'),
    (r'apache-jena', 'Apache Jena'),
    (r'guzzlehttp', 'GuzzleHttp'),
    (r'dalvik', 'Android Dalvik'),
    (r'cfnetwork', 'CFNetwork Client'),
    (r'anyconnect', 'Cisco AnyConnect'),

    # Security scanners
    (r'nmap', 'Nmap'),
    (r'nikto', 'Nikto'),
    (r'sqlmap', 'SQLMap'),
    (r'masscan', 'Masscan'),
    (r'zgrab', 'ZGrab'),
    (r'censys', 'Censys'),
    (r'shodan', 'Shodan'),
    (r'security\.ipip\.net', 'IPIP Security Scanner'),
    (r'palo\s*alto', 'Palo Alto Scanner'),
    (r'fuzz faster u fool', 'FFUF Fuzzer'),

    # Monitoring and uptime
    (r'uptimerobot', 'UptimeRobot'),
    (r'pingdom', 'Pingdom'),
    (r'newrelic', 'New Relic'),
    (r'datadog', 'Datadog'),
    (r'site24x7', 'Site24x7'),
    (r'statuscake', 'StatusCake'),

    # Tools and libraries
    (r'^curl', 'curl'),
    (r'^wget', 'wget'),
    (r'python-requests', 'Python Requests'),
    (r'python-urllib', 'Python urllib'),
    (r'grequests', 'Python GRequests'),
    (r'python/', 'Python'),
    (r'java/', 'Java'),
    (r'go-http-client', 'Go HTTP Client'),
    (r'axios', 'Axios'),
    (r'node-fetch', 'Node Fetch'),
    (r'okhttp', 'OkHttp'),
    (r'apache-httpclient', 'Apache HttpClient'),
    (r'libwww-perl', 'Perl LWP'),
    (r'php/', 'PHP'),
    (r'ruby', 'Ruby'),
    (r'^httpclient', 'HTTPClient'),
    (r'^ahc/', 'Async HTTP Client'),
    (r'alittle client', 'ALittle Client'),

    # Generic bot patterns (MUST be last - catch-all)
    (r'bot[/\s\-_]', 'Generic Bot'),
    (r'crawler', 'Generic Crawler'),
    (r'spider', 'Generic Spider'),
    (r'scraper', 'Generic Scraper'),
    (r'fetcher', 'Generic Fetcher'),
]

def extract_urls_from_ua(user_agent):
    """Extract HTTP/HTTPS URLs from user agent string."""
    if not user_agent:
        return set()
    # Match http:// or https:// URLs
    url_pattern = r'https?://[^\s\)\]\"\'<>]+'
    urls = re.findall(url_pattern, user_agent, re.IGNORECASE)
    # Clean up URLs (remove trailing punctuation)
    cleaned = set()
    for url in urls:
        # Remove trailing punctuation that might have been captured
        url = url.rstrip('.,;:)')
        if url:
            cleaned.add(url)
    return cleaned

def is_bot(user_agent):
    """Determine if user agent is a bot and return bot name."""
    if not user_agent or user_agent == '-':
        return True, 'Empty User Agent'

    ua_lower = user_agent.lower()

    # Check against known bot patterns
    for pattern, name in BOT_PATTERNS:
        if re.search(pattern, ua_lower):
            return True, name

    # Check if it looks like a browser
    has_browser_indicator = any(ind in ua_lower for ind in BROWSER_INDICATORS)

    # If it has Mozilla but also has specific browser identifiers, it's likely a real browser
    if has_browser_indicator and 'mozilla/5.0' in ua_lower:
        # Additional check - real browsers usually have these
        if ('applewebkit' in ua_lower or 'gecko' in ua_lower or 'trident' in ua_lower):
            return False, None

    # If no browser indicators at all, likely a bot
    if not has_browser_indicator:
        return True, 'Unknown Non-Browser'

    return False, None

def parse_datetime(dt_str):
    """Parse nginx datetime format: 10/Oct/2025:00:00:12 -0400"""
    try:
        # Parse with timezone
        dt = datetime.strptime(dt_str, '%d/%b/%Y:%H:%M:%S %z')
        return dt
    except ValueError:
        try:
            # Try without timezone
            dt = datetime.strptime(dt_str.split()[0], '%d/%b/%Y:%H:%M:%S')
            return dt
        except ValueError:
            return None

def format_number(n):
    """Format number with thousands separators."""
    return f"{n:,}"

def analyze_bots(log_dir, output_file='bot_paths.json'):
    """Analyze all log files and track bot paths."""

    # Store bot activity: {bot_identifier: [list of access records]}
    # bot_identifier = f"{bot_name}|{ip}" to track individual bot instances
    bot_activity = defaultdict(list)
    bot_summary = defaultdict(lambda: {'count': 0, 'ips': set(), 'user_agents': set(), 'info_urls': set()})

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
    bot_requests = 0
    browser_requests = 0

    all_entries = []

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
                    user_agent = data['user_agent']

                    is_bot_ua, bot_name = is_bot(user_agent)

                    if is_bot_ua:
                        bot_requests += 1

                        dt = parse_datetime(data['datetime'])
                        if not dt:
                            continue

                        ip = data['ip']
                        bot_identifier = f"{bot_name}|{ip}"

                        # Create access record
                        record = {
                            'timestamp': dt.isoformat(),
                            'url': data['url'],
                            'method': data['method'],
                            'status': data['status'],
                            'ip': ip,
                            'user_agent': user_agent,
                            'referer': data['referer']
                        }

                        all_entries.append((dt, bot_identifier, bot_name, record))

                        # Update summary
                        bot_summary[bot_name]['count'] += 1
                        bot_summary[bot_name]['ips'].add(ip)
                        bot_summary[bot_name]['user_agents'].add(user_agent)
                        # Extract info URLs from user agent
                        info_urls = extract_urls_from_ua(user_agent)
                        bot_summary[bot_name]['info_urls'].update(info_urls)
                    else:
                        browser_requests += 1

        except Exception as e:
            print(f"  Error processing {log_file.name}: {e}")

    print(f"\nSorting {len(all_entries)} bot entries chronologically...")

    # Sort all entries by timestamp
    all_entries.sort(key=lambda x: x[0])

    # Build bot_activity from sorted entries
    for dt, bot_identifier, bot_name, record in all_entries:
        bot_activity[bot_identifier].append(record)

    # Print summary report
    print("\n" + "=" * 80)
    print("BOT ACTIVITY ANALYSIS REPORT")
    print("=" * 80)

    print(f"\n### OVERVIEW ###")
    print(f"Total Requests Analyzed: {format_number(total_lines)}")
    print(f"Bot Requests: {format_number(bot_requests)} ({bot_requests/total_lines*100:.1f}%)")
    print(f"Browser Requests: {format_number(browser_requests)} ({browser_requests/total_lines*100:.1f}%)")
    print(f"Unique Bot Types: {len(bot_summary)}")
    print(f"Unique Bot Instances (bot+IP): {len(bot_activity)}")

    print(f"\n### BOT TYPE SUMMARY (sorted by request count) ###")
    print(f"{'Bot Name':<30} {'Requests':>12} {'Unique IPs':>12} {'Unique UAs':>10}")
    print("-" * 70)

    for bot_name, stats in sorted(bot_summary.items(), key=lambda x: x[1]['count'], reverse=True):
        print(f"{bot_name:<30} {format_number(stats['count']):>12} {len(stats['ips']):>12} {len(stats['user_agents']):>10}")

    # Top bot instances by activity
    print(f"\n### TOP 30 MOST ACTIVE BOT INSTANCES ###")
    print(f"{'Bot Instance':<50} {'Requests':>10}")
    print("-" * 65)

    top_instances = sorted(bot_activity.items(), key=lambda x: len(x[1]), reverse=True)[:30]
    for bot_id, records in top_instances:
        bot_name, ip = bot_id.split('|', 1)
        display_name = f"{bot_name} ({ip})"
        if len(display_name) > 48:
            display_name = display_name[:45] + "..."
        print(f"{display_name:<50} {format_number(len(records)):>10}")

    # Sample paths for top bots
    print(f"\n### SAMPLE PATHS FOR TOP 5 BOT INSTANCES ###")
    for bot_id, records in top_instances[:5]:
        bot_name, ip = bot_id.split('|', 1)
        print(f"\n--- {bot_name} ({ip}) - {len(records)} total requests ---")
        print(f"First seen: {records[0]['timestamp']}")
        print(f"Last seen: {records[-1]['timestamp']}")
        print("First 10 URLs visited:")
        for i, rec in enumerate(records[:10]):
            print(f"  {i+1}. [{rec['status']}] {rec['method']} {rec['url'][:70]}")

    # Export data for visualization
    print(f"\n### EXPORTING DATA ###")

    # Convert sets to lists for JSON serialization
    summary_export = {}
    for bot_name, stats in bot_summary.items():
        summary_export[bot_name] = {
            'count': stats['count'],
            'ips': list(stats['ips']),
            'user_agents': list(stats['user_agents']),
            'info_urls': list(stats['info_urls'])
        }

    export_data = {
        'metadata': {
            'total_requests': total_lines,
            'bot_requests': bot_requests,
            'browser_requests': browser_requests,
            'unique_bot_types': len(bot_summary),
            'unique_bot_instances': len(bot_activity),
            'generated_at': datetime.now().isoformat()
        },
        'bot_summary': summary_export,
        'bot_paths': dict(bot_activity)
    }

    with open(output_file, 'w') as f:
        json.dump(export_data, f, indent=2)

    print(f"Full bot path data exported to: {output_file}")
    print(f"File size: {os.path.getsize(output_file) / (1024*1024):.2f} MB")

    # Also export a smaller summary file
    output_dir = os.path.dirname(output_file)
    summary_file = os.path.join(output_dir, 'bot_summary.json') if output_dir else 'bot_summary.json'
    summary_only = {
        'metadata': export_data['metadata'],
        'bot_summary': summary_export,
        'top_instances': {
            bot_id: {
                'request_count': len(records),
                'first_seen': records[0]['timestamp'],
                'last_seen': records[-1]['timestamp'],
                'sample_urls': [r['url'] for r in records[:100]]
            }
            for bot_id, records in top_instances[:50]
        }
    }

    with open(summary_file, 'w') as f:
        json.dump(summary_only, f, indent=2)

    print(f"Summary data exported to: {summary_file}")

    print("\n" + "=" * 80)
    print("END OF REPORT")
    print("=" * 80)

if __name__ == '__main__':
    # Default paths relative to scripts/ directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    default_log_dir = os.path.join(script_dir, '..', 'access_logs')
    default_output = os.path.join(script_dir, '..', 'data', 'bot_paths.json')

    log_directory = sys.argv[1] if len(sys.argv) > 1 else default_log_dir
    output_file = sys.argv[2] if len(sys.argv) > 2 else default_output

    if not os.path.isdir(log_directory):
        print(f"Error: Directory '{log_directory}' not found")
        sys.exit(1)

    analyze_bots(log_directory, output_file)
