{
    'name': 'Car Wash Wallet Management',
    'version': '18.0.1.0.0',
    'category': 'Sales',
    'summary': 'Customer self-service wallet funding and management',
    'description': """
        Car Wash Wallet Management System
        ==================================
        * Allows customers to fund their wallets online
        * Integrates with payment gateways (Paystack/Flutterwave)
        * Sends SMS/Email notifications for transactions
        * Customer portal for wallet management
        * POS integration for wallet payments
    """,
    'author': 'Joseph Benson',
    'website': '',
    'depends': [
        'base',
        'sale',
        'portal',
        'payment',
        'point_of_sale',  # If you're using POS
    ],
    'data': [
        'security/wallet_security.xml',
        'security/ir.model.access.csv',
        'data/wallet_sequences.xml',
        'views/wallet_transaction_views.xml',
        'views/wallet_topup_views.xml',
        'views/res_partner_views.xml',
        'views/portal_templates.xml',
        'data/wallet_product_data.xml',
        'data/email_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'carwash_wallet/static/src/css/portal.css',
            'carwash_wallet/static/src/js/portal.js',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
