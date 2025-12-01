import './style.css';
import { renderBotVsBrowser } from './visualizations/bot-vs-browser';
import { renderIpLocation } from './visualizations/ip-location';

// Router: Load visualization based on ?viz= parameter
function getVizParam(): string | null {
  const params = new URLSearchParams(window.location.search);
  return params.get('viz');
}

function showError(message: string) {
  const app = document.querySelector<HTMLDivElement>('#app')!;
  app.innerHTML = `<div class="error-message">${message}</div>`;
}

function showAvailableViz() {
  const app = document.querySelector<HTMLDivElement>('#app')!;
  app.innerHTML = `
    <div class="viz-container">
      <div class="viz-header">
        <h1>Traffic Visualizations</h1>
        <p>Select a visualization:</p>
      </div>
      <ul style="list-style: none; padding: 1rem 0;">
        <li style="margin-bottom: 0.5rem;">
          <a href="?viz=bot_vs_browser" style="color: #3b82f6; text-decoration: none;">
            Bot vs Browser Traffic
          </a>
        </li>
        <li style="margin-bottom: 0.5rem;">
          <a href="?viz=ip_location" style="color: #3b82f6; text-decoration: none;">
            Traffic by Country
          </a>
        </li>
      </ul>
    </div>
  `;
}

async function init() {
  const viz = getVizParam();

  if (!viz) {
    showAvailableViz();
    return;
  }

  switch (viz) {
    case 'bot_vs_browser':
      await renderBotVsBrowser();
      break;
    case 'ip_location':
      await renderIpLocation();
      break;
    default:
      showError(`Unknown visualization: ${viz}`);
  }
}

init();
