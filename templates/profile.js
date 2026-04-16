// 🔄 LIVE DATA UPDATE
setInterval(() => {
    fetch('/emotion')
    .then(res => res.json())
    .then(data => {
        if (document.getElementById("points"))
            document.getElementById("points").innerText = data.points;

        if (document.getElementById("streak"))
            document.getElementById("streak").innerText = "🔥 " + data.streak + " streak";
    });
}, 1000);


// 💎 REDEEM FUNCTION (agar button use karega)
function redeem() {
    fetch('/redeem', {
        method: "POST"
    })
    .then(res => res.json())
    .then(data => {
        alert(data.msg);
    });
}


// 📊 MINI CHART (safe load)
const chartCanvas = document.getElementById("miniChart");

if (chartCanvas) {
    new Chart(chartCanvas, {
        type: 'line',
        data: {
            labels: ["Mon","Tue","Wed","Thu","Fri"],
            datasets: [{
                label: "Mood Trend",
                data: [1,2,3,2,4],
                tension: 0.4
            }]
        }
    });
}