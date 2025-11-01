// ===== Configuration =====
const API_ENDPOINT = '/api/metrics';
const UPDATE_INTERVAL = 30000; // 30 seconds

// ===== Chart Instances =====
let priceChart, tvlChart, chainChart, revenueChart, buybackChart;

// ===== Initialize Dashboard =====
document.addEventListener('DOMContentLoaded', () => {
    initializeCharts();
    fetchMetrics();
    setInterval(fetchMetrics, UPDATE_INTERVAL);

    // Setup chart period controls
    setupChartControls();
});

// ===== Fetch Metrics from API =====
async function fetchMetrics() {
    try {
        const response = await fetch(API_ENDPOINT);
        if (!response.ok) throw new Error('Failed to fetch metrics');

        const data = await response.json();
        updateDashboard(data);
        updateLastUpdate();
    } catch (error) {
        console.error('Error fetching metrics:', error);
        // Show error state
        showError('Unable to fetch data. Retrying...');
    }
}

// ===== Update Dashboard =====
function updateDashboard(data) {
    // Update hero metrics
    updateHeroMetrics(data);

    // Update chain data
    updateChainData(data);

    // Update staking metrics
    updateStakingMetrics(data);

    // Update revenue and buybacks
    updateRevenueData(data);

    // Update charts
    updateCharts(data);
}

// ===== Update Hero Metrics =====
function updateHeroMetrics(data) {
    // Token price
    const price = data.token_price || 0;
    document.getElementById('token-price').textContent = `$${price.toFixed(4)}`;

    const priceChange = data.price_change_24h || 0;
    const priceChangeEl = document.getElementById('price-change');
    priceChangeEl.textContent = `${priceChange >= 0 ? '+' : ''}${priceChange.toFixed(2)}%`;
    priceChangeEl.className = `metric-change ${priceChange >= 0 ? 'positive' : 'negative'}`;

    // Market cap
    const marketCap = data.market_cap || 0;
    document.getElementById('market-cap').textContent = formatCurrency(marketCap);
    document.getElementById('mcap-rank').textContent = data.mcap_rank ? `Rank #${data.mcap_rank}` : '-';

    // Total TVL
    const tvl = data.total_tvl || 0;
    document.getElementById('total-tvl').textContent = formatCurrency(tvl);

    // Calculate TVL breakdown
    const sonic = data.chains?.sonic?.tvl || 0;
    const plasma = data.chains?.plasma?.tvl || 0;
    const ethereum = data.chains?.ethereum?.tvl || 0;
    document.getElementById('tvl-breakdown').textContent =
        `Sonic: ${formatCurrency(sonic)} | Plasma: ${formatCurrency(plasma)} | ETH: ${formatCurrency(ethereum)}`;

    // Total holders
    const totalHolders = data.total_holders || 0;
    document.getElementById('total-holders').textContent = formatNumber(totalHolders);

    const holdersChange = data.holders_change_24h || 0;
    document.getElementById('holders-change').textContent =
        `${holdersChange >= 0 ? '+' : ''}${holdersChange} today`;

    // Secondary metrics
    document.getElementById('total-supply').textContent = `${formatNumber(data.total_supply || 50000000)} TREVEE`;
    document.getElementById('circulating-supply').textContent = `${formatNumber(data.circulating_supply || 0)} TREVEE`;
    document.getElementById('staked-amount').textContent = `${formatNumber(data.total_staked || 0)} TREVEE`;
}

// ===== Update Chain Data =====
function updateChainData(data) {
    const chains = data.chains || {};

    // Sonic
    if (chains.sonic) {
        document.getElementById('sonic-supply').textContent = formatNumber(chains.sonic.supply || 0);
        document.getElementById('sonic-staked').textContent = formatNumber(chains.sonic.staked || 0);
        document.getElementById('sonic-holders').textContent = formatNumber(chains.sonic.holders || 0);
    }

    // Plasma
    if (chains.plasma) {
        document.getElementById('plasma-supply').textContent = formatNumber(chains.plasma.supply || 0);
        document.getElementById('plasma-holders').textContent = chains.plasma.holders || 19;
    }

    // Ethereum
    if (chains.ethereum) {
        document.getElementById('eth-supply').textContent = formatNumber(chains.ethereum.supply || 0);
        document.getElementById('eth-holders').textContent = formatNumber(chains.ethereum.holders || 0);
    }
}

// ===== Update Staking Metrics =====
function updateStakingMetrics(data) {
    const totalStaked = data.total_staked || 0;
    const totalSupply = data.total_supply || 50000000;
    const stakingRatio = totalSupply > 0 ? (totalStaked / totalSupply * 100) : 0;

    document.getElementById('staking-total').textContent = `${formatNumber(totalStaked)} TREVEE`;
    document.getElementById('staking-ratio').textContent = `${stakingRatio.toFixed(2)}%`;
    document.getElementById('stk-supply').textContent = formatNumber(data.stk_supply || 0);
    document.getElementById('stakers-count').textContent = formatNumber(data.stakers_count || 0);
}

// ===== Update Revenue Data =====
function updateRevenueData(data) {
    const revenue = data.revenue || {};
    const buyback = data.buyback || {};

    // Revenue
    document.getElementById('revenue-30d').textContent = formatCurrency(revenue.total_30d || 0);
    const revenueChange = revenue.change_30d || 0;
    const revenueChangeEl = document.getElementById('revenue-change');
    revenueChangeEl.textContent = `${revenueChange >= 0 ? '+' : ''}${revenueChange.toFixed(1)}%`;
    revenueChangeEl.className = `change ${revenueChange >= 0 ? 'positive' : 'negative'}`;

    document.getElementById('revenue-today').textContent = formatCurrency(revenue.today || 0);
    document.getElementById('revenue-yesterday').textContent = formatCurrency(revenue.yesterday || 0);

    // Buybacks
    document.getElementById('buyback-30d').textContent = formatCurrency(buyback.total_30d || 0);
    const buybackChange = buyback.change_30d || 0;
    const buybackChangeEl = document.getElementById('buyback-change');
    buybackChangeEl.textContent = `${buybackChange >= 0 ? '+' : ''}${buybackChange.toFixed(1)}%`;
    buybackChangeEl.className = `change ${buybackChange >= 0 ? 'positive' : 'negative'}`;

    document.getElementById('buyback-amount').textContent = `${formatNumber(buyback.tokens_bought || 0)} TREVEE`;
    document.getElementById('buyback-avg-price').textContent = formatCurrency(buyback.avg_price || 0);
}

// ===== Initialize Charts =====
function initializeCharts() {
    // Chart.js default config
    Chart.defaults.color = '#a0a0a0';
    Chart.defaults.borderColor = '#2a2d3a';

    // Price Chart
    const priceCtx = document.getElementById('priceChart').getContext('2d');
    priceChart = new Chart(priceCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Price (USD)',
                data: [],
                borderColor: '#00d4ff',
                backgroundColor: 'rgba(0, 212, 255, 0.1)',
                fill: true,
                tension: 0.4
            }]
        },
        options: getLineChartOptions('$')
    });

    // TVL Chart
    const tvlCtx = document.getElementById('tvlChart').getContext('2d');
    tvlChart = new Chart(tvlCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'TVL',
                data: [],
                borderColor: '#7b61ff',
                backgroundColor: 'rgba(123, 97, 255, 0.1)',
                fill: true,
                tension: 0.4
            }]
        },
        options: getLineChartOptions('$')
    });

    // Chain Chart
    const chainCtx = document.getElementById('chainChart').getContext('2d');
    chainChart = new Chart(chainCtx, {
        type: 'pie',
        data: {
            labels: ['Sonic', 'Plasma', 'Ethereum'],
            datasets: [{
                data: [0, 0, 0],
                backgroundColor: ['#1d4ed8', '#7b61ff', '#627eea']
            }]
        },
        options: getDoughnutChartOptions()
    });

    // Revenue Chart
    const revenueCtx = document.getElementById('revenueChart').getContext('2d');
    revenueChart = new Chart(revenueCtx, {
        type: 'bar',
        data: {
            labels: [],
            datasets: [{
                label: 'Revenue',
                data: [],
                backgroundColor: '#00ff88',
                borderRadius: 6
            }]
        },
        options: getBarChartOptions()
    });

    // Buyback Chart
    const buybackCtx = document.getElementById('buybackChart').getContext('2d');
    buybackChart = new Chart(buybackCtx, {
        type: 'bar',
        data: {
            labels: [],
            datasets: [{
                label: 'Buybacks',
                data: [],
                backgroundColor: '#00d4ff',
                borderRadius: 6
            }]
        },
        options: getBarChartOptions()
    });
}

// ===== Update Charts =====
function updateCharts(data) {
    // Update price chart
    if (data.price_history) {
        priceChart.data.labels = data.price_history.labels || [];
        priceChart.data.datasets[0].data = data.price_history.values || [];
        priceChart.update();
    }

    // Update TVL chart
    if (data.tvl_history) {
        tvlChart.data.labels = data.tvl_history.labels || [];
        tvlChart.data.datasets[0].data = data.tvl_history.values || [];
        tvlChart.update();
    }

    // Update chain chart
    if (data.chains) {
        chainChart.data.datasets[0].data = [
            data.chains.sonic?.supply || 0,
            data.chains.plasma?.supply || 0,
            data.chains.ethereum?.supply || 0
        ];
        chainChart.update();
    }

    // Update revenue chart
    if (data.revenue?.history) {
        revenueChart.data.labels = data.revenue.history.labels || [];
        revenueChart.data.datasets[0].data = data.revenue.history.values || [];
        revenueChart.update();
    }

    // Update buyback chart
    if (data.buyback?.history) {
        buybackChart.data.labels = data.buyback.history.labels || [];
        buybackChart.data.datasets[0].data = data.buyback.history.values || [];
        buybackChart.update();
    }
}

// ===== Chart Options =====
function getLineChartOptions(prefix = '') {
    return {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                display: false
            },
            tooltip: {
                mode: 'index',
                intersect: false,
                backgroundColor: 'rgba(26, 29, 38, 0.95)',
                titleColor: '#fff',
                bodyColor: '#a0a0a0',
                borderColor: '#2a2d3a',
                borderWidth: 1,
                padding: 12,
                displayColors: false,
                callbacks: {
                    label: (context) => `${prefix}${formatNumber(context.parsed.y)}`
                }
            }
        },
        scales: {
            x: {
                grid: {
                    display: false
                }
            },
            y: {
                grid: {
                    color: '#2a2d3a'
                },
                ticks: {
                    callback: (value) => prefix + formatNumber(value)
                }
            }
        }
    };
}

function getDoughnutChartOptions() {
    return {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                position: 'bottom',
                labels: {
                    padding: 16,
                    usePointStyle: true
                }
            },
            tooltip: {
                backgroundColor: 'rgba(26, 29, 38, 0.95)',
                titleColor: '#fff',
                bodyColor: '#a0a0a0',
                borderColor: '#2a2d3a',
                borderWidth: 1,
                padding: 12
            }
        }
    };
}

function getBarChartOptions() {
    return {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                display: false
            },
            tooltip: {
                backgroundColor: 'rgba(26, 29, 38, 0.95)',
                titleColor: '#fff',
                bodyColor: '#a0a0a0',
                borderColor: '#2a2d3a',
                borderWidth: 1,
                padding: 12
            }
        },
        scales: {
            x: {
                grid: {
                    display: false
                }
            },
            y: {
                grid: {
                    color: '#2a2d3a'
                },
                ticks: {
                    callback: (value) => '$' + formatNumber(value)
                }
            }
        }
    };
}

// ===== Chart Controls =====
function setupChartControls() {
    document.querySelectorAll('.chart-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            // Remove active class from all buttons
            e.target.parentElement.querySelectorAll('.chart-btn').forEach(b => b.classList.remove('active'));
            // Add active class to clicked button
            e.target.classList.add('active');

            // Fetch data for selected period
            const period = e.target.dataset.period;
            // In production, this would fetch different data based on period
            console.log('Fetching data for period:', period);
        });
    });
}

// ===== Utility Functions =====
function formatNumber(num) {
    if (num >= 1000000) {
        return (num / 1000000).toFixed(2) + 'M';
    } else if (num >= 1000) {
        return (num / 1000).toFixed(2) + 'K';
    }
    return num.toLocaleString();
}

function formatCurrency(num) {
    if (num >= 1000000000) {
        return '$' + (num / 1000000000).toFixed(2) + 'B';
    } else if (num >= 1000000) {
        return '$' + (num / 1000000).toFixed(2) + 'M';
    } else if (num >= 1000) {
        return '$' + (num / 1000).toFixed(2) + 'K';
    }
    return '$' + num.toFixed(2);
}

function updateLastUpdate() {
    const now = new Date();
    const timeString = now.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
    document.getElementById('last-update').textContent = timeString;
}

function showError(message) {
    // Simple error display - could be enhanced with a toast notification
    console.error(message);
}
