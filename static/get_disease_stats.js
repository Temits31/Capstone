document.addEventListener('DOMContentLoaded', function() {
    const ctx = document.getElementById('diseasePieChart').getContext('2d');
    
    let diseasePieChart = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: [],  // Disease names will be populated from the backend
            datasets: [{
                label: 'Disease Detections',
                data: [],  // Detection counts will be populated from the backend
                backgroundColor: [
                    'rgba(255, 99, 132, 0.2)',
                    'rgba(54, 162, 235, 0.2)',
                    'rgba(255, 206, 86, 0.2)',
                    'rgba(75, 192, 192, 0.2)',
                    'rgba(153, 102, 255, 0.2)',
                    'rgba(255, 159, 64, 0.2)'
                ],
                borderColor: [
                    'rgba(255, 99, 132, 1)',
                    'rgba(54, 162, 235, 1)',
                    'rgba(255, 206, 86, 1)',
                    'rgba(75, 192, 192, 1)',
                    'rgba(153, 102, 255, 1)',
                    'rgba(255, 159, 64, 1)'
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true
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