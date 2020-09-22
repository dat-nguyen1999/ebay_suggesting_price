var ctx = document.getElementById('chart').getContext('2d');
var x = new Chart(ctx);
var chart = new Chart(ctx, {
    type: 'line',
    data: {
        labels: [],
        datasets: [
            {
                label: 'Suggested Price',
                data: [],
                borderColor:  'rgb(234,165,0)',
                borderWidth : 5

            },
            {
                label: 'Super Comeptition',     //
                data: [],
                borderColor:  'rgb(0,127,84)',

            },
            {
                label: 'My Competition Price',
                data: [],
                borderColor:  'rgb(0,191,255)',

            },

            {
                label: 'Minimum Price',
                data: [],
                borderColor:  'rgb(146,201,99)',
                hidden: true,

            },
            {
                label: 'Maximum Price',
                data: [],
                borderColor:  'rgb(216,102,99)',    // đỏ
                hidden: true,

            },
        ]
    },
    options: {
        responsive: true,
        aspectRatio: 1.7,
        maintainAspectRatio: true,
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
                            return '$'+(value ? value.toString() : '')
                        },
                        beginAtZero: false
                    }
                }
            ]
        }
    }
});
async function get_history_price(id, chart, group_by="day") {
    let json = null;
    while (!json || json.begin) {
        let url = `/info/ebay_listing_item/${id}?group_by=${group_by}`;
        let data = await fetch(url, {
            method: 'GET',
            credentials: "same-origin"
        });

        if (data.status != 200) {
            return;
        }

        json = await data.json();
        if (json) {
            if (group_by === 'day'){
                chart.options.scales.xAxes =  [{
                    type: 'time',
                    time: {
                        parser: 'HH:mm A',
                        unit: 'minute',
                        displayFormats: {
                            minute: 'hh:mm A'
                        },

                    },
                    ticks: {
                        source: 'labels'
                    }
                }];
                chart.options.tooltips.callbacks.footer = function (tooltipItem){
                    reason = json.reason[tooltipItem[0]['index']];
                    if (reason != "" && tooltipItem[0]['datasetIndex'] == 0){
                        return 'Reason:\n ' + json.reason[tooltipItem[0]['index']];
                    }
                }
                chart.options.tooltips.bodyFontColor ='#D1F2EB'
                chart.data.labels = json.label.map(parseDatetime);
            }
            else if (group_by === 'week'){
                chart.options.scales.xAxes = []
                chart.options.tooltips.callbacks.footer = function (tooltipItem){
                    reason = json.reason[tooltipItem[0]['index']];
                    if (reason && tooltipItem[0]['datasetIndex'] == 0){
                        return 'Reason:\n ' + json.reason[tooltipItem[0]['index']];
                    }
                }
                chart.options.tooltips.bodyFontColor ='#D1F2EB'
                chart.data.labels = json.label;
            }
            else {
                chart.options.scales.xAxes =  [{
                    type: 'time',
                    time: {
                        parser: 'YYYY-MMM-D',
                        unit: 'day',
                        displayFormats: {
                            day: 'YYYY MMM D'
                        },

                    },
                    ticks: {
                        source: 'labels'
                    }
                }];
                chart.options.tooltips.callbacks.footer = function (tooltipItem){
                    reason = json.reason[tooltipItem[0]['index']];
                    if (reason != "" && tooltipItem[0]['datasetIndex'] == 0){
                        return 'Reason:\n' + json.reason[tooltipItem[0]['index']];
                    }
                }
                chart.options.tooltips.bodyFontColor ='#D1F2EB'
                chart.data.labels = json.label.map(parseDatetime);
            }
            chart.data.datasets[0].data = json.suggesting;
            chart.data.datasets[2].data = json.my_competition;
            chart.data.datasets[1].data = json.super_competition;
            chart.data.datasets[3].data = json.minimum_price;
            chart.data.datasets[4].data = json.maximum_price;
            chart.update();
        }
    }
};
// 2020-09-04 22:04
function parseDatetime(item){
    //var datetime = moment(item,"hh:mm");
    var datetime = new Date(item);
    return datetime;
}
console.log("456")

function getId (){
    var My_params = new URLSearchParams(window.location.href);
    var id = My_params.get('id');
    if (!id){
        id = parseInt(window.location.hash.split('&')[0].split('=')[1]);
    }
    return id;
}
get_history_price(getId(), chart);

$('#filter_chart').on('change', function() {
    group_by = $('#filter_chart')[0].value;
    get_history_price(getId(), chart, group_by);
});

$('#btn_resize').click(function(e){
    chart.options.maintainAspectRatio = !chart.options.maintainAspectRatio;
    $('#myDiv').toggleClass('fullscreen');
    $('#btn_resize').toggleClass('fullscreen');
    setTimeout(function (){
        chart.update();
    },50);
});