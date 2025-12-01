#!/usr/bin/env python3
"""
Analyze GPTBot URL patterns from access logs.
Categorizes URLs by type and generates statistics.
"""

import re
import json
import sys
from collections import defaultdict, Counter
from urllib.parse import urlparse, parse_qs, unquote
from datetime import datetime

def categorize_url(url):
    """Categorize a URL into a meaningful bucket."""
    parsed = urlparse(url)
    path = parsed.path
    query = parse_qs(parsed.query)

    # Handle /w/index.php with query params
    if path == '/w/index.php':
        title = unquote(query.get('title', [''])[0])

        if title.startswith('Special:WhatLinksHere'):
            target = title.replace('Special:WhatLinksHere/', '')
            if target.startswith('Item:Q'):
                return ('Special:WhatLinksHere', 'Item pages', target)
            elif target.startswith('Property:P'):
                return ('Special:WhatLinksHere', 'Property pages', target)
            else:
                return ('Special:WhatLinksHere', 'Other', target)
        elif title.startswith('Special:Log'):
            return ('Special:Log', 'Log pages', title)
        elif title.startswith('Special:UserLogin'):
            return ('Special:UserLogin', 'Login attempts', title)
        elif title.startswith('Special:Search'):
            return ('Special:Search', 'Search queries', title)
        elif title.startswith('Special:'):
            special_type = title.split('/')[0]
            return (special_type, 'Other special', title)
        elif title.startswith('Item:Q'):
            return ('Item pages', 'Direct item access', title)
        elif title.startswith('Property:P'):
            return ('Property pages', 'Direct property access', title)
        elif title.startswith('User:') or title.startswith('User_talk:'):
            return ('User pages', 'User/talk pages', title)
        elif title:
            return ('Other wiki pages', 'Via index.php', title)
        else:
            return ('Unknown', 'No title param', url)

    # Handle /wiki/ paths
    elif path.startswith('/wiki/'):
        page = unquote(path[6:])

        if page.startswith('Special:EntityData/'):
            entity_part = page.replace('Special:EntityData/', '')
            if '.' in entity_part:
                fmt = entity_part.split('.')[-1]
                entity_id = entity_part.rsplit('.', 1)[0]
                return ('Special:EntityData', f'Format: {fmt}', entity_id)
            else:
                return ('Special:EntityData', 'Default format', entity_part)
        elif page.startswith('Special:WhatLinksHere'):
            return ('Special:WhatLinksHere', 'Direct access', page)
        elif page.startswith('Special:NewItem'):
            return ('Special:NewItem', 'New item creation', page)
        elif page.startswith('Special:RecentChangesLinked'):
            return ('Special:RecentChangesLinked', 'Related changes', page)
        elif page.startswith('Special:'):
            special_type = page.split('/')[0]
            return (special_type, 'Wiki path', page)
        elif page.startswith('Item:Q'):
            return ('Item pages', 'Wiki path', page)
        elif page.startswith('Item_talk:Q'):
            return ('Item talk pages', 'Discussion', page)
        elif page.startswith('Property:P'):
            return ('Property pages', 'Wiki path', page)
        elif page.startswith('Property_talk:P'):
            return ('Property talk pages', 'Discussion', page)
        elif page.startswith('User:'):
            return ('User pages', 'User page', page)
        elif page.startswith('User_talk:'):
            return ('User pages', 'User talk', page)
        elif page.startswith('Project:'):
            return ('Project pages', 'Project namespace', page)
        elif page.startswith('MediaWiki'):
            return ('MediaWiki pages', 'System messages', page)
        else:
            return ('Other wiki pages', 'Wiki path', page)

    # Handle /entity/ paths (Wikidata-style)
    elif path.startswith('/entity/'):
        entity = path[8:]
        return ('Entity redirect', 'Linked data', entity)

    # Handle other paths
    elif path == '/':
        return ('Homepage', 'Root', '/')
    elif path.startswith('/static/') or path.startswith('/resources/'):
        return ('Static resources', 'Assets', path)
    else:
        return ('Other', 'Uncategorized', path)

def analyze_gptbot_log(log_file, output_file='gptbot_url_analysis.json'):
    """Analyze GPTBot access log and generate statistics."""

    # Counters
    category_counts = defaultdict(int)
    subcategory_counts = defaultdict(lambda: defaultdict(int))
    status_codes = Counter()
    bytes_by_category = defaultdict(int)
    hourly_distribution = defaultdict(int)
    unique_items = defaultdict(set)
    sample_urls = defaultdict(list)

    # Parse log pattern
    log_pattern = re.compile(
        r'(?P<ip>\d+\.\d+\.\d+\.\d+)\s+'
        r'-\s+-\s+'
        r'\[(?P<datetime>[^\]]+)\]\s+'
        r'"(?P<method>\w+)\s+(?P<url>[^\s]+)\s+[^"]*"\s+'
        r'(?P<status>\d+)\s+'
        r'(?P<size>\d+|-)'
    )

    total_requests = 0
    total_bytes = 0

    print(f"Analyzing {log_file}...")

    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            match = log_pattern.match(line.strip())
            if not match:
                continue

            total_requests += 1
            data = match.groupdict()

            url = data['url']
            status = data['status']
            size = int(data['size']) if data['size'] != '-' else 0

            # Parse datetime for hourly distribution
            try:
                dt = datetime.strptime(data['datetime'].split()[0], '%d/%b/%Y:%H:%M:%S')
                hourly_distribution[dt.hour] += 1
            except:
                pass

            # Categorize URL
            category, subcategory, detail = categorize_url(url)

            category_counts[category] += 1
            subcategory_counts[category][subcategory] += 1
            status_codes[status] += 1
            bytes_by_category[category] += size
            total_bytes += size

            # Track unique items for certain categories
            if category in ['Item pages', 'Property pages', 'Special:WhatLinksHere']:
                # Extract Q/P number
                match_id = re.search(r'[QP]\d+', detail)
                if match_id:
                    unique_items[category].add(match_id.group())

            # Keep sample URLs (max 5 per category)
            if len(sample_urls[category]) < 5:
                sample_urls[category].append(url)

            if total_requests % 100000 == 0:
                print(f"  Processed {total_requests:,} requests...")

    print(f"\nTotal requests analyzed: {total_requests:,}")
    print(f"Total bytes: {total_bytes / (1024*1024):.1f} MB")

    # Build output
    output = {
        'metadata': {
            'source_file': log_file,
            'total_requests': total_requests,
            'total_bytes': total_bytes,
            'analyzed_at': datetime.now().isoformat()
        },
        'summary': {
            'top_categories': sorted(
                [(cat, count) for cat, count in category_counts.items()],
                key=lambda x: x[1],
                reverse=True
            ),
            'status_codes': dict(status_codes.most_common()),
        },
        'categories': {},
        'hourly_distribution': dict(sorted(hourly_distribution.items())),
    }

    # Build detailed category info
    for category in sorted(category_counts.keys(), key=lambda x: category_counts[x], reverse=True):
        cat_data = {
            'total_requests': category_counts[category],
            'percentage': round(category_counts[category] / total_requests * 100, 2),
            'total_bytes': bytes_by_category[category],
            'avg_bytes_per_request': round(bytes_by_category[category] / category_counts[category]) if category_counts[category] > 0 else 0,
            'subcategories': dict(sorted(
                subcategory_counts[category].items(),
                key=lambda x: x[1],
                reverse=True
            )),
            'sample_urls': sample_urls[category],
        }

        if category in unique_items:
            cat_data['unique_entities'] = len(unique_items[category])
            cat_data['sample_entities'] = list(unique_items[category])[:20]

        output['categories'][category] = cat_data

    # Write output
    print(f"\nWriting {output_file}...")
    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2)

    # Print summary
    print("\n" + "=" * 60)
    print("URL CATEGORY BREAKDOWN")
    print("=" * 60)

    for category, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
        pct = count / total_requests * 100
        print(f"\n{category}: {count:,} ({pct:.1f}%)")
        for subcat, subcount in sorted(subcategory_counts[category].items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"    {subcat}: {subcount:,}")

    print("\n" + "=" * 60)
    print("STATUS CODES")
    print("=" * 60)
    for status, count in status_codes.most_common():
        print(f"  {status}: {count:,}")

    return output

if __name__ == '__main__':
    import os
    # Default paths relative to scripts/ directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    default_input = os.path.join(script_dir, '..', 'data', 'GPTBot_access_log')
    default_output = os.path.join(script_dir, '..', 'data', 'gptbot_url_analysis.json')

    log_file = sys.argv[1] if len(sys.argv) > 1 else default_input
    output_file = sys.argv[2] if len(sys.argv) > 2 else default_output

    analyze_gptbot_log(log_file, output_file)
