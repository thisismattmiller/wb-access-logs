#!/usr/bin/env node
/**
 * Traffic Analysis with Geographic Data
 * Analyzes nginx access logs to generate traffic per minute data with country breakdown.
 * Uses fast-geoip to lookup IP locations.
 */

const fs = require('fs');
const path = require('path');
const readline = require('readline');

// ISO 3166-1 alpha-2 country code to full name mapping
const COUNTRY_NAMES = {
    'AF': 'Afghanistan', 'AL': 'Albania', 'DZ': 'Algeria', 'AS': 'American Samoa', 'AD': 'Andorra',
    'AO': 'Angola', 'AI': 'Anguilla', 'AQ': 'Antarctica', 'AG': 'Antigua and Barbuda', 'AR': 'Argentina',
    'AM': 'Armenia', 'AW': 'Aruba', 'AU': 'Australia', 'AT': 'Austria', 'AZ': 'Azerbaijan',
    'BS': 'Bahamas', 'BH': 'Bahrain', 'BD': 'Bangladesh', 'BB': 'Barbados', 'BY': 'Belarus',
    'BE': 'Belgium', 'BZ': 'Belize', 'BJ': 'Benin', 'BM': 'Bermuda', 'BT': 'Bhutan',
    'BO': 'Bolivia', 'BA': 'Bosnia and Herzegovina', 'BW': 'Botswana', 'BR': 'Brazil', 'BN': 'Brunei',
    'BG': 'Bulgaria', 'BF': 'Burkina Faso', 'BI': 'Burundi', 'KH': 'Cambodia', 'CM': 'Cameroon',
    'CA': 'Canada', 'CV': 'Cape Verde', 'KY': 'Cayman Islands', 'CF': 'Central African Republic', 'TD': 'Chad',
    'CL': 'Chile', 'CN': 'China', 'CO': 'Colombia', 'KM': 'Comoros', 'CG': 'Congo',
    'CD': 'Congo (DRC)', 'CR': 'Costa Rica', 'CI': 'Ivory Coast', 'HR': 'Croatia', 'CU': 'Cuba',
    'CY': 'Cyprus', 'CZ': 'Czech Republic', 'DK': 'Denmark', 'DJ': 'Djibouti', 'DM': 'Dominica',
    'DO': 'Dominican Republic', 'EC': 'Ecuador', 'EG': 'Egypt', 'SV': 'El Salvador', 'GQ': 'Equatorial Guinea',
    'ER': 'Eritrea', 'EE': 'Estonia', 'ET': 'Ethiopia', 'FJ': 'Fiji', 'FI': 'Finland',
    'FR': 'France', 'GA': 'Gabon', 'GM': 'Gambia', 'GE': 'Georgia', 'DE': 'Germany',
    'GH': 'Ghana', 'GR': 'Greece', 'GD': 'Grenada', 'GU': 'Guam', 'GT': 'Guatemala',
    'GN': 'Guinea', 'GW': 'Guinea-Bissau', 'GY': 'Guyana', 'HT': 'Haiti', 'HN': 'Honduras',
    'HK': 'Hong Kong', 'HU': 'Hungary', 'IS': 'Iceland', 'IN': 'India', 'ID': 'Indonesia',
    'IR': 'Iran', 'IQ': 'Iraq', 'IE': 'Ireland', 'IL': 'Israel', 'IT': 'Italy',
    'JM': 'Jamaica', 'JP': 'Japan', 'JO': 'Jordan', 'KZ': 'Kazakhstan', 'KE': 'Kenya',
    'KI': 'Kiribati', 'KP': 'North Korea', 'KR': 'South Korea', 'KW': 'Kuwait', 'KG': 'Kyrgyzstan',
    'LA': 'Laos', 'LV': 'Latvia', 'LB': 'Lebanon', 'LS': 'Lesotho', 'LR': 'Liberia',
    'LY': 'Libya', 'LI': 'Liechtenstein', 'LT': 'Lithuania', 'LU': 'Luxembourg', 'MO': 'Macau',
    'MK': 'North Macedonia', 'MG': 'Madagascar', 'MW': 'Malawi', 'MY': 'Malaysia', 'MV': 'Maldives',
    'ML': 'Mali', 'MT': 'Malta', 'MH': 'Marshall Islands', 'MR': 'Mauritania', 'MU': 'Mauritius',
    'MX': 'Mexico', 'FM': 'Micronesia', 'MD': 'Moldova', 'MC': 'Monaco', 'MN': 'Mongolia',
    'ME': 'Montenegro', 'MA': 'Morocco', 'MZ': 'Mozambique', 'MM': 'Myanmar', 'NA': 'Namibia',
    'NR': 'Nauru', 'NP': 'Nepal', 'NL': 'Netherlands', 'NZ': 'New Zealand', 'NI': 'Nicaragua',
    'NE': 'Niger', 'NG': 'Nigeria', 'NO': 'Norway', 'OM': 'Oman', 'PK': 'Pakistan',
    'PW': 'Palau', 'PS': 'Palestine', 'PA': 'Panama', 'PG': 'Papua New Guinea', 'PY': 'Paraguay',
    'PE': 'Peru', 'PH': 'Philippines', 'PL': 'Poland', 'PT': 'Portugal', 'PR': 'Puerto Rico',
    'QA': 'Qatar', 'RO': 'Romania', 'RU': 'Russia', 'RW': 'Rwanda', 'KN': 'Saint Kitts and Nevis',
    'LC': 'Saint Lucia', 'VC': 'Saint Vincent and the Grenadines', 'WS': 'Samoa', 'SM': 'San Marino',
    'ST': 'Sao Tome and Principe', 'SA': 'Saudi Arabia', 'SN': 'Senegal', 'RS': 'Serbia', 'SC': 'Seychelles',
    'SL': 'Sierra Leone', 'SG': 'Singapore', 'SK': 'Slovakia', 'SI': 'Slovenia', 'SB': 'Solomon Islands',
    'SO': 'Somalia', 'ZA': 'South Africa', 'SS': 'South Sudan', 'ES': 'Spain', 'LK': 'Sri Lanka',
    'SD': 'Sudan', 'SR': 'Suriname', 'SZ': 'Eswatini', 'SE': 'Sweden', 'CH': 'Switzerland',
    'SY': 'Syria', 'TW': 'Taiwan', 'TJ': 'Tajikistan', 'TZ': 'Tanzania', 'TH': 'Thailand',
    'TL': 'Timor-Leste', 'TG': 'Togo', 'TO': 'Tonga', 'TT': 'Trinidad and Tobago', 'TN': 'Tunisia',
    'TR': 'Turkey', 'TM': 'Turkmenistan', 'TV': 'Tuvalu', 'UG': 'Uganda', 'UA': 'Ukraine',
    'AE': 'United Arab Emirates', 'GB': 'United Kingdom', 'US': 'United States', 'UY': 'Uruguay',
    'UZ': 'Uzbekistan', 'VU': 'Vanuatu', 'VA': 'Vatican City', 'VE': 'Venezuela', 'VN': 'Vietnam',
    'YE': 'Yemen', 'ZM': 'Zambia', 'ZW': 'Zimbabwe'
};

function getCountryName(code) {
    return COUNTRY_NAMES[code] || code;
}

// Nginx log pattern
const LOG_PATTERN = /^(\d+\.\d+\.\d+\.\d+)\s+-\s+-\s+\[([^\]]+)\]\s+"(\w+)\s+([^\s]+)\s+[^"]*"\s+(\d+)\s+(\d+|-)\s+"([^"]*)"\s+"([^"]*)"/;

// Parse nginx datetime: 10/Oct/2025:00:00:12 -0400
function parseDateTime(dtStr) {
    const months = {
        'Jan': 0, 'Feb': 1, 'Mar': 2, 'Apr': 3, 'May': 4, 'Jun': 5,
        'Jul': 6, 'Aug': 7, 'Sep': 8, 'Oct': 9, 'Nov': 10, 'Dec': 11
    };

    const match = dtStr.match(/(\d+)\/(\w+)\/(\d+):(\d+):(\d+):(\d+)\s+([+-]\d+)/);
    if (!match) return null;

    const [, day, monthStr, year, hour, minute, second, tz] = match;
    const month = months[monthStr];

    // Create date (ignore timezone for simplicity, treat as local)
    return new Date(year, month, day, hour, minute, 0, 0);
}

function truncateToMinute(date) {
    return new Date(date.getFullYear(), date.getMonth(), date.getDate(),
                    date.getHours(), date.getMinutes(), 0, 0);
}

function formatMinuteKey(date) {
    const pad = n => n.toString().padStart(2, '0');
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}:00`;
}

async function processLogFile(filePath, geoip, ipCache, minuteData, countryTotals, statusTotals) {
    return new Promise((resolve, reject) => {
        const fileStream = fs.createReadStream(filePath);
        const rl = readline.createInterface({
            input: fileStream,
            crlfDelay: Infinity
        });

        let lineCount = 0;
        let parsedCount = 0;

        rl.on('line', async (line) => {
            lineCount++;

            const match = line.match(LOG_PATTERN);
            if (!match) return;

            const [, ip, datetime, method, url, status, size] = match;

            const dt = parseDateTime(datetime);
            if (!dt) return;

            parsedCount++;

            const minuteKey = formatMinuteKey(truncateToMinute(dt));

            // Initialize minute data if needed
            if (!minuteData[minuteKey]) {
                minuteData[minuteKey] = {
                    requests: 0,
                    bytes: 0,
                    countries: {},
                    status_codes: {}
                };
            }

            // Count request
            minuteData[minuteKey].requests++;

            // Count bytes
            if (size !== '-') {
                minuteData[minuteKey].bytes += parseInt(size, 10);
            }

            // Count status code
            minuteData[minuteKey].status_codes[status] = (minuteData[minuteKey].status_codes[status] || 0) + 1;
            statusTotals[status] = (statusTotals[status] || 0) + 1;

            // Lookup country (use cache to avoid repeated lookups)
            let country = ipCache[ip];
            if (country === undefined) {
                try {
                    const geo = await geoip.lookup(ip);
                    country = geo ? geo.country : 'Unknown';
                } catch (e) {
                    country = 'Unknown';
                }
                ipCache[ip] = country;
            }

            // Count by country for this minute
            minuteData[minuteKey].countries[country] = (minuteData[minuteKey].countries[country] || 0) + 1;

            // Count total by country
            countryTotals[country] = (countryTotals[country] || 0) + 1;
        });

        rl.on('close', () => {
            resolve({ lineCount, parsedCount });
        });

        rl.on('error', reject);
    });
}

async function main() {
    const geoip = require('fast-geoip');

    // Default paths relative to scripts/ directory
    const scriptDir = path.dirname(require.main.filename);
    const defaultLogDir = path.join(scriptDir, '..', 'access_logs');
    const defaultOutput = path.join(scriptDir, '..', 'data', 'traffic_per_minute_geo.json');

    const logDir = process.argv[2] || defaultLogDir;
    const outputFile = process.argv[3] || defaultOutput;

    console.log(`Scanning ${logDir} for log files...`);

    // Get all log files
    const files = fs.readdirSync(logDir)
        .filter(f => f.startsWith('access.log'))
        .map(f => path.join(logDir, f))
        .sort();

    if (files.length === 0) {
        console.error(`No log files found in ${logDir}`);
        process.exit(1);
    }

    console.log(`Found ${files.length} log files to process...\n`);

    // Data structures
    const minuteData = {};      // minute -> { requests, bytes, countries, status_codes }
    const countryTotals = {};   // country -> total count
    const statusTotals = {};    // status -> total count
    const ipCache = {};         // ip -> country (cache)

    let totalLines = 0;
    let totalParsed = 0;

    // Process each file
    for (const file of files) {
        const fileName = path.basename(file);
        const fileSize = (fs.statSync(file).size / (1024 * 1024)).toFixed(1);
        process.stdout.write(`Processing ${fileName} (${fileSize} MB)...`);

        const { lineCount, parsedCount } = await processLogFile(file, geoip, ipCache, minuteData, countryTotals, statusTotals);

        totalLines += lineCount;
        totalParsed += parsedCount;

        console.log(` ${parsedCount.toLocaleString()} requests`);
    }

    console.log(`\nTotal: ${totalParsed.toLocaleString()} of ${totalLines.toLocaleString()} lines parsed`);
    console.log(`Unique IPs looked up: ${Object.keys(ipCache).length.toLocaleString()}`);

    // Sort minutes and build time series
    const sortedMinutes = Object.keys(minuteData).sort();

    if (sortedMinutes.length === 0) {
        console.error('No data found!');
        process.exit(1);
    }

    console.log(`Time range: ${sortedMinutes[0]} to ${sortedMinutes[sortedMinutes.length - 1]}`);
    console.log(`Total minutes: ${sortedMinutes.length.toLocaleString()}`);

    // Calculate statistics
    const requestCounts = sortedMinutes.map(m => minuteData[m].requests);
    const totalRequests = requestCounts.reduce((a, b) => a + b, 0);
    const avgRpm = totalRequests / requestCounts.length;
    const maxRpm = Math.max(...requestCounts);
    const minRpm = Math.min(...requestCounts);

    // Find peak minute
    let peakMinute = sortedMinutes[0];
    let peakRequests = 0;
    for (const minute of sortedMinutes) {
        if (minuteData[minute].requests > peakRequests) {
            peakRequests = minuteData[minute].requests;
            peakMinute = minute;
        }
    }

    console.log(`\nTraffic Statistics:`);
    console.log(`  Average requests/minute: ${avgRpm.toFixed(1)}`);
    console.log(`  Max requests/minute: ${maxRpm.toLocaleString()} (at ${peakMinute})`);
    console.log(`  Min requests/minute: ${minRpm.toLocaleString()}`);
    console.log(`  Total requests: ${totalRequests.toLocaleString()}`);

    // Build time series with country names
    const timeSeries = sortedMinutes.map(minute => {
        const data = minuteData[minute];

        // Convert country codes to include names
        const countriesWithNames = {};
        for (const [code, count] of Object.entries(data.countries)) {
            countriesWithNames[code] = {
                code: code,
                name: getCountryName(code),
                count: count
            };
        }

        return {
            timestamp: minute,
            requests: data.requests,
            bytes: data.bytes,
            countries: countriesWithNames,
            status_codes: data.status_codes
        };
    });

    // Build country totals with names and percentages
    const countryTotalsWithNames = {};
    for (const [code, count] of Object.entries(countryTotals)) {
        countryTotalsWithNames[code] = {
            code: code,
            name: getCountryName(code),
            count: count,
            percentage: Math.round((count / totalRequests) * 10000) / 100
        };
    }

    // Sort countries by count
    const sortedCountryTotals = Object.entries(countryTotalsWithNames)
        .sort((a, b) => b[1].count - a[1].count)
        .reduce((obj, [key, val]) => {
            obj[key] = val;
            return obj;
        }, {});

    // Build output
    const exportData = {
        metadata: {
            source_directory: logDir,
            total_lines: totalLines,
            parsed_lines: totalParsed,
            total_minutes: sortedMinutes.length,
            unique_ips: Object.keys(ipCache).length,
            start_time: sortedMinutes[0],
            end_time: sortedMinutes[sortedMinutes.length - 1],
            generated_at: new Date().toISOString()
        },
        statistics: {
            total_requests: totalRequests,
            avg_requests_per_minute: Math.round(avgRpm * 100) / 100,
            max_requests_per_minute: maxRpm,
            min_requests_per_minute: minRpm,
            peak_minute: peakMinute,
            peak_requests: peakRequests,
            status_code_totals: statusTotals,
            country_totals: sortedCountryTotals
        },
        time_series: timeSeries
    };

    // Write output
    console.log(`\nWriting ${outputFile}...`);
    fs.writeFileSync(outputFile, JSON.stringify(exportData, null, 2));

    const fileSize = (fs.statSync(outputFile).size / (1024 * 1024)).toFixed(2);
    console.log(`Done! Output file size: ${fileSize} MB`);

    // Print top countries
    console.log('\n' + '='.repeat(60));
    console.log('TOP 20 COUNTRIES BY REQUESTS');
    console.log('='.repeat(60));

    const topCountries = Object.entries(sortedCountryTotals).slice(0, 20);
    for (const [code, data] of topCountries) {
        console.log(`${data.name.padEnd(30)} ${data.count.toLocaleString().padStart(12)} (${data.percentage.toFixed(1)}%)`);
    }
}

main().catch(err => {
    console.error('Error:', err);
    process.exit(1);
});
