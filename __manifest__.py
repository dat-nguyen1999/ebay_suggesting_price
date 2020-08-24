# -*- coding: utf-8 -*-
{
    'name': "ebay suggesting pricer v1.0", #tên module
    'summary': """ebay suggesting repricer v1.0""",  #mô tả ngắn gọn module
    'description': """ebay suggesting repricer ver 1.0""",  #mô tả chi tiết app module / tính năng
    'author': "tiendat",    # tác giả, bạn có thể để tên của bản thân -DAT
    'website': "https://tiendat.info",  #website chứa thêm thông tin của module
    'category': 'Uncategorized',    # loại module
    'version': '0.1',   # phiên bản app
    'depends': [    # dependcy của module mình sẽ phụ thuộc vào những app / module khác nào
        'base',"mail"
    ],
    'external_dependencies': {'python': ['ebaysdk']},
    'data': [
        'security/ir.model.access.csv',
        'views/suggesting_price.xml',
        'views/rules.xml',
        'views/menuItem.xml',
    ], # liên quan đến view, các file xml
    # 'qweb': ['static/src/xml/*.xml'],
    'installable': True,    # cài đặt được
    'application': True,    # khi vào menu Apps, mặc định filter "Apps" sẽ được dùng.
}