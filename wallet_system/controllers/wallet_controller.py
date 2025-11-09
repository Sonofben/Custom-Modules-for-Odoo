from odoo import http
from odoo.http import request

class WalletController(http.Controller):

    @http.route(['/wallet'], type='http', auth='user', website=True)
    def wallet_page(self, **kw):
        customer = request.env.user.partner_id
        wallet = request.env['wallet.system'].sudo().search([('customer_id', '=', customer.id)], limit=1)
        if not wallet:
            wallet = request.env['wallet.system'].sudo().create({'customer_id': customer.id})
        transactions = request.env['wallet.transaction'].sudo().search([('wallet_id', '=', wallet.id)], order='date desc')
        return request.render('wallet_system.wallet_page_template', {
            'wallet': wallet,
            'transactions': transactions,
        })

