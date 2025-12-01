# wb-access-logs

Nginx access log analysis toolkit with visualizations for analyzing bot traffic, geographic distribution, and request patterns.

## Directory Structure

```
wb-access-logs/
├── scripts/           # Analysis scripts (Python & Node.js)
├── data/              # Generated JSON data files
├── viz/               # Vite visualization app (Chart.js)
├── table/             # Vue 3 data explorer app
├── access_logs/       # Symlink to raw nginx log files
├── index.html         # Main landing page
└── gptbot_analysis.html  # GPTBot URL analysis report
```

## Scripts

### Log Analyzers

| Script | Description | Output |
|--------|-------------|--------|
| [scripts/analyze_logs.py](scripts/analyze_logs.py) | General log analysis with hits per day, status codes, top URLs, IPs | Console report |
| [scripts/analyze_bots.py](scripts/analyze_bots.py) | Bot detection and path tracking with 100+ bot patterns | [data/bot_paths.json](data/), [data/bot_summary.json](data/) |
| [scripts/analyze_bot_speed.py](scripts/analyze_bot_speed.py) | Bot timing analysis - request rates, burst detection | [data/bot_speed_analysis.json](data/) |
| [scripts/analyze_traffic.py](scripts/analyze_traffic.py) | Traffic per minute with status codes | [data/traffic_per_minute.json](data/) |
| [scripts/analyze_bot_vs_browser.py](scripts/analyze_bot_vs_browser.py) | Bot vs browser traffic per minute | [data/bot_vs_browser.json](data/) |
| [scripts/analyze_gptbot_urls.py](scripts/analyze_gptbot_urls.py) | GPTBot URL pattern analysis | [data/gptbot_url_analysis.json](data/) |

### Enrichment & Processing

| Script | Description | Output |
|--------|-------------|--------|
| [scripts/analyze_traffic_geo.js](scripts/analyze_traffic_geo.js) | Traffic per minute with geo IP lookup | [data/traffic_per_minute_geo.json.gz](data/) |
| [scripts/enrich_bot_geo.js](scripts/enrich_bot_geo.js) | Add geographic data to bot summary | [data/bot_summary_geo.json](data/) |
| [scripts/slim_traffic_data.py](scripts/slim_traffic_data.py) | Compress traffic data for visualization | [data/traffic_slim.json](data/) |

## Data Files

| File | Description | Size |
|------|-------------|------|
| [data/bot_vs_browser.json](data/bot_vs_browser.json) | Bot/browser traffic per minute (compact) | ~300KB |
| [data/traffic_slim.json](data/traffic_slim.json) | Traffic by country per minute (compact) | ~850KB |
| [data/bot_summary_geo.json](data/bot_summary_geo.json) | All bots with geo data | ~1.3MB |
| [data/bot_speed_analysis.json](data/bot_speed_analysis.json) | Bot timing metrics | ~90KB |
| [data/gptbot_url_analysis.json](data/gptbot_url_analysis.json) | GPTBot URL categories | ~17KB |
| [data/GPTBot_access_log.gz](data/GPTBot_access_log.gz) | Raw GPTBot requests | ~7MB |
| [data/traffic_per_minute_geo.json.gz](data/traffic_per_minute_geo.json.gz) | Full traffic data with geo (compressed) | ~4MB |

## Visualizations

### viz/ - Chart Visualizations

Vite + TypeScript + Chart.js app with multiple visualizations accessible via URL parameters.

```bash
cd viz
npm install
npm run dev    # Development server
npm run build  # Build to viz/dist/
```

**Available visualizations:**
- `?viz=bot_vs_browser` - Bot vs browser traffic line chart
- `?viz=ip_location` - Traffic by country line chart

### table/ - Data Explorer

Vue 3 + TypeScript app for exploring bot summary data in a sortable table.

```bash
cd table
npm install
npm run dev    # Development server
npm run build  # Build to table/dist/
```

**Features:**
- Sortable by bot name or request count
- Search/filter by bot name
- Shows request counts, IP counts, user agent counts
- Top countries per bot
- Info URLs extracted from user agents

## Usage

### Running Scripts

All scripts can be run from the repo root directory:

```bash
# Analyze logs (requires access_logs/ symlink)
python3 scripts/analyze_logs.py

# Generate bot summary with geo
python3 scripts/analyze_bots.py
node scripts/enrich_bot_geo.js

# Generate traffic data
python3 scripts/analyze_traffic.py
node scripts/analyze_traffic_geo.js
python3 scripts/slim_traffic_data.py

# Bot vs browser analysis
python3 scripts/analyze_bot_vs_browser.py
```

### Deploying Visualizations

1. Build both apps:
```bash
cd viz && npm run build && cd ..
cd table && npm run build && cd ..
```

2. Copy data files to dist directories:
```bash
cp data/bot_vs_browser.json data/traffic_slim.json viz/dist/data/
cp data/bot_summary_geo.json table/dist/data/
```

3. Serve from repo root (all paths are relative for GitHub Pages compatibility)

## Requirements

### Python Scripts
- Python 3.8+
- No external dependencies (uses stdlib only)

### Node.js Scripts
- Node.js 18+
- `fast-geoip` package (install with `npm install` in `scripts/` directory)

### Visualization Apps
- Node.js 18+
- Dependencies installed via `npm install` in each app directory

## License

MIT
