let barChart, pieChart;

function loadCharts() {
    fetch('/analytics_data')
    .then(res => res.json())
    .then(data => {

        const labels = data.labels;
        const values = data.values;

        // 🔥 BAR CHART
        if (barChart) barChart.destroy();
        barChart = new Chart(document.getElementById("barChart"), {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Emotion Count',
                    data: values
                }]
            }
        });

        // 🔥 PIE CHART
        if (pieChart) pieChart.destroy();
        pieChart = new Chart(document.getElementById("pieChart"), {
            type: 'pie',
            data: {
                labels: labels,
                datasets: [{
                    data: values
                }]
            }
        });

    });
}

// 🔄 AUTO UPDATE
setInterval(loadCharts, 2000);
loadCharts();