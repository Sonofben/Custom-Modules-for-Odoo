from odoo import models, fields, api

class Wallet(models.Model):
    _name = 'wallet.system'
    _description = 'Customer Wallet'

    customer_id = fields.Many2one('res.partner', string='Customer', required=True)
    balance = fields.Float(string='Wallet Balance', default=0.0)
    last_transaction_date = fields.Datetime(string='Last Transaction', readonly=True)
    transaction_count = fields.Integer(string='Transaction Count', compute='_compute_transactions')

    @api.depends('customer_id')
    def _compute_transactions(self):
        for rec in self:
            rec.transaction_count = self.env['wallet.transaction'].search_count([('wallet_id', '=', rec.id)])

class WalletTransaction(models.Model):
    _name = 'wallet.transaction'
    _description = 'Wallet Transactions'

    wallet_id = fields.Many2one('wallet.system', string='Wallet')
    amount = fields.Float(string='Amount', required=True)
    type = fields.Selection([('credit', 'Credit'), ('debit', 'Debit')], string='Transaction Type', required=True)
    reference = fields.Char(string='Reference')
    date = fields.Datetime(string='Date', default=fields.Datetime.now)
    notes = fields.Text(string='Notes')

    @api.model
    def create(self, vals):
        record = super(WalletTransaction, self).create(vals)
        wallet = record.wallet_id
        if record.type == 'credit':
            wallet.balance += record.amount
        else:
            wallet.balance -= record.amount
        wallet.last_transaction_date = fields.Datetime.now()
        return record

