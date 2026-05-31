from load_trades import Trade

# TRADE INGESTION:
def test_signed_qty_buy():
    trade = Trade(
        trade_id = 'TR-001',
        book = 'physical',
        commodity = 'nbp_gas',
        delivery_period='2026-01',
        action = 'buy',
        quantity_mwh='100',
        price='80'
    )
    assert trade.signed_quantity==100

def test_signed_quantity_sell():
    trade = Trade(
        trade_id = 'TR-002',
        book = 'physical',
        commodity = 'nbp_gas',
        delivery_period='2026-01',
        action = 'sell',
        quantity_mwh='100',
        price='80'
    )
    assert trade.signed_quantity==-100

# TRADE AGGREGATION: