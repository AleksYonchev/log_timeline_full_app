
document.addEventListener('DOMContentLoaded', function () {
    const form = document.getElementById('uploadForm');
    const messageBox = document.getElementById('messageBox');

    if (form) {
        form.addEventListener('submit', async function (e) {
            e.preventDefault();

            const fileInput = form.querySelector('input[name="file"]');
            const file = fileInput.files[0];
            if (!file) return;

            const formData = new FormData();
            formData.append('file', file);

            const res = await fetch('/upload', {
                method: 'POST',
                body: formData
            });

            const data = await res.json();

            if (data.message) {
                messageBox.innerText = data.message;
                messageBox.style.display = 'block';

                const map = document.getElementById('map');
                const canvas = document.querySelector('canvas');
                if (map) map.style.display = 'none';
                if (canvas) canvas.style.display = 'none';
                return;
            }

            if (data.timeline_id) {
                await loadTimeline(data.timeline_id);
            }
        });
    }
});

async function loadTimeline(timelineId) {
    const res = await fetch(`/timeline/${timelineId}`);
    const data = await res.json();
    const events = data.events;

    const ctx = document.getElementById('timelineChart').getContext('2d');

    const chartData = {
        labels: events.map(e => e.datetime),
        datasets: [{
            label: 'Събития по време',
            data: events.map(e => ({ x: e.datetime, y: 1 })),
            backgroundColor: 'rgba(54, 162, 235, 0.6)'
        }]
    };

    const chartOptions = {
        responsive: true,
        scales: {
            x: {
                type: 'time',
                time: {
                    unit: 'hour',
                    tooltipFormat: 'yyyy-MM-dd HH:mm',
                    displayFormats: {
                        hour: 'HH:mm',
                        day: 'MMM dd',
                        minute: 'HH:mm'
                    }
                },
                title: {
                    display: true,
                    text: 'Дата и час'
                },
                ticks: {
                    autoSkip: true,
                    maxRotation: 45,
                    minRotation: 20
                }
            },
            y: {
                display: false
            }
        },
        plugins: {
            tooltip: {
                callbacks: {
                    label: function(context) {
                        const event = events[context.dataIndex];
                        return `${event.title}`;
                    }
                }
            }
        }
    };

    if (window.timelineChart) {
        window.timelineChart.destroy();
    }

    window.timelineChart = new Chart(ctx, {
        type: 'scatter',
        data: chartData,
        options: chartOptions
    });
}
