from typing import Self

from furl import furl

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
        self.search_suffix = "mieszkanie/warszawa"
        self.description = []

    def get_markdown_description(self, filter_name: str) -> str:
        options = "\n".join(f"• {d}" for d in self.description)
        return f"Filter: `{filter_name}`\n" + options

    def with_air_conditioning(self) -> Self:
        self.description.append("With Air conditioning")
        self.extras.add("AIR_CONDITIONING")
        return self

    def with_internet(self) -> Self:
        self.description.append("With Internet")
        self.media.add("INTERNET")
        return self

    def with_max_price(self, price_max: int) -> Self:
        self.description.append(f"With max price: {price_max}")
        self.price_max = price_max
        return self

    def with_min_price(self, price_min: int) -> Self:
        self.description.append(f"With min price: {price_min}")
        self.price_min = price_min
        return self

    def with_min_area(self, area_min: int) -> Self:
        self.description.append(f"With min area: {area_min}")
        self.area_min = area_min
        return self

    def with_max_area(self, area_max: int) -> Self:
        self.description.append(f"With max area: {area_max}")
        self.area_max = area_max
        return self

    def with_page(self, page_idx: int) -> Self:
        self.page = page_idx
        return self

    def with_minimum_build_year(self, year: int) -> Self:
        self.description.append(f"With minimum build year: {year}")
        self.min_built_year = year
        return self

    def in_wola(self):
        self.description.append(f"In Wola")
        self.locations = "[districts_6-117]"
        return self

    def in_mokotow(self):
        self.description.append(f"In Mokotow")
        self.locations = "[districts_6-39]"
        return self

    def in_ochota(self):
        self.description.append(f"In Ochota")
        self.locations = "[districts_6-40]"
        return self

    def in_sluzewiec(self):
        self.description.append(f"In Sluzewiec")
        self.locations = "[districts_6-7548]"
        return self

    def in_ochota(self):
        self.locations = "[districts_6-40]"
        self.search_suffix = "mieszkanie/warszawa/ochota"
        return self

    def in_sady_zoliborskie(self):
        self.description.append(f"In Sady Zoliborskie")
        self.locations = "[districts_6-9215]"
        return self

    def in_muranow(self):
        self.description.append(f"In Muranow")
        self.locations = "[districts_6-961]"
        return self

    def compose_url(self):
        url = furl(f"https://www.otodom.pl/pl/oferty/wynajem") / self.search_suffix
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
        url.args["searchingCriteria"] = ["wynajem", "mieszkanie"]
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

    def matches_filter(self, item: dict) -> bool:
        # return 'warszawa' in item.get('locationLabel', {}).get('value', '').lower()
        return True


def _specify_common_conditions(f: FlatFilter) -> FlatFilter:
    return f.with_max_price(4500).with_min_area(38).with_minimum_build_year(2008)


FILTERS = {
    # "warsaw": (_specify_common_conditions(FlatFilter("warsaw"))),
    "wola": (_specify_common_conditions(FlatFilter("wola").in_wola())),
    "mokotow": (_specify_common_conditions(FlatFilter("mokotow").in_mokotow())),
    "ochota": (_specify_common_conditions(FlatFilter("ochota").in_ochota())),
    # "muranow": (_specify_common_conditions(FlatFilter("muranow").in_muranow())),
    # "sluzewiec": (_specify_common_conditions(FlatFilter("sluzewiec").in_sluzewiec())),
    "sady_zoliborskie": (
        _specify_common_conditions(FlatFilter("sady_zoliborskie").in_sady_zoliborskie())
    ),
}

assert all(f.name == name for name, f in FILTERS.items())
