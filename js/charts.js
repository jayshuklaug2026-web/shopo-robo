/**
 * Shopo Robo - Interactive Chart Manager
 * Renders P&L bar charts and market price trend visualizations using Chart.js or HTML Canvas fallback.
 */

const ChartsManager = {
    pnlChart: null,
    salesAnalyticsChart: null,

    init() {
        this.renderDashboardPnL();
    },

    // Render the exact Profit & Loss chart from the mockup
    renderDashboardPnL() {
        const ctx = document.getElementById('pnlChartCanvas');
        if (!ctx) return;

        const sales = StoreData.stats.monthlySales || 156000;
        const expenses = StoreData.stats.monthlyExpenses || 134440;
        const profit = StoreData.stats.monthlyProfit || 21560;

        if (window.Chart) {
            if (this.pnlChart) this.pnlChart.destroy();

            this.pnlChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: ['Sales', 'Expenses', 'Profit'],
                    datasets: [{
                        data: [sales, expenses, profit],
                        backgroundColor: [
                            '#84CC16', // Vibrant Lime Green for Sales
                            '#94A3B8', // Neutral Slate for Expenses
                            '#65A30D'  // Deep Lime Green for Profit
                        ],
                        borderRadius: 6,
                        borderSkipped: false,
                        barThickness: 34
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    return '₹ ' + Number(context.raw).toLocaleString('en-IN');
                                }
                            }
                        }
                    },
                    scales: {
                        x: {
                            grid: { display: false },
                            ticks: { font: { family: "'Plus Jakarta Sans', sans-serif", size: 12, weight: '600' }, color: '#475569' }
                        },
                        y: {
                            display: false,
                            beginAtZero: true
                        }
                    }
                }
            });
        } else {
            // High-fidelity Canvas fallback if Chart.js is offline
            this.renderCanvasBarChartFallback(ctx, [
                { label: 'Sales', val: sales, color: '#84CC16' },
                { label: 'Expenses', val: expenses, color: '#94A3B8' },
                { label: 'Profit', val: profit, color: '#65A30D' }
            ]);
        }
    },

    // Render detailed Analytics Chart for the Sales & Profit View
    renderDetailedSalesChart() {
        const ctx = document.getElementById('detailedSalesChartCanvas');
        if (!ctx || !window.Chart) return;

        if (this.salesAnalyticsChart) this.salesAnalyticsChart.destroy();

        this.salesAnalyticsChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: ['Week 1', 'Week 2', 'Week 3', 'Week 4'],
                datasets: [
                    {
                        label: 'Revenue (₹)',
                        data: [32000, 41000, 38500, 44500],
                        borderColor: '#84CC16',
                        backgroundColor: 'rgba(132, 204, 22, 0.1)',
                        fill: true,
                        tension: 0.35,
                        pointBackgroundColor: '#84CC16'
                    },
                    {
                        label: 'Expenses (₹)',
                        data: [28000, 34000, 31000, 37440],
                        borderColor: '#94A3B8',
                        borderDash: [5, 5],
                        tension: 0.35,
                        pointBackgroundColor: '#94A3B8'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'top' },
                    tooltip: {
                        callbacks: {
                            label: function(c) { return `${c.dataset.label}: ₹ ${c.raw.toLocaleString('en-IN')}`; }
                        }
                    }
                },
                scales: {
                    y: {
                        ticks: {
                            callback: function(v) { return '₹' + (v / 1000) + 'k'; }
                        }
                    }
                }
            }
        });
    },

    // HTML5 canvas fallback
    renderCanvasBarChartFallback(canvas, items) {
        const ctx = canvas.getContext('2d');
        const w = canvas.width;
        const h = canvas.height;
        ctx.clearRect(0, 0, w, h);

        const maxVal = Math.max(...items.map(i => i.val));
        const barWidth = 32;
        const gap = (w - (items.length * barWidth)) / (items.length + 1);

        items.forEach((item, idx) => {
            const barH = (item.val / maxVal) * (h - 40);
            const x = gap + idx * (barWidth + gap);
            const y = h - 25 - barH;

            // Draw bar
            ctx.fillStyle = item.color;
            ctx.beginPath();
            ctx.roundRect ? ctx.roundRect(x, y, barWidth, barH, 4) : ctx.rect(x, y, barWidth, barH);
            ctx.fill();

            // Label
            ctx.fillStyle = '#475569';
            ctx.font = '11px sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText(item.label, x + barWidth / 2, h - 8);

            // Value
            ctx.font = '10px sans-serif';
            ctx.fillText('₹' + Math.round(item.val / 1000) + 'k', x + barWidth / 2, y - 5);
        });
    }
};

window.ChartsManager = ChartsManager;
