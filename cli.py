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

@app.command()
def show_position_aggregations(
    path: str = typer.Argument(..., help="Path to trade file"),
    output_format: OutputFormat = typer.Option(
        OutputFormat.TERMINAL,
        help="Report output format"
    )
):
    trade_list = load_trades_from_json(path)
    aggregated_trades = position_aggregations(trade_list)

    # Build DataFrame directly
    df = pd.DataFrame([
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

    # CSV output
    if output_format == OutputFormat.CSV:
        df.to_csv("position_report.csv", index=False)
        console.print("[green]Saved position_report.csv[/green]")
        return

    # Terminal output
    table = Table(title="Position Report")

    table.add_column("Book", style="cyan")
    table.add_column("Commodity", style="cyan")
    table.add_column("Delivery Period", style="cyan")
    table.add_column("Net Position", justify="right")
    table.add_column("Trade Count", justify="right")
    table.add_column("Total Cost", justify="right")
    table.add_column("Avg Price", justify="right")

    for _, row in df.iterrows():

        style = "green" if row["Net Position"] > 0 else "red"

        table.add_row(
            str(row["Book"]),
            str(row["Commodity"]),
            str(row["Delivery Period"]),
            f"{row['Net Position']:+,.0f} MWh",
            f"{row['Trade Count']}",
            f"£{row['Total Cost']:,.2f}",
            f"£{row['Avg Price']:,.2f}/MWh",
            style=style,
        )

    console.print(table)

@app.command()
def show_risk_report(
    path: str = typer.Argument(..., help="Path to trade file"),
    output_format: OutputFormat = typer.Option(
        OutputFormat.TERMINAL,
        help="Report output format"
    )
):
    trade_list = load_trades_from_json(path)

    # Get outputs
    deltas = delta_exposure(trade_list)
    hedge_coverages = hedge_coverage(trade_list)

    # Convert to DataFrames
    delta_df = pd.DataFrame([
        {
            "Commodity": d.commodity,
            "Delivery Period": d.delivery_period,
            "Delta Exposure": d.delta_exposure,
        }
        for d in deltas
    ])

    hedge_df = pd.DataFrame([
        {
            "Commodity": h.commodity,
            "Delivery Period": h.delivery_period,
            "Hedge Coverage": h.hedge_coverage,
        }
        for h in hedge_coverages
    ])

    # Merge reports
    report_df = pd.merge(
        delta_df,
        hedge_df,
        on=["Commodity", "Delivery Period"],
        how="outer"
    )

    # CSV output
    if output_format == OutputFormat.CSV:
        report_df.to_csv("risk_report.csv", index=False)
        console.print("[green]Saved risk_report.csv[/green]")
        return

    # Terminal output
    table = Table(title="Risk Report")

    table.add_column("Commodity", style="cyan")
    table.add_column("Delivery Period", style="cyan")
    table.add_column("Delta Exposure", justify="right")
    table.add_column("Hedge Coverage", justify="right")

    for _, row in report_df.iterrows():

        delta = row["Delta Exposure"]
        hedge = row["Hedge Coverage"]

        style = "green" if delta > 0 else "red"

        table.add_row(
            str(row["Commodity"]),
            str(row["Delivery Period"]),
            f"{delta:+,.0f} MWh",
            f"{hedge:.0f}%",
            style=style,
        )

    console.print(table)

@app.command()
def show_p_and_l(
    trade_path: str = typer.Argument(..., help="Path to trade file"),
    price_source: PriceSource = typer.Option(
        ...,
        help="Source for market prices"
    ),
    price_path: str | None = typer.Option(
        None,
        help="Path to market price file"
    ),
    static_prices: str | None = typer.Option(
        None,
        help='Static prices as JSON: \'{"commodity|delivery_period": price}\''
    ),
    output_format: OutputFormat = typer.Option(
        OutputFormat.TERMINAL,
        help="Report output format"
    )
):
    trade_list = load_trades_from_json(trade_path)
    aggregated_trades = position_aggregations(trade_list)

    # Build price provider
    if price_source == PriceSource.STATIC:

        if not static_prices:
            raise typer.BadParameter(
                "Provide --static-prices for static price source"
            )

        price_dict = {
            tuple(k.split("|")): v
            for k, v in json.loads(static_prices).items()
        }

        price_provider = StaticPriceProvider(price_dict)

    elif price_source == PriceSource.CSV:

        if not price_path:
            raise typer.BadParameter(
                "Provide --price-path for csv price source"
            )

        price_provider = CsvPriceProvider(price_path)

    # Build DataFrame
    df = pd.DataFrame([
        {
            "Book": pos.book,
            "Commodity": pos.commodity,
            "Delivery Period": pos.delivery_period,
            "Net Position": pos.net_position,
            "Average Price": pos.average_price,
            "Market Price": price_provider.get_price(
                str(pos.commodity),
                pos.delivery_period
            ),
        }
        for pos in aggregated_trades
    ])

    # Calculate PnL
    df["MtM PnL"] = (
        (df["Market Price"] - df["Average Price"])
        * df["Net Position"]
    )

    # CSV output
    if output_format == OutputFormat.CSV:
        df.to_csv("pnl_report.csv", index=False)
        console.print("[green]Saved pnl_report.csv[/green]")
        return

    # Terminal output
    table = Table(title="PnL Report")

    table.add_column("Book", style="cyan")
    table.add_column("Commodity", style="cyan")
    table.add_column("Delivery Period", style="cyan")
    table.add_column("Net Position", justify="right")
    table.add_column("Average Price", justify="right")
    table.add_column("Market Price", justify="right")
    table.add_column("MtM PnL", justify="right")

    for _, row in df.iterrows():

        style = "green" if row["MtM PnL"] > 0 else "red"

        table.add_row(
            str(row["Book"]),
            str(row["Commodity"]),
            str(row["Delivery Period"]),
            f"{row['Net Position']:+,.0f} MWh",
            f"£{row['Average Price']:,.2f}/MWh",
            f"£{row['Market Price']:,.2f}/MWh",
            f"£{row['MtM PnL']:+,.2f}",
            style=style,
        )

    console.print(table)



if __name__ == "__main__":
    app()


