from rich.console import Console
from rich.table import Table
import typer
from enum import StrEnum
import json

from load_trades import load_trades_from_json, TradeCommodityType, TradeBook, Trade
import pandas as pd
from dataclasses import dataclass
import numpy as np
from price_providers import PriceProvider, StaticPriceProvider, CsvPriceProvider
from trade_aggregator import position_aggregations, hedge_coverage, delta_exposure

class PriceSource(StrEnum):
    CSV='csv'
    STATIC='static'

class OutputFormat(StrEnum):
    CSV='csv'
    TERMINAL='terminal'

app = typer.Typer()
console=Console()

def position_aggregations_to_df(aggregated_trades):
    return pd.DataFrame([
        {
            "Book": p.book,
            "Commodity": p.commodity,
            "Delivery Period": p.delivery_period,
            "Net Position": p.net_position,
            "Trade Count": p.trade_count,
            "Total Cost": p.total_cost,
            "Avg Price": p.average_price,
        }
        for p in aggregated_trades
    ])


@app.command()
def show_position_aggregations(
    path: str = typer.Argument(..., help='Path to trade file'),
    output_format: OutputFormat = typer.Option('terminal', help ='Report output format')
):
    trade_list = load_trades_from_json(path)
    aggregated_trades = position_aggregations(trade_list)
    df = position_aggregations_to_df(aggregated_trades)

    if output_format == OutputFormat.CSV:
        df.to_csv("report.csv", index=False)
    else:
        table = Table(title='Position Aggregations')
        table.add_column("Book", style='cyan')
        table.add_column("Commodity", style='cyan')
        table.add_column("Delivery Period", style='cyan')
        table.add_column("Net Position", style='cyan')

        for _, row in df.iterrows():
            style = 'green' if row["Net Position"] > 0 else "red"
            table.add_row(
                str(row["Book"]),
                str(row["Commodity"]),
                str(row["Delivery Period"]),
                f"{row['Net Position']:+,.0f} MWh",
                style=style,
            )

        console.print(table)

@app.command()
def show_hedge_coverages(
    path: str = typer.Argument(..., help='Path to trade file'),
):
    trade_list = load_trades_from_json(path)
    hedge_coverages = hedge_coverage(trade_list)
    
    table=Table(title='Hedge Coveraages')
    table.add_column("Commodity", style='cyan')
    table.add_column("Delivery Period", style='cyan')
    table.add_column("Hedge Coverage", style='cyan')

    for hc in hedge_coverages:
        table.add_row(
            hc.commodity,
            hc.delivery_period,
            f"{hc.hedge_coverage:.0f}%",
        )
    console.print(table)

@app.command()
def show_delta_exposures(
    path: str = typer.Argument(..., help='Path to trade file')
):
    trade_list = load_trades_from_json(path)
    deltas = delta_exposure(trade_list)
    table=Table(title='Position Aggregations')
    table.add_column("Commodity", style='cyan')
    table.add_column("Delivery Period", style='cyan')
    table.add_column("Delta Exposure", style='cyan')

    for d in deltas:
        style = 'green' if d.delta_exposure > 0 else "red"
        table.add_row(
            d.commodity,
            d.delivery_period,
            f"{d.delta_exposure:+,.0f} MWh",
            style=style,
        )
    console.print(table)


@app.command()
def show_p_and_l(
    trade_path: str = typer.Argument(..., help='Path to trade file'),
    price_source: PriceSource = typer.Argument(..., help='Source for market prices'),
    price_path: str| None = typer.Option(None, help="Path to market price file"),
    static_prices: str| None = typer.Option(None, 
                                            help='Feed static prices, format: \'{"commodity|delivery_period": price, ...}\'')
):
    trade_list = load_trades_from_json(trade_path)
    aggregated_trades = position_aggregations(trade_list)
    
    if price_source == "static":
        import json

        price_dict = {
            tuple(k.split("|")): v
            for k, v in json.loads(static_prices).items()
        }

        price_provider = StaticPriceProvider(price_dict)

    if price_source == "csv":
        price_provider = CsvPriceProvider(price_path)
    
    table = Table(title= 'PnL')
    table.add_column("Book")
    table.add_column("Commodity")
    table.add_column("Delivery Period")
    table.add_column("Net Position")
    table.add_column("Average Price")
    table.add_column("Market Price")
    table.add_column("MtM PnL")

    for pos in aggregated_trades:
        market_price = price_provider.get_price(pos.commodity, pos.delivery_period)
        mtm_pnl = (market_price-pos.average_price)*pos.net_position
        style = "green" if mtm_pnl > 0 else "red"
        table.add_row(
            pos.book,
            pos.commodity,
            pos.delivery_period,
            f"{pos.net_position:+,.0f} MWh",
            f"£{pos.average_price:+,.2f}/MWh",
            f"£{market_price:+,.2f}/MWh",
            f"£{mtm_pnl:+,.2f}",
            style=style,
        )
    console.print(table)



if __name__ == "__main__":
    app()


