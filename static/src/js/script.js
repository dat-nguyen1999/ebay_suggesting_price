odoo.define('ebay_pricer_1.dashboard', function (require) {
    'use strict';

    var field_registry = require('web.field_registry');
    var field_utils = require('web.field_utils');
    var BasicFields = require('web.basic_fields');
    var core = require('web.core');
    var qweb = core.qweb;
    var rpc = require('web.rpc')



    var basisGraph = BasicFields.FieldChar.extend({
        template: "basic_graph",
        jsLibs: [
            '/web/static/lib/Chart/Chart.js',
        ],
        xmlDependencies: ["/ebay_pricer_1/static/src/xml/tmpl.xml"],
        events: _.extend({}, BasicFields.FieldChar.prototype.events, {
            'change #filter_chart': '_selectRangeChange',
            'click #btn_resize': '_resizeEvent'
        }),
        _resizeEvent: function (event) {

            chart.options.maintainAspectRatio = !chart.options.maintainAspectRatio;
            $('#myDiv').toggleClass('fullscreen');
            $('#btn_resize').toggleClass('fullscreen');
            setTimeout(function (){
                chart.update();
            },50);

        },
        _selectRangeChange: function (event) {
            // Change range interval here
        },

        _doDebouncedAction: function () {
            // this.datewidget.changeDatetime();
        },
        _getValue: function () {
            return this.value
        },

        init: function () {
            this._super.apply(this, arguments);
        },
        start: function () {
            // this.$el.append(qweb.render('time_picker'))
            this._super.apply(this, arguments);
        },

        _renderEdit: function () {
            this.$input = this.$el
            this._renderGraph()
        },
        _renderReadonly: function () {
            this.$input = this.$el
            this._renderGraph()
        }
        ,
        _renderGraph: async function () {
            this._canvas = this.$('#chart')
            this._filter_chart = this.$('#filter_chart')
            console.log(this.value);

            let return_val = await this._rpc({
                model:"ebay_listing",
                method:"get_database_from_server",
                args:[this.value, this._filter_chart.val()]
            })
            console.log(return_val)
            function parseDatetime(item){
                //var datetime = moment(item,"hh:mm");
                var datetime = new Date(item);
                return datetime;
            }

            var ctx = document.getElementById('chart').getContext('2d');
            var chart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [
                        {
                            label: 'Suggested Price',
                            data: [],
                            borderColor:  'rgb(0,191,185)',

                        },
                        {
                            label: 'Super Comeptition',     // vàng
                            data: [],
                            borderColor:  'rgb(234,165,0)',
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
                    }


                    ,
                    scales: {
                        yAxes: [
                            {
                                ticks: {
                                    callback: function (value, index, values) {
                                        return (value ? value.toString() : '') + '$'
                                    },
                                    beginAtZero: false
                                }
                            }
                        ]
                    }
                }
            });
            if (this._filter_chart === 'day'){
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
                console.log(chart);
                chart.config.data.labels = return_val.label.map(parseDatetime);
                chart.config.data.datasets[0].data = return_val.suggesting;
            chart.config.data.datasets[1].data = return_val.super_competition;
            chart.config.data.datasets[2].data = return_val.minimum_price;
            chart.config.data.datasets[3].data = return_val.maximum_price;
            chart.update();
            }
            else if (this._filter_chart === 'week'){
                chart.options.scales.xAxes = []
                chart.config.data.labels = return_val.label;
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

                chart.config.data.labels = return_val.label.map(parseDatetime);
                chart.config.data.datasets[0].data = return_val.suggesting;
                chart.config.data.datasets[1].data = return_val.super_competition;
                chart.config.data.datasets[2].data = return_val.minimum_price;
                chart.config.data.datasets[3].data = return_val.maximum_price;
                chart.update();
            }
            console.log(chart)



            //    code here

            /*
            * À, ông dùng cái gì để định danh cái product cho vẽ graph. id man
            * product id à.id trong db man, làm sao ông determine nó. Nó coó phải 1 cái field nào k, lay tren url man.
            * Show tui coi thử. OK, hiểu
            * Dùng this._rpc({}) Đẻ gọi về backend cho lẹ
            * Example
            * .then(function(result) {
            self.do_action(result);
            * Còn chỗ nào thắc mắc k. nhieefu lam man ei :3
            * Để tôi demo thử cái cho ông coi nhé
            * upgrade model dio9 ông
            * nếu ông muốn lấy id, dùng this.value
            * Load lâu thế ông ôi :V Ông ghi  data vào table nào đó.
            *
            let return_val = await this._rpc({
                 route: `/info/ebay_listing_item/${this.value}?group_by=${group_by}`,
            params: {
                iban: sepa_data.iban,
            }
            }).then(()=>{

            })
            * ebay_listing,  có model k. dài thế
        });
            * */
        }
    });

    field_registry.add('basic_graph', basisGraph);
    return {
        basisGraph: basisGraph,
    };
})