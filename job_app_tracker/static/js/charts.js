let statusChart;
let timelineChart;

// Status chart configuration
const statusColors = {
    'Applied': '#4CAF50',
    'In Progress': '#2196F3',
    'Interview': '#9C27B0',
    'Offer': '#FFC107',
    'Rejected': '#F44336',
    'Withdrawn': '#607D8B'
};

// Function to fetch status counts from the API
async function fetchStatusCounts() {
    try {
        const response = await fetch('/api/status-counts');
        if (!response.ok) {
            throw new Error('Failed to fetch status counts');
        }
        return await response.json();
    } catch (error) {
        console.error('Error fetching status counts:', error);
        return null;
    }
}

// Function to fetch timeline data from the API
async function fetchTimelineData(days = 28) {
    try {
        const response = await fetch(`/api/applications/timeline?days=${days}`);
        if (!response.ok) {
            throw new Error('Failed to fetch timeline data');
        }
        return await response.json();
    } catch (error) {
        console.error('Error fetching timeline data:', error);
        return null;
    }
}

// Function to create or update the status chart
async function createStatusChart() {
    const statusCounts = await fetchStatusCounts();
    if (!statusCounts) return;

    const labels = Object.keys(statusCounts);
    const data = Object.values(statusCounts);
    const colors = labels.map(label => statusColors[label]);

    const statusCtx = document.getElementById('statusChart');
    if (!statusCtx) return;

    // Destroy existing chart if it exists
    const existingChart = Chart.getChart(statusCtx);
    if (existingChart) {
        existingChart.destroy();
    }

    // Create new chart
    new Chart(statusCtx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: colors,
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right'
                }
            }
        }
    });
}

// Function to create or update the timeline chart
async function createTimelineChart() {
    const timelineData = await fetchTimelineData();
    const timelineCtx = document.getElementById('timelineChart');
    
    if (!timelineCtx || !timelineData) return;

    // Destroy existing chart if it exists
    const existingChart = Chart.getChart(timelineCtx);
    if (existingChart) {
        existingChart.destroy();
    }

    // Define status types and their colors
    const statusTypes = [
        { status: 'Applied', color: '#4CAF50' },
        { status: 'In Progress', color: '#2196F3' },
        { status: 'Interview', color: '#9C27B0' },
        { status: 'Offer', color: '#FFC107' },
        { status: 'Rejected', color: '#F44336' },
        { status: 'Withdrawn', color: '#607D8B' }
    ];

    // Create a dataset for each status
    const datasets = statusTypes.map(({ status, color }) => ({
        label: status,
        data: timelineData[status] || Array(timelineData.labels.length).fill(0),
        borderColor: color,
        backgroundColor: color + '20', // Add transparency
        fill: false,
        tension: 0.4,
        borderWidth: 2,
        pointRadius: 4,
        pointHoverRadius: 6,
        spanGaps: false,
        showLine: true
    }));

    // Create new chart
    new Chart(timelineCtx, {
        type: 'line',
        data: {
            labels: timelineData.labels,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1
                    },
                    grid: {
                        display: true,
                        drawBorder: true
                    }
                },
                x: {
                    grid: {
                        display: false
                    }
                }
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'bottom',
                    labels: {
                        usePointStyle: true,
                        padding: 20,
                        boxWidth: 10
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        label: function(context) {
                            const label = context.dataset.label || '';
                            const value = context.parsed.y;
                            return `${label}: ${value} application${value !== 1 ? 's' : ''}`;
                        }
                    }
                }
            },
            interaction: {
                mode: 'nearest',
                axis: 'x',
                intersect: false
            }
        }
    });
}

// Function to update the time range for the timeline chart
async function updateTimeRange(days) {
    // Remove active class from all buttons
    document.querySelectorAll('.time-range-btn').forEach(btn => {
        btn.classList.remove('bg-blue-500', 'text-white');
        btn.classList.add('bg-gray-100', 'text-gray-700');
    });

    // Add active class to clicked button
    const activeBtn = document.querySelector(`[data-days="${days}"]`);
    if (activeBtn) {
        activeBtn.classList.remove('bg-gray-100', 'text-gray-700');
        activeBtn.classList.add('bg-blue-500', 'text-white');
    }

    // Update the timeline chart
    const timelineData = await fetchTimelineData(days);
    const timelineCtx = document.getElementById('timelineChart');
    const existingChart = Chart.getChart(timelineCtx);

    if (existingChart && timelineData) {
        existingChart.data.labels = timelineData.labels;
        existingChart.data.datasets.forEach(dataset => {
            const status = dataset.label;
            dataset.data = timelineData[status] || Array(timelineData.labels.length).fill(0);
        });
        existingChart.update('none');
    } else {
        await createTimelineChart();
    }
}

// Initialize charts
async function initCharts() {
    await createStatusChart();
    await createTimelineChart();
}

// Event listeners for real-time updates
document.addEventListener('applicationAdded', initCharts);
document.addEventListener('applicationUpdated', initCharts);
document.addEventListener('applicationDeleted', initCharts);

// Initialize charts when the document is ready
document.addEventListener('DOMContentLoaded', initCharts); 