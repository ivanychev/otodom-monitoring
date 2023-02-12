from furl import furl
from typing_extensions import Self

# 'https://www.otodom.pl/pl/oferty/wynajem/mieszkanie/warszawa?distanceRadius=0&page=1&limit=36&market=ALL&ownerTypeSingleSelect=ALL&extras=[AIR_CONDITIONING]&media=[INTERNET]&buildYearMin=2010&locations=[cities_6-26]&viewType=listing&lang=pl&searchingCriteria=wynajem&searchingCriteria=mieszkanie&searchingCriteria=cala-polska'


class FlatFilter:
    """This class describes flat filters and transforms it to URL."""

    def __init__(self, name):
        self.name = name
        self.extras = set()
        self.media = set()
        self.page = None
        self.min_built_year = None
        self.price_max = None
        self.price_min = None
        self.area_max = None
        self.area_min = None
        self.locations = "[cities_6-26]"

    def with_air_conditioning(self) -> Self:
        self.extras.add("AIR_CONDITIONING")
        return self

    def with_internet(self) -> Self:
        self.media.add("INTERNET")
        return self

    def with_max_price(self, price_max: int) -> Self:
        self.price_max = price_max
        return self

    def with_min_price(self, price_min: int) -> Self:
        self.price_min = price_min
        return self

    def with_min_area(self, area_min: int) -> Self:
        self.area_min = area_min
        return self

    def with_max_area(self, area_max: int) -> Self:
        self.area_max = area_max
        return self

    def with_page(self, page_idx: int) -> Self:
        self.page = page_idx
        return self

    def with_minimum_build_year(self, year: int) -> Self:
        self.min_built_year = year
        return self

    def in_wola(self):
        self.locations = "[districts_6-117]"
        return self

    def in_mokotow(self):
        self.locations = "[districts_6-39]"
        return self

    def in_sluzewiec(self):
        self.locations = "[districts_6-7548]"
        return self

    def in_sady_zoliborskie(self):
        self.locations = "[districts_6-9215]"
        return self

    def in_muranow(self):
        self.locations = "[districts_6-961]"
        return self

    def compose_url(self):
        url = furl(f"https://www.otodom.pl/pl/oferty/wynajem/mieszkanie/warszawa")
        extras = "[" + ",".join(self.extras) + "]"
        media = "[" + ",".join(self.media) + "]"

        url.args["distanceRadius"] = 0
        url.args["limit"] = 36
        url.args["market"] = "ALL"
        url.args["ownerTypeSingleSelect"] = "ALL"
        url.args["locations"] = self.locations
        url.args["viewType"] = "listing"
        url.args["lang"] = "pl"
        url.args["extras"] = extras
        url.args["media"] = media
        url.args["searchingCriteria"] = ["wynajem", "mieszkanie", "cala-polska"]
        if self.min_built_year:
            url.args["buildYearMin"] = self.min_built_year
        if self.page:
            url.args["page"] = self.page
        if self.price_max:
            url.args["priceMax"] = self.price_max
        if self.price_min:
            url.args["priceMin"] = self.price_min
        if self.area_min:
            url.args["areaMin"] = self.area_min
        if self.area_max:
            url.args["areaMax"] = self.area_max

        return str(url)


def _specify_common_conditions_no_conditioner(f: FlatFilter) -> FlatFilter:
    return (
        f.with_internet()
        .with_max_price(4200)
        .with_min_area(40)
        .with_minimum_build_year(2008)
    )


FILTERS = {
    "wola_no_conditioner": (_specify_common_conditions_no_conditioner(FlatFilter("wola_no_conditioner").in_wola())),
    "mokotow_no_conditioner": (_specify_common_conditions_no_conditioner(FlatFilter("mokotow_no_conditioner").in_mokotow())),
}

assert all(f.name == name for name, f in FILTERS.items())
