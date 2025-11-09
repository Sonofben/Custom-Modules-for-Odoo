{
    'name': 'Customer Wallet System',
    'version': '1.0',
    'category': 'Website',
    'summary': 'Allow customers to manage wallet, top-up online, and use for payments',
    'author': 'Joseph Benson', 
    'depends': ['base', 'website', 'sale', 'mail'],
    'data': [
        'views/wallet_menu.xml',
        'views/wallet_template.xml',
        'views/wallet_view.xml',
        'data/mail_template.xml',
    ],
    'installable': True,
    'application': True,
}
