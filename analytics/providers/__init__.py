"""Supplementary provider adapters; MCX remains the authoritative futures source."""

from .frankfurter import FrankfurterAdapter
from .fred import FredAdapter
from .gnews import GNewsAdapter
from .goldprice import GoldPriceAdapter

__all__ = ["FrankfurterAdapter", "FredAdapter", "GNewsAdapter", "GoldPriceAdapter"]
