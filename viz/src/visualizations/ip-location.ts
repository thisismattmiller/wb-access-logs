import { Chart, registerables } from 'chart.js';
import 'chartjs-adapter-date-fns';
import { format } from 'date-fns';

Chart.register(...registerables);

interface TrafficSlimData {
  m: {
    start: number;
    minutes: number;
    interval: number;
  };
  s: {
    total: number;
    avg: number;
    max: number;
    min: number;
    peak_offset: number;
  };
  countries: Record<string, string>;
  top: string[];
  country_totals: Record<string, number>;
  d: number[][]; // [minute_offset, requests, ...country_counts, other]
}

// Distinct colors for 10 countries + other
const COUNTRY_COLORS = [
  'rgba(59, 130, 246, 0.8)',   // blue - BR
  'rgba(239, 68, 68, 0.8)',    // red - VN
  'rgba(34, 197, 94, 0.8)',    // green - US
  'rgba(168, 85, 247, 0.8)',   // purple - CH
  'rgba(249, 115, 22, 0.8)',   // orange - AR
  'rgba(236, 72, 153, 0.8)',   // pink - SG
  'rgba(20, 184, 166, 0.8)',   // teal - EC
  'rgba(234, 179, 8, 0.8)',    // yellow - BD
  'rgba(99, 102, 241, 0.8)',   // indigo - IN
  'rgba(6, 182, 212, 0.8)',    // cyan - IQ
  'rgba(156, 163, 175, 0.6)',  // gray - other
];

function formatNumber(n: number): string {
  return n.toLocaleString();
}

function downsample(data: number[][], targetPoints: number): number[][] {
  if (data.length <= targetPoints) return data;

  const ratio = Math.ceil(data.length / targetPoints);
  const result: number[][] = [];

  for (let i = 0; i < data.length; i += ratio) {
    const chunk = data.slice(i, Math.min(i + ratio, data.length));
    const avgEntry: number[] = [];

    // Average each column
    for (let col = 0; col < chunk[0].length; col++) {
      const avg = Math.round(chunk.reduce((s, row) => s + row[col], 0) / chunk.length);
      avgEntry.push(avg);
    }
    result.push(avgEntry);
  }

  return result;
}

export async function renderIpLocation() {
  const app = document.querySelector<HTMLDivElement>('#app')!;

  app.innerHTML = `
    <div class="viz-container">
      <div class="viz-header">
        <h1>Traffic by Country</h1>
        <p>Requests per minute by geographic location</p>
      </div>
      <div class="chart-container">
        <canvas id="chart"></canvas>
      </div>
      <div id="legend" class="country-legend"></div>
      <div class="stats-row" id="stats"></div>
    </div>
  `;

  try {
    const response = await fetch('./data/traffic_slim.json');
    if (!response.ok) throw new Error('Failed to load data');

    const data: TrafficSlimData = await response.json();

    // Downsample for performance
    const sampledData = downsample(data.d, 500);

    // Prepare labels (timestamps)
    const labels = sampledData.map(d => {
      const timestamp = (data.m.start + d[0] * 60) * 1000;
      return new Date(timestamp);
    });

    // Create datasets for each country
    const datasets = data.top.map((code, i) => ({
      label: data.countries[code] || code,
      data: sampledData.map(d => d[2 + i]), // country data starts at index 2
      borderColor: COUNTRY_COLORS[i],
      backgroundColor: COUNTRY_COLORS[i].replace('0.8', '0.1'),
      fill: false,
      tension: 0.3,
      pointRadius: 0,
      borderWidth: 1.5,
    }));

    // Add "other" dataset
    datasets.push({
      label: 'Other',
      data: sampledData.map(d => d[d.length - 1]),
      borderColor: COUNTRY_COLORS[10],
      backgroundColor: COUNTRY_COLORS[10].replace('0.6', '0.1'),
      fill: false,
      tension: 0.3,
      pointRadius: 0,
      borderWidth: 1.5,
    });

    const ctx = document.getElementById('chart') as HTMLCanvasElement;

    new Chart(ctx, {
      type: 'line',
      data: {
        labels,
        datasets,
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: 'index',
          intersect: false,
        },
        plugins: {
          legend: {
            display: false,
          },
          tooltip: {
            enabled: true,
            backgroundColor: 'rgba(0, 0, 0, 0.8)',
            titleColor: '#fff',
            bodyColor: '#fff',
            padding: 12,
            displayColors: true,
            callbacks: {
              title: (items) => {
                if (!items.length) return '';
                const timestamp = items[0].parsed.x;
                if (timestamp == null) return '';
                return format(new Date(timestamp), 'MMM d, yyyy HH:mm');
              },
              label: (item) => {
                const y = item.parsed.y ?? 0;
                return ` ${item.dataset.label}: ${formatNumber(y)} req/min`;
              },
            },
          },
        },
        scales: {
          x: {
            type: 'time',
            time: {
              unit: 'day',
              displayFormats: {
                day: 'MMM d',
              },
            },
            grid: {
              display: false,
            },
            ticks: {
              maxRotation: 0,
            },
          },
          y: {
            beginAtZero: true,
            grid: {
              color: 'rgba(128, 128, 128, 0.1)',
            },
            ticks: {
              callback: (value) => formatNumber(value as number),
            },
          },
        },
      },
    });

    // Render custom legend
    const legendEl = document.getElementById('legend')!;
    const legendItems = [...data.top.map((code, i) => ({
      code,
      name: data.countries[code] || code,
      color: COUNTRY_COLORS[i],
      total: data.country_totals[code] || 0,
    })), {
      code: 'other',
      name: 'Other',
      color: COUNTRY_COLORS[10],
      total: Object.entries(data.country_totals)
        .filter(([code]) => !data.top.includes(code))
        .reduce((sum, [, count]) => sum + count, 0),
    }];

    legendEl.innerHTML = legendItems.map(item => `
      <div class="country-legend-item">
        <div class="legend-color" style="background-color: ${item.color}"></div>
        <span class="country-name">${item.name}</span>
        <span class="country-count">${formatNumber(item.total)}</span>
      </div>
    `).join('');

    // Render stats
    const statsEl = document.getElementById('stats')!;
    statsEl.innerHTML = `
      <div class="stat-card">
        <div class="label">Total Requests</div>
        <div class="value">${formatNumber(data.s.total)}</div>
      </div>
      <div class="stat-card">
        <div class="label">Avg/min</div>
        <div class="value">${data.s.avg.toFixed(1)}</div>
      </div>
      <div class="stat-card">
        <div class="label">Peak/min</div>
        <div class="value">${formatNumber(data.s.max)}</div>
      </div>
      <div class="stat-card">
        <div class="label">Countries Tracked</div>
        <div class="value">${Object.keys(data.countries).length}</div>
      </div>
    `;

  } catch (error) {
    console.error('Error loading data:', error);
    app.innerHTML = `<div class="error-message">Error loading visualization data. Make sure traffic_slim.json is in the public/data folder.</div>`;
  }
}
