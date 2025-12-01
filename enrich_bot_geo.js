#!/usr/bin/env node
/**
 * Enrich bot_summary.json with geographic data for each bot's IPs
 * Uses fast-geoip to lookup IP locations and calculates country distribution
 */

const fs = require('fs');
const path = require('path');

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

async function main() {
    const geoip = require('fast-geoip');

    const inputFile = process.argv[2] || 'bot_summary.json';
    const outputFile = process.argv[3] || 'bot_summary_geo.json';

    console.log(`Loading ${inputFile}...`);

    const data = JSON.parse(fs.readFileSync(inputFile, 'utf8'));
    const botSummary = data.bot_summary;

    console.log(`Found ${Object.keys(botSummary).length} bot types to process...\n`);

    let totalIPs = 0;
    let processedIPs = 0;
    let failedLookups = 0;

    // Count total IPs
    for (const botName of Object.keys(botSummary)) {
        totalIPs += botSummary[botName].ips.length;
    }

    console.log(`Total IPs to lookup: ${totalIPs.toLocaleString()}\n`);

    // Process each bot
    for (const botName of Object.keys(botSummary)) {
        const bot = botSummary[botName];
        const ips = bot.ips;

        // Country counts for this bot
        const countryCounts = {};
        const regionCounts = {};
        const cityCounts = {};
        const timezoneCounts = {};

        // Lookup each IP
        for (const ip of ips) {
            processedIPs++;

            try {
                const geo = await geoip.lookup(ip);

                if (geo) {
                    // Count country
                    const country = geo.country || 'Unknown';
                    countryCounts[country] = (countryCounts[country] || 0) + 1;

                    // Count region (country + region)
                    if (geo.region) {
                        const region = `${country}-${geo.region}`;
                        regionCounts[region] = (regionCounts[region] || 0) + 1;
                    }

                    // Count city
                    if (geo.city) {
                        const city = `${geo.city}, ${country}`;
                        cityCounts[city] = (cityCounts[city] || 0) + 1;
                    }

                    // Count timezone
                    if (geo.timezone) {
                        timezoneCounts[geo.timezone] = (timezoneCounts[geo.timezone] || 0) + 1;
                    }
                } else {
                    countryCounts['Unknown'] = (countryCounts['Unknown'] || 0) + 1;
                    failedLookups++;
                }
            } catch (err) {
                countryCounts['Unknown'] = (countryCounts['Unknown'] || 0) + 1;
                failedLookups++;
            }
        }

        // Calculate percentages for countries
        const totalForBot = ips.length;
        const countryPercentages = {};

        for (const [countryCode, count] of Object.entries(countryCounts)) {
            countryPercentages[countryCode] = {
                code: countryCode,
                name: getCountryName(countryCode),
                count: count,
                percentage: Math.round((count / totalForBot) * 10000) / 100  // 2 decimal places
            };
        }

        // Sort by count descending
        const sortedCountries = Object.entries(countryPercentages)
            .sort((a, b) => b[1].count - a[1].count)
            .reduce((obj, [key, val]) => {
                obj[key] = val;
                return obj;
            }, {});

        // Sort cities by count (top 10)
        const sortedCities = Object.entries(cityCounts)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 10)
            .reduce((obj, [key, val]) => {
                obj[key] = val;
                return obj;
            }, {});

        // Add geo data to bot
        bot.geo = {
            countries: sortedCountries,
            top_cities: sortedCities,
            timezones: timezoneCounts
        };

        // Progress update
        if (processedIPs % 1000 === 0 || processedIPs === totalIPs) {
            process.stdout.write(`\rProcessed ${processedIPs.toLocaleString()} / ${totalIPs.toLocaleString()} IPs (${Math.round(processedIPs/totalIPs*100)}%)`);
        }
    }

    console.log(`\n\nLookup complete. Failed lookups: ${failedLookups.toLocaleString()}`);

    // Update metadata
    data.metadata.geo_enriched_at = new Date().toISOString();
    data.metadata.total_ips_processed = totalIPs;
    data.metadata.failed_geo_lookups = failedLookups;

    // Write output
    console.log(`\nWriting ${outputFile}...`);
    fs.writeFileSync(outputFile, JSON.stringify(data, null, 2));

    const fileSize = fs.statSync(outputFile).size / (1024 * 1024);
    console.log(`Done! Output file size: ${fileSize.toFixed(2)} MB`);

    // Print summary of top countries across all bots
    console.log('\n' + '='.repeat(60));
    console.log('TOP COUNTRIES BY BOT TYPE');
    console.log('='.repeat(60));

    const sortedBots = Object.entries(botSummary)
        .sort((a, b) => b[1].count - a[1].count)
        .slice(0, 20);

    for (const [botName, bot] of sortedBots) {
        const topCountries = Object.entries(bot.geo.countries)
            .slice(0, 3)
            .map(([code, data]) => `${data.name}:${data.percentage}%`)
            .join(', ');

        console.log(`${botName.substring(0, 25).padEnd(25)} | ${topCountries}`);
    }
}

main().catch(err => {
    console.error('Error:', err);
    process.exit(1);
});
