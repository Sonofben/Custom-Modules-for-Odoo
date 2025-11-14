from odoo import http, fields
from odoo.http import request
import logging
import json
import requests

_logger = logging.getLogger(__name__)

# For quick setup you can keep the sandbox link, but in production you'll call Flutterwave to create a payment
ICPSudo = request.env['ir.config_parameter'].sudo()
FLW_DIRECT_LINK = ICPSudo.get_param('wallet_online_funding.flw_direct_link')
FLW_SECRET_KEY = ICPSudo.get_param('wallet_online_funding.flw_secret_key')
FLW_SECRET_HASH = ICPSudo.get_param('wallet_online_funding.flw_secret_hash')
# Put secret in ir.config_parameter in production:
# FLW_SECRET_KEY is now fetched from ir.config_parameter

class WalletOnlineFundingController(http.Controller):

    @http.route(['/wallet/fund'], type='http', auth='public', website=True)
    def wallet_fund_form(self, **kw):
        return request.render('wallet_online_funding.wallet_fund_template', {})

    @http.route(['/wallet/fund/submit'], type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def wallet_fund_submit(self, **post):
        email = post.get('email')
        phone = post.get('phone')
        try:
            amount = float(post.get('amount', 0))
        except Exception:
            amount = 0.0

        if not email and not phone:
            return request.render('wallet_online_funding.wallet_error_template', {'message': 'Provide email or phone'})

        if amount <= 0:
            return request.render('wallet_online_funding.wallet_error_template', {'message': 'Provide a valid amount'})

        # find or create partner
        Partner = request.env['res.partner'].sudo()
        partner = None
        
        # 1. Try to find logged-in user's partner
        if request.env.user.partner_id.id != request.env.ref('base.public_partner').id:
            partner = request.env.user.partner_id
        
        # 2. If not logged in, search by email/phone
        if not partner:
            domain = []
            if email:
                domain.append(('email', '=', email))
            if phone:
                domain.append(('phone', '=', phone))
            
            if domain:
                partner = Partner.search(domain, limit=1)
        
        # 3. Create if not found
        if not partner:
            partner = Partner.create({
                'name': email or phone or 'Customer', 
                'email': email or False, 
                'phone': phone or False, 
                'customer_rank': 1
            })

        # create transaction (pending)
        seq = request.env['ir.sequence'].sudo().next_by_code('wallet_online.tx.seq') or str(partner.id)
        tx_ref = f"WALLET_{partner.id}_{seq}"
        tx = request.env['wallet.transaction'].sudo().create({
            'partner_id': partner.id,
            'amount': amount,
            'tx_type': 'fund',
            'reference': tx_ref,
            'provider': 'flutterwave',
            'status': 'pending',
        })

        # For quick test we redirect to a static sandbox link; in production create a payment session via Flutterwave API
        # We include tx_ref in the redirect if possible (some payment links may support query params)
        redirect_url = FLW_DIRECT_LINK
        if '?' in redirect_url:
            redirect_url = f"{redirect_url}&tx_ref={tx_ref}&amount={amount}&email={partner.email or ''}"
        else:
            redirect_url = f"{redirect_url}?tx_ref={tx_ref}&amount={amount}&email={partner.email or ''}"

        return request.redirect(redirect_url)

    @http.route(['/wallet/flutterwave/webhook'], type='json', auth='public', csrf=False, methods=['POST'])
    def flutterwave_webhook(self, **post):
        """Accept webhook POST from Flutterwave. Expects JSON payload."""
        try:
            data = request.httprequest.get_json(force=True)
        except Exception:
            data = post or {}
        _logger.info("Flutterwave webhook payload: %s", data)

        # Flutterwave payload keys may differ — adapt here
        tx_ref = data.get('tx_ref') or (data.get('data') or {}).get('tx_ref') or data.get('reference')
        status = (data.get('status') or (data.get('data') or {}).get('status') or '').lower()
        amount = None
        try:
            amount = float((data.get('amount') or (data.get('data') or {}).get('amount') or 0) or 0)
        except Exception:
            amount = 0.0

        if not tx_ref:
            _logger.warning("Webhook without tx_ref: %s", data)
            return {'status':'error', 'message':'Missing tx_ref'}

        # find transaction
        tx = request.env['wallet.transaction'].sudo().search([('reference','=',tx_ref)], limit=1)
        if not tx:
            _logger.warning("Transaction not found for tx_ref %s", tx_ref)
            return {'status':'error', 'message':'Transaction not found'}

        # verify with Flutterwave if possible (recommended)
        verified = False
        # 1. Webhook Signature Verification (CRITICAL SECURITY FIX)
        signature = request.httprequest.headers.get('verif-hash')
        if FLW_SECRET_HASH and signature != FLW_SECRET_HASH:
            _logger.error("Webhook signature mismatch. Expected %s, got %s", FLW_SECRET_HASH, signature)
            return {'status':'error', 'message':'Invalid signature'}

        # 2. Transaction Verification (Good Practice)
        verified = False
        if FLW_SECRET_KEY:
            try:
                headers = {'Authorization': f'Bearer {FLW_SECRET_KEY}'}
                verify_url = f'https://api.flutterwave.com/v3/transactions/verify_by_reference?tx_ref={tx_ref}'
                r = requests.get(verify_url, headers=headers, timeout=10)
                jr = r.json()
                if jr.get('status') == 'success' and jr.get('data'):
                    amount = float(jr['data'].get('amount') or amount or 0)
                    verified = True
            except Exception as e:
                _logger.warning("Flutterwave verify failed: %s", e)
        else:
            # no secret provided — we trust incoming webhook (fine for sandbox/testing)
            verified = (status == 'successful' or status == 'success')

        if not verified:
            tx.sudo().write({'status':'failed', 'note': 'Verification failed'})
            return {'status':'error', 'message':'Verification failed'}

        # mark transaction done and apply
        tx.sudo().write({'status':'done'})
        # call apply (now idempotent)
        try:
            tx._apply_funding()
        except Exception as e:
            _logger.exception("Failed to apply funding for tx %s: %s", tx_ref, e)
            return {'status':'error', 'message':str(e)}

        # send email notification
        try:
            template = request.env.ref('wallet_online_funding.wallet_funded_email_template', raise_if_not_found=False)
            if template and tx.partner_id.email:
                template.sudo().with_context(amount="%.2f" % tx.amount).send_mail(tx.partner_id.id, force_send=True)
        except Exception as e:
            _logger.warning("Failed to send email: %s", e)

        # Optionally send SMS here (integration is similar)
        return {'status':'success'}

