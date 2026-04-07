import json
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class TradeCommodityType(StrEnum):
    NBP_GAS = 'nbp_gas'
    TTF_GAS = 'ttf_gas'

class TradeBook(StrEnum):
    PHYSICAL = 'physical'
    HEDGE='hedge'

class TradeAction(StrEnum):
    BUY='buy'
    SELL='sell'

@dataclass(frozen=True, slots=True)
class Trade:
    trade_id: str
    book: TradeBook
    commodity: TradeCommodityType
    delivery_period: str
    action: TradeAction
    quantity_mwh: float
    price: float

    @property
    def signed_quantity(self)->float:
        if self.action==TradeAction.BUY:
            return self.quantity_mwh
        return -self.quantity_mwh

def trade_from_dict(data: dict) -> Trade:
    return Trade(
        trade_id=str(data["trade_id"]),
        book=TradeBook(data["book"]),
        commodity=TradeCommodityType(data["commodity"]),
        delivery_period=data["delivery_period"],
        action=TradeAction(data["action"]),
        quantity_mwh=float(data["quantity_mwh"]),
        price=float(data["price"]),
    )

def load_trades_from_json(filepath: str | Path) -> list[Trade]:
    with open(filepath) as f:
        raw = json.load(f)
    return [trade_from_dict(trade) for trade in raw]

def print_trades(trade_list: list[Trade]):
    for trade in trade_list:
        print('---------------------\n'
        f'Trade ID: {trade.trade_id}\n'
        f'Book: {trade.book}\n'
        f'Commodity type: {trade.commodity}\n'
        f'Delivery period: {trade.delivery_period}\n'
        f'Action: {trade.action}\n'
        f'Quantity (MWh): {trade.quantity_mwh}\n'
        f'Price: {trade.price}\n'
        f'Signed qty: {trade.signed_quantity}\n'
        '---------------------\n'
        )


if __name__=='__main__':
    trades = load_trades_from_json('trades.json')
    print_trades(trades)


