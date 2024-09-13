const ctx = document.getElementById('diseaseChart').getContext('2d');
    
let diseaseChart = new Chart(ctx, {
    type: 'line',
    data: {
        labels: [],
        datasets: [{
            label: 'Disease Detections',
            data: [],
            borderColor: 'rgba(75, 192, 192, 1)',
            fill: false,
            tension: 0.1
        }]
    },
    options: {
        responsive: true,
        scales: {
            x: {
                type: 'time',
                time: {
                    unit: 'day'  // Default unit
                }
            },
            y: {
                beginAtZero: true
            }
        }
    }
});

function updateChart() {
    const filterType = document.getElementById('filterSelect').value;

    fetch(`/get_disease_data?filter=${filterType}`)
        .then(response => response.json())
        .then(data => {
            let timeUnit = 'day';

            if (filterType === 'weekly') timeUnit = 'week';
            else if (filterType === 'monthly') timeUnit = 'month';
            else if (filterType === 'yearly') timeUnit = 'year';

            diseaseChart.data.labels = data.labels;
            diseaseChart.data.datasets[0].data = data.data;
            diseaseChart.options.scales.x.time.unit = timeUnit;
            diseaseChart.update();
        })
        .catch(error => console.error('Error fetching data:', error));
}

// Initial chart load
updateChart();