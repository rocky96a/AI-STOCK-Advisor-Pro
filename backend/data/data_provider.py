from abc import ABC, abstractmethod


class DataProvider(ABC):

    @abstractmethod
    def get_data(
        self,
        symbol,
        period="2y",
        interval="1d",
    ):
        """
        Return normalized OHLCV DataFrame:

        Datetime
        Open
        High
        Low
        Close
        Volume
        """
        raise NotImplementedError
