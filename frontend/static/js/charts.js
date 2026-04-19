/**
 * Sportylytics – charts.js
 * Chart.js-based visualizations for match statistics.
 * Chart.js is loaded from CDN in base.html.
 */

/**
 * Render a possession donut chart inside a canvas element.
 * @param {string} canvasId - ID of the <canvas> element
 * @param {number} homePct  - Home team possession percentage (0-100)
 * @param {string} homeColor - Home accent color
 * @param {string} awayColor - Away accent color
 */
function renderPossessionChart(canvasId, homePct, homeColor, awayColor) {
  const canvas = document.getElementById(canvasId);
  if (!canvas || typeof Chart === 'undefined') return;

  const awayPct = 100 - homePct;

  new Chart(canvas, {
    type: 'doughnut',
    data: {
      labels: ['Home', 'Away'],
      datasets: [{
        data: [homePct, awayPct],
        backgroundColor: [homeColor || '#00b4d8', awayColor || '#f97316'],
        borderColor: '#1a1a1a',
        borderWidth: 3,
        hoverOffset: 4,
      }]
    },
    options: {
      cutout: '72%',
      responsive: true,
      maintainAspectRatio: true,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: ctx => ` ${ctx.label}: ${ctx.parsed}%`
          }
        }
      },
      animation: {
        animateRotate: true,
        duration: 800,
        easing: 'easeOutQuart',
      }
    }
  });
}

/**
 * Render a horizontal bar chart comparing two teams on a set of statistics.
 */
function renderStatsBarChart(canvasId, labels, homeValues, awayValues, homeLabel, awayLabel) {
  const canvas = document.getElementById(canvasId);
  if (!canvas || typeof Chart === 'undefined') return;

  new Chart(canvas, {
    type: 'bar',
    data: {
      labels,
      datasets: [
        {
          label: homeLabel,
          data: homeValues,
          backgroundColor: 'rgba(0, 180, 216, 0.8)',
          borderRadius: 4,
          borderSkipped: false,
        },
        {
          label: awayLabel,
          data: awayValues,
          backgroundColor: 'rgba(249, 115, 22, 0.8)',
          borderRadius: 4,
          borderSkipped: false,
        }
      ]
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      plugins: {
        legend: {
          display: true,
          labels: {
            color: '#9ca3af',
            font: { family: 'Inter', size: 12 },
            boxWidth: 12,
            borderRadius: 3,
          }
        },
        tooltip: {
          backgroundColor: '#1e1e1e',
          borderColor: '#2a2a2a',
          borderWidth: 1,
          titleColor: '#f0f0f0',
          bodyColor: '#9ca3af',
        }
      },
      scales: {
        x: {
          grid: { color: '#1c1c1c' },
          ticks: { color: '#6b7280', font: { family: 'Inter', size: 11 } }
        },
        y: {
          grid: { color: '#1c1c1c' },
          ticks: { color: '#9ca3af', font: { family: 'Inter', size: 12 } }
        }
      },
      animation: {
        duration: 700,
        easing: 'easeOutQuart',
      }
    }
  });
}

// Expose globally
window.renderPossessionChart = renderPossessionChart;
window.renderStatsBarChart   = renderStatsBarChart;
