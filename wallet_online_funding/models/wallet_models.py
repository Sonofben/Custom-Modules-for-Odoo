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
    date = fields.Datetime(string='Date', default=fields.Datetime.now)
    note = fields.Text(string='Notes')

    @api.model
    def create(self, vals):
        # Create the transaction record first
        rec = super().create(vals)
        # If it's a funding and marked done, update balances
        try:
            if rec.tx_type == 'fund' and rec.status == 'done':
                rec._apply_funding()
        except Exception as e:
            _logger.exception("Error applying funding on create: %s", e)
        return rec

    def _apply_funding(self):
        """Update partner canonical balance and attempt to update external e-wallet model if present."""
        for rec in self:
            partner = rec.partner_id
            # 1) update canonical partner.wallet_balance
            partner.sudo().write({'wallet_balance': partner.wallet_balance + rec.amount})

            # 2) try to detect and update external e-wallet model (if any)
            # Candidate model names to attempt - common naming variations
            candidates = [
                'wallet.system', 'ewallet.wallet', 'pos.wallet', 'gift.card', 'sale.gift.card',
                'e_wallet', 'res.e_wallet', 'pos_ewallet.ewallet'
            ]
            for model_name in candidates:
                try:
                    # Try to obtain the model proxy
                    Model = self.env[model_name]
                except Exception:
                    Model = None
                if not Model:
                    continue

                # Try common partner field names
                partner_fields = ['partner_id', 'partner', 'customer_id', 'owner_id']
                balance_fields = ['balance', 'wallet_balance', 'amount', 'value']

                # Find the external wallet record for this partner
                ext_wallet = None
                for pf in partner_fields:
                    try:
                        ext_wallet = Model.sudo().search([(pf, '=', partner.id)], limit=1)
                        if ext_wallet:
                            break
                    except Exception:
                        ext_wallet = None

                # If found, try to update its balance field or call its API method
                if ext_wallet:
                    updated = False
                    for bf in balance_fields:
                        if bf in ext_wallet._fields:
                            try:
                                # increment the external balance
                                newbal = (ext_wallet[b f] if False else 0)  # placeholder to satisfy static analysis
                            except Exception:
                                newbal = None
                            try:
                                # safer: read current value using getattr
                                cur = float(ext_wallet[bf]) if ext_wallet[bf] is not None else 0.0
                                ext_wallet.sudo().write({bf: cur + rec.amount})
                                updated = True
                                _logger.info("Updated external wallet model %s field %s for partner %s", model_name, bf, partner.id)
                                break
                            except Exception as e:
                                _logger.warning("Could not update field %s on %s: %s", bf, model_name, e)
                    # If model exposes 'credit' or 'add_balance' methods, try calling them
                    if not updated:
                        for method_name in ['credit', 'add_balance', 'increase_balance']:
                            if hasattr(ext_wallet, method_name):
                                try:
                                    getattr(ext_wallet, method_name)(rec.amount)
                                    updated = True
                                    _logger.info("Called %s on %s for partner %s", method_name, model_name, partner.id)
                                    break
                                except Exception as e:
                                    _logger.warning("Method %s failed on %s: %s", method_name, model_name, e)

                    # if we managed to update one external wallet, stop searching
                    if updated:
                        break

            # done: partner.wallet_balance already updated

