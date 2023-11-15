from abc import ABC, abstractmethod

from otodom.cars.model import CarOffering


class CarSearcher(ABC):
    @abstractmethod
    def search_all(self) -> list[CarOffering]:
        pass

    @abstractmethod
    def search_result_count(self) -> int:
        pass

    @abstractmethod
    def pretty_str(self) -> str:
        pass
