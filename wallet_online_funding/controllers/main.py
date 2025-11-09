from odoo import http
from odoo.http import request
import json
import logging

_logger = logging.getLogger(__name__)

class WalletFundingController(http.Controller):

    @http.route('/wallet/fund', type='http', auth='public', website=True)
    def wallet_fund_form(self, **kw):
        """Simple form for customers to fund wallet"""
        html_form = """
            <html>
            <body style="text-align:center; margin-top:50px;">
                <h2>Fund Your Wallet</h2>
                <form action="https://sandbox.flutterwave.com/pay/9dowbcfw1iwt" method="GET">
                    <label>Email:</label><br>
                    <input type="email" name="email" required/><br><br>
                    <label>Phone:</label><br>
                    <input type="text" name="phone" required/><br><br>
                    <label>Amount:</label><br>
                    <input type="number" name="amount" required/><br><br>
                    <input type="submit" value="Proceed to Pay" style="padding:10px 20px;"/>
                </form>
            </body>
            </html>
        """
        return html_form


    @http.route('/wallet/flutterwave/callback', type='json', auth='public', methods=['POST'], csrf=False)
    def flutterwave_callback(self, **kwargs):
        """Receive webhook from Flutterwave after payment"""
        try:
            data = json.loads(request.httprequest.data)
            _logger.info("Flutterwave Webhook Data: %s", data)

            # Confirm successful transaction
            if data.get('status') == 'successful':
                email = data.get('customer', {}).get('email')
                phone = data.get('customer', {}).get('phone_number')
                amount = float(data.get('amount', 0.0))

                if not amount:
                    _logger.warning("No amount received in webhook")
                    return {"status": "error", "message": "Invalid amount"}

                # Find customer by email or phone
                partner = None
                if email:
                    partner = request.env['res.partner'].sudo().search([('email', '=', email)], limit=1)
                if not partner and phone:
                    partner = request.env['res.partner'].sudo().search([('phone', '=', phone)], limit=1)

                if not partner:
                    _logger.warning("No partner found for email %s or phone %s", email, phone)
                    return {"status": "error", "message": "Customer not found"}

                # Update wallet balance (assuming eWallet is stored in partner)
                new_balance = partner.wallet_balance + amount
                partner.sudo().write({'wallet_balance': new_balance})

                # Send notification email
                request.env['mail.mail'].sudo().create({
                    'subject': 'Wallet Funded Successfully',
                    'email_to': partner.email,
                    'body_html': f"""
                        <p>Hello {partner.name},</p>
                        <p>Your wallet has been funded with <b>₦{amount:,.2f}</b>.</p>
                        <p>New balance: <b>₦{new_balance:,.2f}</b></p>
                        <p>Thank you for your patronage.</p>
                    """
                }).send()

                _logger.info("Wallet credited successfully for partner %s", partner.name)
                return {"status": "success"}

            else:
                _logger.warning("Unsuccessful payment callback received")
                return {"status": "error", "message": "Payment not successful"}

        except Exception as e:
            _logger.error("Flutterwave Callback Error: %s", str(e))
            return {"status": "error", "message": str(e)}

