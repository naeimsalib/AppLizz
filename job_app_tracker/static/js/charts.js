// Initialize the charts when the document is ready
function initCharts(statusData, timelineData) {
    // Status Distribution Chart
    const statusCtx = document.getElementById('statusChart');
    if (statusCtx) {
        // Ensure all status types are included with their proper counts
        const statuses = [
            'Applied',
            'In Progress',
            'Interview',
            'Offer',
            'Rejected',
            'Withdrawn'
        ];
        
        // Create data array ensuring all statuses are represented
        const chartData = statuses.map(status => statusData[status] || 0);
        
        const statusChart = new Chart(statusCtx.getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: statuses,
                datasets: [{
                    data: chartData,
                    backgroundColor: [
                        '#4f46e5', // Applied
                        '#2563eb', // In Progress
                        '#059669', // Interview
                        '#047857', // Offer
                        '#dc2626', // Rejected
                        '#6b7280'  // Withdrawn
                    ],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            usePointStyle: true,
                            padding: 20
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const label = context.label || '';
                                const value = context.raw || 0;
                                return `${label}: ${value}`;
                            }
                        }
                    }
                }
            }
        });
        
        // Store the chart instance in a global variable
        window.statusChart = statusChart;
    }

    // Timeline Chart
    const timelineCtx = document.getElementById('timelineChart');
    if (timelineCtx) {
        // Define status types and their colors
        const statusTypes = [
            { status: 'Applied', color: '#4f46e5' },
            { status: 'In Progress', color: '#2563eb' },
            { status: 'Interview', color: '#059669' },
            { status: 'Offer', color: '#047857' },
            { status: 'Rejected', color: '#dc2626' },
            { status: 'Withdrawn', color: '#6b7280' }
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
            showLine: true // Ensure line is always shown
        }));

        const timelineChart = new Chart(timelineCtx.getContext('2d'), {
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
                },
                elements: {
                    point: {
                        radius: function(context) {
                            const value = context.raw;
                            return value > 0 ? 4 : 0; // Only show points for non-zero values
                        },
                        hoverRadius: 6
                    },
                    line: {
                        borderWidth: 2
                    }
                }
            }
        });

        // Store the chart instance in a global variable
        window.timelineChart = timelineChart;
    }
}

// Function to update the time range for the timeline chart
function updateTimeRange(days) {
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

    // Make an AJAX call to get new data
    fetch(`/api/applications/timeline?days=${days}`)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            // Update the timeline chart with new data
            if (window.timelineChart) {
                window.timelineChart.data.labels = data.labels;
                // Update each dataset
                window.timelineChart.data.datasets.forEach(dataset => {
                    const status = dataset.label;
                    dataset.data = data[status] || Array(data.labels.length).fill(0);
                });
                window.timelineChart.update('none'); // Use 'none' for smoother updates
            }
        })
        .catch(error => {
            console.error('Error fetching timeline data:', error);
            // Optionally show an error message to the user
            // alert('Failed to update timeline data. Please try again later.');
        });
} 