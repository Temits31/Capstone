document.addEventListener('DOMContentLoaded', function() {
    const ctx = document.getElementById('diseasePieChart').getContext('2d');
    
    let diseasePieChart = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: [],
            datasets: [{
                label: 'Disease Detections',
                data: [], 
                backgroundColor: [
                    '#19381f', // Color for first disease
                    '#EEE82C', // Color for second disease
                    '#91CB3E', // Color for third disease
                    '#53A548', // Color for fourth disease
                    '#4C934C'  // Color for fifth disease
                ],
                borderColor: [
                    '#19381f', // Color for first disease
                    '#EEE82C', // Color for second disease
                    '#91CB3E', // Color for third disease
                    '#53A548', // Color for fourth disease
                    '#4C934C'  // Color for fifth disease
                ],
                borderWidth: 3
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'right', // Moves labels to the right of the pie chart
                    labels: {
                        usePointStyle: true, // Makes the labels look like points instead of boxes
                    }
                }
            }




        }
    });

    function updatePieChart() {
        fetch(`/get_disease_stats`)
            .then(response => response.json())
            .then(data => {
                console.log(data)
                if (data.labels && data.labels.length > 0 && data.data && data.data.length > 0) {
                    diseasePieChart.data.labels = data.labels;  // Disease names
                    diseasePieChart.data.datasets[0].data = data.data;  // Detection counts
                    diseasePieChart.update();
                } else {
                    console.error('No valid data returned from server');
                }
            })
            .catch(error => console.error('Error fetching data:', error));
    }

    updatePieChart();
});