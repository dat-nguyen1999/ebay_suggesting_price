# -*- coding: utf-8 -*-
{
    'name': "ebay suggest pricer v1.0", #tên module
    'summary': """ebay suggest pricer v1.0""",  #mô tả ngắn gọn module
    'description': """ebay suggest pricer ver 1.0""",  #mô tả chi tiết app module / tính năng
    'author': "tiendat",    # tác giả, bạn có thể để tên của bản thân -DAT
    'website': "https://tiendat.info",  #website chứa thêm thông tin của module
    'category': 'Uncategorized',    # loại module
    'version': '0.1',   # phiên bản app
    'depends': [    # dependcy của module mình sẽ phụ thuộc vào những app / module khác nào
        'base',"mail","sale_ebay",'web'
    ],
    'external_dependencies': {'python': ['ebaysdk']},
    'data': [
        'security/ir.model.access.csv',
        'views/importChartJS.xml',
        'views/history.xml',
        'views/competitions.xml',
        'views/suggesting_price.xml',
        'views/rules.xml',
        'views/ebay_settings.xml',
        'views/menuItem.xml',
    ], # liên quan đến view, các file xml
    'qweb': ['static/src/xml/hello_world.xml'],
    'installable': True,    # cài đặt được
    'application': True,    # khi vào menu Apps, mặc định filter "Apps" sẽ được dùng.
}