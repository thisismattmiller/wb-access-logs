<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';

interface CountryInfo {
  code: string;
  name: string;
  count: number;
  percentage: number;
}

interface BotGeo {
  countries: Record<string, CountryInfo>;
  top_cities: Record<string, number>;
  timezones: Record<string, number>;
}

interface BotData {
  count: number;
  ips: string[];
  user_agents: string[];
  info_urls: string[];
  geo: BotGeo;
}

interface BotSummaryData {
  metadata: {
    total_requests: number;
    bot_requests: number;
    browser_requests: number;
    unique_bot_types: number;
    unique_bot_instances: number;
    generated_at: string;
  };
  bot_summary: Record<string, BotData>;
}

interface BotRow {
  name: string;
  count: number;
  ipCount: number;
  userAgentCount: number;
  infoUrls: string[];
  topCountries: CountryInfo[];
}

const data = ref<BotSummaryData | null>(null);
const loading = ref(true);
const error = ref<string | null>(null);
const searchQuery = ref('');
const sortKey = ref<'name' | 'count'>('count');
const sortAsc = ref(false);

const rows = computed<BotRow[]>(() => {
  if (!data.value) return [];

  return Object.entries(data.value.bot_summary).map(([name, bot]) => {
    const topCountries = Object.values(bot.geo?.countries || {})
      .sort((a, b) => b.count - a.count)
      .slice(0, 5);

    return {
      name,
      count: bot.count,
      ipCount: bot.ips.length,
      userAgentCount: bot.user_agents.length,
      infoUrls: bot.info_urls || [],
      topCountries,
    };
  });
});

const filteredRows = computed(() => {
  let result = rows.value;

  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase();
    result = result.filter(row => row.name.toLowerCase().includes(query));
  }

  result = [...result].sort((a, b) => {
    if (sortKey.value === 'name') {
      return sortAsc.value
        ? a.name.localeCompare(b.name)
        : b.name.localeCompare(a.name);
    } else {
      return sortAsc.value ? a.count - b.count : b.count - a.count;
    }
  });

  return result;
});

function toggleSort(key: 'name' | 'count') {
  if (sortKey.value === key) {
    sortAsc.value = !sortAsc.value;
  } else {
    sortKey.value = key;
    sortAsc.value = key === 'name'; // Default asc for name, desc for count
  }
}

function formatNumber(n: number): string {
  return n.toLocaleString();
}

function cleanUrl(url: string): string {
  // Clean up malformed URLs with escape sequences
  return url.replace(/\\x[0-9A-Fa-f]{2}/g, '');
}

onMounted(async () => {
  try {
    const response = await fetch('./data/bot_summary_geo.json');
    if (!response.ok) throw new Error('Failed to load data');
    data.value = await response.json();
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Unknown error';
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <div>
    <h1>Bot Summary Explorer</h1>
    <p class="subtitle">Explore bot traffic data from nginx access logs</p>

    <div v-if="loading" class="loading">Loading data...</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <template v-else-if="data">
      <div class="stats-bar">
        <div class="stat">
          <span class="stat-label">Bot Types:</span>
          <span class="stat-value">{{ formatNumber(data.metadata.unique_bot_types) }}</span>
        </div>
        <div class="stat">
          <span class="stat-label">Bot Requests:</span>
          <span class="stat-value">{{ formatNumber(data.metadata.bot_requests) }}</span>
        </div>
        <div class="stat">
          <span class="stat-label">Unique IPs:</span>
          <span class="stat-value">{{ formatNumber(data.metadata.unique_bot_instances) }}</span>
        </div>
      </div>

      <div class="search-box">
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Search bot name..."
        />
      </div>

      <div class="table-container">
        <table>
          <thead>
            <tr>
              <th
                :class="{ sorted: sortKey === 'name' }"
                @click="toggleSort('name')"
              >
                Bot Name
                <span class="sort-icon">{{ sortKey === 'name' ? (sortAsc ? '↑' : '↓') : '↕' }}</span>
              </th>
              <th
                :class="{ sorted: sortKey === 'count' }"
                @click="toggleSort('count')"
                style="text-align: right"
              >
                Requests
                <span class="sort-icon">{{ sortKey === 'count' ? (sortAsc ? '↑' : '↓') : '↕' }}</span>
              </th>
              <th style="text-align: right">IPs</th>
              <th style="text-align: right">User Agents</th>
              <th>Top Countries</th>
              <th>Info URLs</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in filteredRows" :key="row.name">
              <td class="bot-name">{{ row.name }}</td>
              <td class="count">{{ formatNumber(row.count) }}</td>
              <td class="count ip-count">{{ formatNumber(row.ipCount) }}</td>
              <td class="count ua-count">{{ row.userAgentCount }}</td>
              <td>
                <div class="country-list">
                  <span
                    v-for="country in row.topCountries"
                    :key="country.code"
                    class="country-item"
                  >
                    {{ country.name }}<span class="pct">{{ country.percentage }}%</span>
                  </span>
                </div>
              </td>
              <td>
                <ul v-if="row.infoUrls.length" class="url-list">
                  <li v-for="url in row.infoUrls" :key="url">
                    <a :href="cleanUrl(url)" target="_blank" rel="noopener">
                      {{ cleanUrl(url) }}
                    </a>
                  </li>
                </ul>
                <span v-else class="ua-count">-</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <p class="subtitle" style="margin-top: 1rem;">
        Showing {{ filteredRows.length }} of {{ rows.length }} bot types
      </p>
    </template>
  </div>
</template>
