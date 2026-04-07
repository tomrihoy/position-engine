from load_trades import load_trades_from_json, TradeCommodityType, TradeBook, Trade
import pandas as pd
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class TradePositionAggregation:
    book: TradeBook
    commodity: TradeCommodityType
    delivery_period: str
    net_position: float
    trade_count: int
    total_cost: float

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

def aggregate_trades(trade_list: list[Trade])->list[TradePositionAggregation]:
    trade_df = trades_to_df(trade_list)

    aggregated_trades = trade_df.groupby(
        ['book', 'commodity', 'delivery_period']
    ).agg(
        net_position=('signed_qty', 'sum'),
        trade_count=('signed_qty', 'count'),
        total_cost=('cost', 'sum')
    ).reset_index()
    
    position_aggregations=[]
    
    for row in aggregated_trades.itertuples():
        position_aggregations.append(
            TradePositionAggregation(
                book=row.book,
                commodity=row.commodity,
                delivery_period=row.delivery_period,
                net_position=row.net_position,
                trade_count=row.trade_count,
                total_cost=row.total_cost
            )
        )
    return position_aggregations

if __name__ == '__main__':
    trade_list = load_trades_from_json(r'trades.json')
    aggregated_trades = aggregate_trades(trade_list)
    
    header = f"{'Book':<15} {'Commodity':<15} {'Delivery Period':<20} {'Net Position':>15} {'Trade Count':>12} {'Total Cost':>15}"
    print(header)
    print('-' * len(header))
    
    for t in aggregated_trades:
        print(f"{t.book:<15} {t.commodity:<15} {t.delivery_period:<20} {t.net_position:>15.2f} {t.trade_count:>12} {t.total_cost:>15.2f}") 

