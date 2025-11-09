from odoo import models, fields

class PartnerWallet(models.Model):
    _inherit = 'res.partner'

    wallet_balance = fields.Float(string='Wallet Balance', default=0.0)

