from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class ResPartnerWallet(models.Model):
    _inherit = 'res.partner'

    wallet_balance = fields.Float(string='Wallet Balance', default=0.0)


class WalletTransaction(models.Model):
    _name = 'wallet.transaction'
    _description = 'Wallet Transaction (online funding / spending)'

    partner_id = fields.Many2one('res.partner', string='Customer', required=True, ondelete='cascade')
    amount = fields.Float(string='Amount', required=True)
    tx_type = fields.Selection([('fund', 'Funding'), ('spend', 'Spending')], default='fund')
    reference = fields.Char(string='Reference', index=True)
    provider = fields.Char(string='Provider')  # e.g. 'flutterwave'
    status = fields.Selection([('pending','Pending'), ('done','Done'), ('failed','Failed')], default='pending')
    is_applied = fields.Boolean(string='Applied', default=False, readonly=True)
    date = fields.Datetime(string='Date', default=fields.Datetime.now)
    note = fields.Text(string='Notes')

    # Removed dangerous override of create. Funding should only be applied via webhook.

    def _apply_funding(self):
        """Update partner canonical balance. Ensures idempotency."""
        for rec in self:
            if rec.is_applied or rec.status != 'done':
                _logger.info("Skipping application for transaction %s (Applied: %s, Status: %s)", rec.reference, rec.is_applied, rec.status)
                continue

            partner = rec.partner_id
            
            # 1) update canonical partner.wallet_balance
            partner.sudo().write({'wallet_balance': partner.wallet_balance + rec.amount})

            # 2) Mark as applied to ensure idempotency
            rec.write({'is_applied': True})
            
            _logger.info("Applied funding of %s to partner %s. New balance: %s", rec.amount, partner.id, partner.wallet_balance)

            # NOTE: Removed brittle external wallet detection logic. 
            # If integration with a specific external wallet module is required, 
            # it should be done via a dedicated, explicit dependency and method override.

