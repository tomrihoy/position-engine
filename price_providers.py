from typing import Protocol
from pathlib import Path
import pandas as pd

class PriceProvider(Protocol):
    """ Anything which returns market prices. """
    def get_price(self, 
                  commodity_type: str,
                   delivery_period: str)->float:
        ''' Return market prices'''
        
class StaticPriceProvider:
    """ Hardcoded prices for testing. """
    def __init__(self, prices: dict[tuple[str, str], float]): 
        self._prices = prices
    def get_price(self, commodity: str, delivery_period: str) -> float:
        return self._prices[(commodity , delivery_period)]


        
class CsvPriceProvider:
    """ Prices from CSV file. """
    def __init__(self, filepath: str| Path):
        price_df = pd.read_csv(filepath)
        self._prices = dict(zip(zip(price_df['Commodity'], price_df['Delivery Period']), price_df['Price']))

    def get_price(self, commodity: str, delivery_period: str) -> float:
        return self._prices[(commodity , delivery_period)]
