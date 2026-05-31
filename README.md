# Position Engine

A Python-based Energy Trading and Risk Management (ETRM) tool for aggregating trades, calculating risk metrics, and computing mark-to-market P&L for wholesale energy positions.

---

## Overview

The Position Engine ingests trade data from JSON files and provides:

- Trade aggregation by book, commodity, and delivery period
- Delta exposure and hedge coverage calculations
- Mark-to-market P&L against static or CSV-sourced market prices
- A CLI interface for generating terminal and CSV reports

---

## Project Structure

```
position-engine/
├── load_trades.py        # Trade data model and JSON loading
├── trade_aggregator.py   # Aggregation, risk, and P&L logic
├── price_providers.py    # Market price provider interfaces
├── cli.py                # Typer CLI for reports
└── tests/
    └── data/
        └── empty_trades.json
```

---

## Modules

### `load_trades.py`

Defines the core trade data model and JSON ingestion.

**Enums**

| Enum | Values |
|---|---|
| `TradeCommodityType` | `nbp_gas`, `ttf_gas` |
| `TradeBook` | `physical`, `hedge` |
| `TradeAction` | `buy`, `sell` |

**`Trade` dataclass**

Frozen, slotted dataclass representing a single trade.

| Field | Type | Description |
|---|---|---|
| `trade_id` | `str` | Unique trade identifier |
| `book` | `TradeBook` | Physical or hedge book |
| `commodity` | `TradeCommodityType` | Commodity type |
| `delivery_period` | `str` | Delivery period e.g. `2026-01` |
| `action` | `TradeAction` | Buy or sell |
| `quantity_mwh` | `float` | Absolute quantity in MWh |
| `price` | `float` | Trade price |

`signed_quantity` property returns positive quantity for buys, negative for sells.

**Functions**

```python
load_trades_from_json(filepath: str | Path) -> list[Trade]
```
Loads trades from a JSON file. Returns an empty list for empty files rather than raising an error.

---

### `trade_aggregator.py`

Core aggregation and risk calculation logic.

**Dataclasses**

| Class | Fields | Description |
|---|---|---|
| `TradePositionAggregation` | `book`, `commodity`, `delivery_period`, `net_position`, `trade_count`, `total_cost`, `average_price` | Netted position for a book/commodity/period |
| `DeltaExposure` | `commodity`, `delivery_period`, `delta_exposure` | Net physical + hedge exposure |
| `HedgeCoverage` | `commodity`, `delivery_period`, `hedge_coverage` | Hedge as % of physical position |
| `PnLResult` | `pnl`, `timestamp` | P&L with optional timestamp |

**Functions**

```python
position_aggregations(trade_list: list[Trade]) -> list[TradePositionAggregation]
```
Aggregates trades by book, commodity, and delivery period. Returns empty list for no trades.

```python
delta_exposure(trade_list: list[Trade]) -> list[DeltaExposure]
```
Calculates net delta (physical + hedge) by commodity and delivery period.

```python
hedge_coverage(trade_list: list[Trade]) -> list[HedgeCoverage]
```
Calculates hedge coverage as a percentage of the physical position.

```python
find_p_n_l(
    aggregated_trade: TradePositionAggregation,
    price_provider: PriceProvider,
    return_timestamp: bool = False
) -> float | tuple[float, datetime]
```
Calculates unrealised P&L for a single aggregated position. Returns zero for flat or uncalculable positions. Optionally returns a timestamp alongside the P&L.

---

### `price_providers.py`

Provides market prices via a `Protocol`-based interface, allowing different price sources to be swapped without changing downstream code.

**`PriceProvider` (Protocol)**

```python
def get_price(self, commodity_type: str, delivery_period: str) -> float
```

**Implementations**

| Class | Description | Usage |
|---|---|---|
| `StaticPriceProvider` | Hardcoded dict of prices | Testing and simple scenarios |
| `CsvPriceProvider` | Loads prices from a CSV file | Production use with market data |

**`StaticPriceProvider` example**

```python
prices = StaticPriceProvider({
    ("nbp_gas", "2026-01"): 27.00,
    ("nbp_gas", "2026-02"): 26.00,
})
```

**CSV format for `CsvPriceProvider`**

```
Commodity,Delivery Period,Price
nbp_gas,2026-01,27.00
nbp_gas,2026-02,26.00
```

---

### `cli.py`

Typer-based CLI providing three report commands. Supports both terminal (Rich-formatted tables) and CSV output.

**Commands**

#### `show-position-aggregations`

Displays netted positions by book, commodity, and delivery period.

```bash
python cli.py show-position-aggregations trades.json
python cli.py show-position-aggregations trades.json --output-format csv
```

#### `show-risk-report`

Displays delta exposure and hedge coverage.

```bash
python cli.py show-risk-report trades.json
python cli.py show-risk-report trades.json --output-format csv
```

#### `show-p-and-l`

Displays mark-to-market P&L against a price source.

```bash
# Static prices
python cli.py show-p-and-l trades.json \
    --price-source static \
    --static-prices '{"nbp_gas|2026-01": 27.00, "nbp_gas|2026-02": 26.00}'

# CSV prices
python cli.py show-p-and-l trades.json \
    --price-source csv \
    --price-path market_prices.csv

# Save to CSV
python cli.py show-p-and-l trades.json \
    --price-source csv \
    --price-path market_prices.csv \
    --output-format csv
```

**Output format options**

| Value | Description |
|---|---|
| `terminal` | Rich-formatted coloured table (default) |
| `csv` | Saves report to a CSV file |

---

## Trade JSON Format

```json
[
    {
        "trade_id": "T001",
        "book": "physical",
        "commodity": "nbp_gas",
        "delivery_period": "2026-01",
        "action": "buy",
        "quantity_mwh": 1000.0,
        "price": 25.50
    },
    {
        "trade_id": "T002",
        "book": "hedge",
        "commodity": "nbp_gas",
        "delivery_period": "2026-01",
        "action": "sell",
        "quantity_mwh": 800.0,
        "price": 26.00
    }
]
```

An empty file or empty array `[]` is handled gracefully — all functions return empty results rather than raising errors.

---

## Installation
```bash
# 1. Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Clone the repo
git clone https://github.com/tomrihoy/ETRM-Work.git
cd position-engine

# 3. Create virtual environment with dependencies
uv sync

# 4. Activate virtual environment
source .venv/bin/activate
```

---

## Dependencies

- `pandas` — trade aggregation and DataFrame operations
- `numpy` — numerical calculations
- `typer` — CLI framework
- `rich` — terminal table formatting

---

## Key Design Decisions

**Protocol-based price providers** — `PriceProvider` is defined as a `Protocol` rather than an abstract base class, meaning any object with a `get_price` method satisfies the interface without explicit inheritance. This makes it easy to add new price sources (API, database) without modifying existing code.

**Frozen dataclasses** — `Trade`, `TradePositionAggregation`, and other data objects are frozen (`frozen=True`), making them immutable and hashable. This prevents accidental mutation of trade data after loading.

**Empty list guards** — all aggregation functions return empty lists for empty input rather than raising errors, making the system robust to empty trade files at market open or in testing.

**Stateless CLI** — each CLI command is a self-contained operation that loads trades, computes results, and outputs them. State is persisted via CSV files rather than held in memory between commands.
