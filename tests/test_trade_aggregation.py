import pytest

from load_trades import load_trades_from_json
from price_providers import StaticPriceProvider
from trade_aggregator import delta_exposure, find_p_n_l, position_aggregations


@pytest.fixture
def trade_list():
    return load_trades_from_json("tests/data/trades.json")


@pytest.fixture
def aggregated_trades(trade_list):
    return position_aggregations(trade_list)


@pytest.fixture
def static_price_provider():
    return StaticPriceProvider(
        {
            ("nbp_gas", "2026-01"): 27.00,
            ("nbp_gas", "2026-02"): 26.00,
        }
    )


def test_average_price(aggregated_trades):

    trade_agg = next(
        (
            ta
            for ta in aggregated_trades
            if ta.delivery_period == "2026-01"
            and ta.book == "physical"
            and ta.commodity == "nbp_gas"
        ),
        None,
    )
    assert trade_agg.average_price == 23.50


def test_number_aggregated_trades(aggregated_trades):

    trade_agg = [
        ta
        for ta in aggregated_trades
        if ta.delivery_period == "2026-01"
        and ta.book == "physical"
        and ta.commodity == "nbp_gas"
    ]
    assert len(trade_agg) == 1


def test_delta_exposure(trade_list):

    deltas = delta_exposure(trade_list)
    trade_de = next(
        (
            de
            for de in deltas
            if de.delivery_period == "2026-01" and de.commodity == "nbp_gas"
        ),
        None,
    )
    assert trade_de.delta_exposure == 50


def test_position_aggregation(aggregated_trades):
    """Reference portfolio positions."""

    jan_phys = next(
        at
        for at in aggregated_trades
        if at.commodity == "nbp_gas"
        and at.delivery_period == "2026-01"
        and at.book == "physical"
    )
    assert jan_phys.net_position == 200.0


def test_pnl_total(aggregated_trades, static_price_provider):
    """Total unrealized P&L must be exactly +865."""

    total_pnl = 0
    for at in aggregated_trades:
        pnl = find_p_n_l(aggregated_trade=at, price_provider=static_price_provider)
        total_pnl += pnl
    assert total_pnl == 865.0
