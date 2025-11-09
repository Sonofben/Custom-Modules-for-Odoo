# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError


class WalletTopup(models.Model):
    _name = 'wallet.topup'
    _description = 'Wallet Top-up Request'
    _order = 'create_date desc'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    
    name = fields.Char(
        string='Top-up Reference',
        required=True,
        copy=False,
        readonly=True,
        index=True,
        default=lambda self: self.env['ir.sequence'].next_by_code('wallet.topup') or 'New'
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True,
        default=lambda self: self.env.user.partner_id,
        readonly=True,
        states={'draft': [('readonly', False)]}
    )
    
    amount = fields.Monetary(
        string='Top-up Amount',
        currency_field='currency_id',
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]}
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='partner_id.currency_id',
        store=True
    )
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending Payment'),
        ('paid', 'Paid'),
        ('credited', 'Credited to Wallet'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', required=True, tracking=True)
    
    payment_transaction_id = fields.Many2one(
        'payment.transaction',
        string='Payment Transaction',
        readonly=True
    )
    
    wallet_transaction_id = fields.Many2one(
        'wallet.transaction',
        string='Wallet Transaction',
        readonly=True,
        help='Wallet transaction created when amount is credited'
    )
    
    payment_reference = fields.Char(
        string='Payment Reference',
        readonly=True,
        help='Reference from payment provider'
    )
    
    payment_date = fields.Datetime(
        string='Payment Date',
        readonly=True
    )
    
    notes = fields.Text(string='Notes')
    
    @api.model
    def create(self, vals):
        """Generate sequence for top-up reference"""
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('wallet.topup') or 'New'
        return super(WalletTopup, self).create(vals)
    
    def action_request_payment(self):
        """Generate payment link for customer"""
        self.ensure_one()
        
        if self.amount <= 0:
            raise UserError('Top-up amount must be greater than zero')
        
        self.state = 'pending'
        
        # Return action to payment page
        return {
            'type': 'ir.actions.act_url',
            'url': f'/my/wallet/topup/{self.id}/payment',
            'target': 'self',
        }
    
    def action_confirm_payment(self, payment_reference):
        """Confirm payment received from payment gateway"""
        self.ensure_one()
        
        if self.state != 'pending':
            raise UserError('Can only confirm payment for pending top-ups')
        
        self.write({
            'state': 'paid',
            'payment_reference': payment_reference,
            'payment_date': fields.Datetime.now()
        })
        
        # Credit the wallet
        self.action_credit_wallet()
    
    def action_credit_wallet(self):
        """Credit the amount to customer's wallet"""
        self.ensure_one()
        
        if self.state != 'paid':
            raise UserError('Payment must be confirmed before crediting wallet')
        
        # Add balance to customer wallet
        new_balance = self.partner_id.add_wallet_balance(
            amount=self.amount,
            reference=self.payment_reference or self.name,
            description=f'Wallet top-up via {self.name}'
        )
        
        # Link to the created wallet transaction
        wallet_transaction = self.env['wallet.transaction'].search([
            ('partner_id', '=', self.partner_id.id),
            ('reference', '=', self.payment_reference or self.name)
        ], limit=1)
        
        self.write({
            'state': 'credited',
            'wallet_transaction_id': wallet_transaction.id if wallet_transaction else False
        })
        
        return new_balance
    
    def action_cancel(self):
        """Cancel the top-up request"""
        self.ensure_one()
        
        if self.state == 'credited':
            raise UserError('Cannot cancel a top-up that has already been credited')
        
        self.state = 'cancelled'
    
    def _compute_access_url(self):
        """Compute portal URL for this record"""
        super(WalletTopup, self)._compute_access_url()
        for topup in self:
            topup.access_url = f'/my/wallet/topup/{topup.id}'
