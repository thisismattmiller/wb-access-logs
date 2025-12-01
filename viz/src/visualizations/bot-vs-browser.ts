import { Chart, registerables } from 'chart.js';
import 'chartjs-adapter-date-fns';
import { format } from 'date-fns';

Chart.register(...registerables);

interface BotVsBrowserData {
  m: {
    start: number;
    minutes: number;
    interval: number;
  };
  s: {
    total_bot: number;
    total_browser: number;
    bot_pct: number;
    browser_pct: number;
    avg_bot_per_min: number;
    avg_browser_per_min: number;
    max_bot_per_min: number;
    max_browser_per_min: number;
    peak_bot_minute: string;
    peak_browser_minute: string;
  };
  d: [number, number, number][]; // [minute_offset, bot_count, browser_count]
}

function formatNumber(n: number): string {
  return n.toLocaleString();
}

function downsample(data: [number, number, number][], targetPoints: number): [number, number, number][] {
  if (data.length <= targetPoints) return data;

  const ratio = Math.ceil(data.length / targetPoints);
  const result: [number, number, number][] = [];

  for (let i = 0; i < data.length; i += ratio) {
    const chunk = data.slice(i, Math.min(i + ratio, data.length));
    const avgOffset = Math.round(chunk.reduce((s, d) => s + d[0], 0) / chunk.length);
    const avgBot = Math.round(chunk.reduce((s, d) => s + d[1], 0) / chunk.length);
    const avgBrowser = Math.round(chunk.reduce((s, d) => s + d[2], 0) / chunk.length);
    result.push([avgOffset, avgBot, avgBrowser]);
  }

  return result;
}

export async function renderBotVsBrowser() {
  const app = document.querySelector<HTMLDivElement>('#app')!;

  app.innerHTML = `
    <div class="viz-container">
      <div class="viz-header">
        <h1>Bot vs Browser Traffic</h1>
        <p>Requests per minute over time</p>
      </div>
      <div class="chart-container">
        <canvas id="chart"></canvas>
      </div>
      <div class="legend">
        <div class="legend-item">
          <div class="legend-color bot"></div>
          <span>Bot Traffic</span>
        </div>
        <div class="legend-item">
          <div class="legend-color browser"></div>
          <span>Browser Traffic</span>
        </div>
      </div>
      <div class="stats-row" id="stats"></div>
    </div>
  `;

  try {
    const response = await fetch('./data/bot_vs_browser.json');
    if (!response.ok) throw new Error('Failed to load data');

    const data: BotVsBrowserData = await response.json();

    // Downsample for performance (target ~500 points for smooth rendering)
    const sampledData = downsample(data.d, 500);

    // Prepare chart data
    const labels = sampledData.map(d => {
      const timestamp = (data.m.start + d[0] * 60) * 1000;
      return new Date(timestamp);
    });

    const botData = sampledData.map(d => d[1]);
    const browserData = sampledData.map(d => d[2]);

    const ctx = document.getElementById('chart') as HTMLCanvasElement;

    new Chart(ctx, {
      type: 'line',
      data: {
        labels,
        datasets: [
          {
            label: 'Bot Traffic',
            data: botData,
            borderColor: 'rgba(239, 68, 68, 0.8)',
            backgroundColor: 'rgba(239, 68, 68, 0.1)',
            fill: true,
            tension: 0.3,
            pointRadius: 0,
            borderWidth: 1.5,
          },
          {
            label: 'Browser Traffic',
            data: browserData,
            borderColor: 'rgba(34, 197, 94, 0.8)',
            backgroundColor: 'rgba(34, 197, 94, 0.1)',
            fill: true,
            tension: 0.3,
            pointRadius: 0,
            borderWidth: 1.5,
          },
        ],
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

    // Render stats
    const statsEl = document.getElementById('stats')!;
    statsEl.innerHTML = `
      <div class="stat-card">
        <div class="label">Total Requests</div>
        <div class="value">${formatNumber(data.s.total_bot + data.s.total_browser)}</div>
      </div>
      <div class="stat-card">
        <div class="label">Bot Traffic</div>
        <div class="value bot">${formatNumber(data.s.total_bot)} (${data.s.bot_pct}%)</div>
      </div>
      <div class="stat-card">
        <div class="label">Browser Traffic</div>
        <div class="value browser">${formatNumber(data.s.total_browser)} (${data.s.browser_pct}%)</div>
      </div>
      <div class="stat-card">
        <div class="label">Avg Bot/min</div>
        <div class="value bot">${data.s.avg_bot_per_min.toFixed(1)}</div>
      </div>
      <div class="stat-card">
        <div class="label">Avg Browser/min</div>
        <div class="value browser">${data.s.avg_browser_per_min.toFixed(1)}</div>
      </div>
      <div class="stat-card">
        <div class="label">Peak Bot/min</div>
        <div class="value bot">${formatNumber(data.s.max_bot_per_min)}</div>
      </div>
      <div class="stat-card">
        <div class="label">Peak Browser/min</div>
        <div class="value browser">${formatNumber(data.s.max_browser_per_min)}</div>
      </div>
    `;

  } catch (error) {
    console.error('Error loading data:', error);
    app.innerHTML = `<div class="error-message">Error loading visualization data. Make sure bot_vs_browser.json is in the public/data folder.</div>`;
  }
}
