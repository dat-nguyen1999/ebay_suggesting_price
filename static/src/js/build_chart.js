var ctx = document.getElementById('chart').getContext('2d');
    var x = new Chart(ctx);
    var chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                {
                    label: 'Suggesting Price',
                    data: [],
                    borderColor:  'rgb(0, 0, 255)',

                },
                {
                    label: 'Super Comeptition',
                    data: [],
                    borderColor:  'rgb(255, 0, 0)',
                },
            ]
        },
        options: {
            elements: {
                line: {
                    fill: false,
                    tension: false
                }
            },
            title: {
                display: true,
                position: 'bottom',
                text: ''
            },
            scales: {
                yAxes: [
                    {
                        ticks: {
                            callback: function (value, index, values) {
                                return (value ? value.toString() : '') + '$'
                            },
                            beginAtZero: true
                        }
                    }
                ]
            }
        }
    });
    async function drawSoilMoistureChart(id, chart) {
        let json = null;
        while (!json || json.begin) {
            let url = `/info/ebay_listing_item/${id}`;
            let data = await fetch(url, {
                method: 'GET',
                credentials: "same-origin"
            });

            if (data.status != 200) {
                return;
            }

            json = await data.json();
            if (json) {
                chart.data.labels = json.label;
                chart.data.datasets[0].data = json.suggesting;
                chart.data.datasets[1].data = json.super_competition;
                chart.update();
            }
        }
    };
    drawSoilMoistureChart(parseInt(window.location.hash.split('&')[0].split('=')[1]), chart);