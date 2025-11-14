from odoo.tests.common import TransactionCase

class TestWalletTransaction(TransactionCase):

    def setUp(self):
        super(TestWalletTransaction, self).setUp()
        # Create a test partner
        self.test_partner = self.env['res.partner'].create({
            'name': 'Test Wallet User',
            'email': 'test@example.com',
            'wallet_balance': 100.00,
        })
        # Ensure the sequence is created (if not already in data/sequence.xml)
        # The sequence is now created in data/wallet_data.xml, but we ensure it exists for isolated testing
        self.env['ir.sequence'].create({
            'name': 'Wallet Transaction Reference',
            'code': 'wallet_online.tx.seq',
            'prefix': 'WTX',
            'padding': 6,
        })

    def test_01_transaction_creation_pending(self):
        """Test transaction creation with pending status does not affect balance."""
        initial_balance = self.test_partner.wallet_balance
        
        tx = self.env['wallet.transaction'].create({
            'partner_id': self.test_partner.id,
            'amount': 50.00,
            'tx_type': 'fund',
            'status': 'pending',
            'reference': 'TEST_PENDING_001',
        })
        
        self.assertEqual(tx.status, 'pending', "Transaction status should be 'pending'")
        self.assertEqual(self.test_partner.wallet_balance, initial_balance, "Balance should not change for pending transaction")
        self.assertFalse(tx.is_applied, "Transaction should not be applied")

    def test_02_transaction_apply_funding_correctly(self):
        """Test applying funding updates the partner balance and is marked as applied."""
        initial_balance = self.test_partner.wallet_balance # 100.00
        fund_amount = 75.50
        
        # 1. Create a pending transaction (simulating controller logic)
        tx = self.env['wallet.transaction'].create({
            'partner_id': self.test_partner.id,
            'amount': fund_amount,
            'tx_type': 'fund',
            'status': 'pending',
            'reference': 'TEST_DONE_001',
        })
        
        # 2. Simulate webhook confirmation by updating status and calling _apply_funding
        tx.write({'status': 'done'})
        tx._apply_funding()
        
        # Reload partner to get updated balance
        self.test_partner.invalidate_cache()
        self.test_partner.refresh()
        
        expected_balance = initial_balance + fund_amount
        self.assertEqual(tx.status, 'done', "Transaction status should be 'done'")
        self.assertTrue(tx.is_applied, "Transaction should be marked as applied")
        self.assertAlmostEqual(self.test_partner.wallet_balance, expected_balance, 2, "Partner balance was not updated correctly")

    def test_03_transaction_apply_funding_idempotency(self):
        """Test that calling _apply_funding twice does not double-credit (idempotency)."""
        initial_balance = self.test_partner.wallet_balance # 100.00
        fund_amount = 20.00
        
        # 1. Create a pending transaction
        tx = self.env['wallet.transaction'].create({
            'partner_id': self.test_partner.id,
            'amount': fund_amount,
            'tx_type': 'fund',
            'status': 'pending',
            'reference': 'TEST_IDEMPOTENT_001',
        })
        
        # 2. Apply funding (first time)
        tx.write({'status': 'done'})
        tx._apply_funding()
        
        # Check balance after first application
        self.test_partner.invalidate_cache()
        self.test_partner.refresh()
        expected_balance = initial_balance + fund_amount
        self.assertAlmostEqual(self.test_partner.wallet_balance, expected_balance, 2, "Balance not updated after first apply")
        
        # 3. Apply funding (second time - should be skipped due to is_applied=True)
        tx._apply_funding()
        
        # Check balance after second application
        self.test_partner.invalidate_cache()
        self.test_partner.refresh()
        
        # The balance should remain the same as after the first application
        self.assertAlmostEqual(self.test_partner.wallet_balance, expected_balance, 2, "Balance should not change after second apply (Idempotency Check)")
        self.assertTrue(tx.is_applied, "Transaction should remain marked as applied")
