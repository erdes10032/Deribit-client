import os
from datetime import datetime

import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from app.core.chart_intervals import format_interval
from app.db.models import Price


class ChartService:
    OUTPUT_DIR = "charts"

    def __init__(self):
        os.makedirs(self.OUTPUT_DIR, exist_ok=True)

    def _build_chart(
        self,
        ticker: str,
        prices: list[Price],
        filename: str,
        title: str,
        x_start_ts: int | None = None,
        x_end_ts: int | None = None,
    ) -> str:
        if len(prices) < 2:
            return ""

        prices = sorted(prices, key=lambda x: x.timestamp)

        times = [datetime.fromtimestamp(p.timestamp) for p in prices]
        values = [p.price for p in prices]
        path = os.path.join(self.OUTPUT_DIR, filename)

        plt.figure(figsize=(10, 5))

        plt.plot(times, values)

        plt.title(title)
        plt.xlabel("Time")
        plt.ylabel("Price")

        if x_start_ts is not None and x_end_ts is not None:
            plt.xlim(
                datetime.fromtimestamp(x_start_ts),
                datetime.fromtimestamp(x_end_ts),
            )

        plt.gca().xaxis.set_major_locator(mdates.AutoDateLocator())
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S"))

        plt.xticks(rotation=45)
        plt.tight_layout()

        plt.savefig(path)
        plt.close()

        return path

    def build_chart(self, ticker: str, prices: list[Price]) -> str:
        if len(prices) < 2:
            return ""

        prices = sorted(prices, key=lambda x: x.timestamp)
        start = datetime.fromtimestamp(prices[0].timestamp)
        end = datetime.fromtimestamp(prices[-1].timestamp)

        start_str = start.strftime("%d.%m.%Y_%H-%M-%S")
        end_str = end.strftime("%H-%M-%S")
        filename = f"{ticker}__{start_str}__{end_str}.png"

        return self._build_chart(
            ticker=ticker,
            prices=prices,
            filename=filename,
            title=f"{ticker} price chart",
        )

    def build_window_chart(
        self,
        ticker: str,
        prices: list[Price],
        window_start_ts: int,
        window_end_ts: int,
    ) -> str:
        start_str = datetime.fromtimestamp(window_start_ts).strftime("%d.%m.%Y_%H-%M-%S")
        end_str = datetime.fromtimestamp(window_end_ts).strftime("%H-%M-%S")
        filename = f"{ticker}__{start_str}__{end_str}.png"

        return self._build_chart(
            ticker=ticker,
            prices=prices,
            filename=filename,
            title=f"{ticker} price chart (last {format_interval(window_end_ts - window_start_ts)})",
            x_start_ts=window_start_ts,
            x_end_ts=window_end_ts,
        )

    def build_full_chart(self, ticker: str, prices: list[Price]) -> str:
        if len(prices) < 2:
            return ""

        created_at = datetime.now().strftime("%d.%m.%Y_%H-%M-%S")
        end_ts = max(p.timestamp for p in prices)
        filename = f"{ticker}__full__{created_at}__upto_{end_ts}.png"
        return self._build_chart(
            ticker=ticker,
            prices=prices,
            filename=filename,
            title=f"{ticker} full price chart",
        )