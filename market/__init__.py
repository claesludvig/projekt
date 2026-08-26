"""Multi-timeframe market trend analysis for the daily brief."""

from .brief import (
    Report,
    build_report,
    format_text_summary,
    render_report_chart,
    report_to_dict,
)
from .config import DEFAULT_TIMEFRAMES, DEFAULT_WATCHLIST, Instrument, Timeframe
from .providers import (
    CsvProvider,
    MarketDataError,
    SyntheticProvider,
    YFinanceProvider,
    build_provider,
    record_snapshot,
)
from .trend import (
    Alignment,
    Direction,
    InstrumentTrend,
    TimeframeTrend,
    TrendConfig,
    analyse_instrument,
    classify_timeframe,
    resolve_alignment,
)

__all__ = [
    "Alignment",
    "CsvProvider",
    "DEFAULT_TIMEFRAMES",
    "DEFAULT_WATCHLIST",
    "Direction",
    "Instrument",
    "InstrumentTrend",
    "MarketDataError",
    "Report",
    "SyntheticProvider",
    "Timeframe",
    "TimeframeTrend",
    "TrendConfig",
    "YFinanceProvider",
    "analyse_instrument",
    "build_provider",
    "build_report",
    "classify_timeframe",
    "format_text_summary",
    "record_snapshot",
    "render_report_chart",
    "report_to_dict",
    "resolve_alignment",
]
