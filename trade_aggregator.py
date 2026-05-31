from load_trades import load_trades_from_json, TradeCommodityType, TradeBook, Trade
import pandas as pd
from dataclasses import dataclass
import numpy as np
from price_providers import PriceProvider, StaticPriceProvider, CsvPriceProvider
import datetime

@dataclass(frozen=True, slots=True)
class TradePositionAggregation:
    book: TradeBook
    commodity: TradeCommodityType
    delivery_period: str
    net_position: float
    trade_count: int
    total_cost: float
    average_price: float


@dataclass(frozen=True, slots=True)
class DeltaExposure:
    commodity: TradeCommodityType
    delivery_period: str
    delta_exposure: float

@dataclass(frozen=True, slots=True)
class HedgeCoverage:
    commodity: TradeCommodityType
    delivery_period: str
    hedge_coverage: float

@dataclass(frozen=True)
class PnLResult:
    pnl: float
    timestamp: datetime.datetime | None = None

def trades_to_df(trade_list: list[Trade])->pd.DataFrame:

    df = pd.DataFrame([
        {'book' : t.book,
        'commodity' : t.commodity,
        'delivery_period': t.delivery_period,
        'signed_qty': t.signed_quantity,
        'price': t.price,
        'cost': t.price*t.signed_quantity} 
        for t in trade_list])

    return df

def aggregate_trades(trade_list: list[Trade])->pd.DataFrame:
    trade_df = trades_to_df(trade_list)

    aggregated_trades = trade_df.groupby(
        ['book', 'commodity', 'delivery_period']
    ).agg(
        net_position=('signed_qty', 'sum'),
        trade_count=('signed_qty', 'count'),
        total_cost=('cost', 'sum')
    ).reset_index()
    
    aggregated_trades['avg_price'] = (
        aggregated_trades['total_cost'] / aggregated_trades['net_position']
    ).replace([float('inf'), -float('inf')], None)

    return aggregated_trades


def position_aggregations(trade_list: list[Trade])->list[TradePositionAggregation]:
    
    if not trade_list:
        return []
    aggregated_trades = aggregate_trades(trade_list)
    
    position_aggregations=[]
    
    for row in aggregated_trades.itertuples():
        position_aggregations.append(
            TradePositionAggregation(
                book=row.book,
                commodity=row.commodity,
                delivery_period=row.delivery_period,
                net_position=row.net_position,
                trade_count=row.trade_count,
                total_cost=row.total_cost,
                average_price=row.avg_price
            )
        )
    return position_aggregations

def delta_exposure(trade_list: list[Trade])->list[DeltaExposure]:
    if not trade_list:
        return []
    
    aggregated_trades = aggregate_trades(trade_list)
    delta_df = aggregated_trades.pivot_table( index=["commodity", "delivery_period"], columns="book",
    values="net_position",
    fill_value=0, ).reset_index()
    delta_df["delta"] = (
    delta_df.get("physical", 0) + delta_df.get("hedge", 0)
    )
    delta_exposures=[]
    for row in delta_df.itertuples():
        delta_exposures.append(
            DeltaExposure(
                commodity=row.commodity,
                delivery_period=row.delivery_period,
                delta_exposure=row.delta)
        )
    return delta_exposures
    
def hedge_coverage(trade_list:list[Trade])->list[HedgeCoverage]:
    if not trade_list:
        return []
    aggregated_trades = aggregate_trades(trade_list)
    coverage_df = aggregated_trades.pivot_table( index=["commodity", "delivery_period"], columns="book",
    values="net_position",
    fill_value=0, ).reset_index()
    coverage_df["hedge_coverage"] = (
    100*np.abs(coverage_df.get("hedge", 0))/np.abs(coverage_df.get("physical", 0))
    )
    hedge_coverages=[]
    for row in coverage_df.itertuples():
        hedge_coverages.append(
            HedgeCoverage(
                commodity=row.commodity,
                delivery_period=row.delivery_period,
                hedge_coverage=row.hedge_coverage)
        )
    return hedge_coverages

def find_p_n_l(aggregated_trade:TradePositionAggregation,
    price_provider:PriceProvider,
    return_timestamp: bool = False,
)->float| tuple[float, datetime.datetime]:
    ''' calculate current PnL on netted trade'''
    if aggregated_trade.net_position == 0 or aggregated_trade.average_price is None:
        pnl = 0.0
    else:
        pnl = (price_provider.get_price(aggregated_trade.commodity, aggregated_trade.delivery_period)-aggregated_trade.average_price)*aggregated_trade.net_position
    if return_timestamp is True:
        return (pnl,datetime.datetime.now())
    return pnl
    
def print_position_aggregations(aggregated_trades: list[TradePositionAggregation])->None:
    print('\n')
    header = f"{'Book':<15} {'Commodity':<15} {'Delivery Period':<20} {'Net Position':>15} {'Trade Count':>12} {'Total Cost':>15}"
    print(header)
    print('-' * len(header))
    for t in aggregated_trades:
        print(f"{t.book:<15} {t.commodity:<15} {t.delivery_period:<20} {t.net_position:>15.2f} {t.trade_count:>12} {t.total_cost:>15.2f}") 
    

def print_delta_exposures(deltas: list[DeltaExposure])->None:
    print('\n')
    header = f"{'Commodity':<15} {'Delivery Period':<20} {'Delta Exposure':>15}"
    print(header)
    print('-' * len(header))
    for d in deltas:
        print(f"{d.commodity:<15} {d.delivery_period:<20} {d.delta_exposure:>15.2f}")
    

def print_hedge_coverages(hedge_coverages: list[HedgeCoverage])->None:
    print('\n')
    header = f"{'Commodity':<15} {'Delivery Period':<20} {'Hedge Coverage':>15}"
    print(header)
    print('-' * len(header))
    for h in hedge_coverages:
        print(f"{h.commodity:<15} {h.delivery_period:<20} {h.hedge_coverage:>15.2f}")

def print_p_and_l(aggregated_trades:list[TradePositionAggregation],
                  price_provider:PriceProvider)->None:
    if not aggregated_trades:
        print("No positions to display.")
        return
    
    print('\n')
    header = f"{'Book':<15} {'Commodity':<15} {'Delivery Period':<20} {'Net Position':>15} {'Avg. Price':>15} {'Mkt. Price':>15} {'Unrealised PnL':>15}"
    print(header)
    print('-' * len(header))
    
    for t in aggregated_trades:
        market_price = price_provider.get_price(t.commodity, t.delivery_period) 
        mtm_pl = (market_price-t.average_price)*t.net_position
        print(f"{t.book:<15} {t.commodity:<15} {t.delivery_period:<20} {t.net_position:>15.2f} {t.average_price:>15.2f} {market_price:>15.2f} {mtm_pl:>15.2f}")
    

if __name__ == '__main__':
    trade_list = load_trades_from_json(r'tests/data/empty_trades.json')
    aggregated_trades = position_aggregations(trade_list)
    # print_position_aggregations(aggregated_trades)
    # csv_prices = CsvPriceProvider(r'dummy_price.csv')
    static_prices = StaticPriceProvider ({
                                    ("nbp_gas", "2026-01") : 27.00 ,
                                    ("nbp_gas", "2026-02") : 26.00 ,
                                    })
    print_p_and_l(aggregated_trades, static_prices)
    # sp = StaticPriceProvider({
    #     ("nbp_gas", "2026-01"): 27.00,
    #     ("nbp_gas", "2026-02"): 26.00,
    # })
    #sp.get_price('nbp_gas', '2026-03')
    # trade_list = load_trades_from_json(r'/Users/tomrihoy/Desktop/ETRM Course/position-engine/tests/data/empty_trades.json')
    # aggregated_trades = position_aggregations(trade_list)
    # deltas = delta_exposure(trade_list)
    # hedge_coverages = hedge_coverage(trade_list)

    # print_delta_exposures(deltas)

    # print_hedge_coverages(hedge_coverages)

    # print_position_aggregations(aggregated_trades)
    



    
 

