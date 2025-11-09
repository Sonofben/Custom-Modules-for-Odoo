{
    'name': 'Wallet Online Funding',
    'version': '1.0',
    'summary': 'Public wallet funding + transaction log + integration with existing E-wallet',
    'author': 'Joseph Benson',
    'category': 'Website',
    'depends': ['base', 'contacts','payment', 'mail', 'website'],
    'data': [
        'data/mail_templates.xml',
        'views/wallet_templates.xml',
    ],
    'installable': True,
    'application': False,
}

