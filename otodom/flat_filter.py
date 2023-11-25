from typing import Self

from furl import furl

# 'https://www.otodom.pl/pl/oferty/wynajem/mieszkanie/warszawa?distanceRadius=0&page=1&limit=36&market=ALL&ownerTypeSingleSelect=ALL&extras=[AIR_CONDITIONING]&media=[INTERNET]&buildYearMin=2010&locations=[cities_6-26]&viewType=listing&lang=pl&searchingCriteria=wynajem&searchingCriteria=mieszkanie&searchingCriteria=cala-polska'


class EstateFilter:
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
        self.search_suffix = 'mieszkanie/warszawa'
        self.description = []
        self.locations = []
        self.rent_type = None

    def rent_a_flat(self) -> Self:
        self.rent_type = 'mieszkanie'
        return self

    def rent_a_commercial_estate(self) -> Self:
        self.rent_type = 'lokal'
        return self

    def get_markdown_description(self, filter_name: str) -> str:
        options = '\n'.join(f'• {d}' for d in self.description)
        return f'Filter: `{filter_name}`\n' + options

    def with_air_conditioning(self) -> Self:
        self.description.append('With Air conditioning')
        self.extras.add('AIR_CONDITIONING')
        return self

    def with_internet(self) -> Self:
        self.description.append('With Internet')
        self.media.add('INTERNET')
        return self

    def with_max_price(self, price_max: int) -> Self:
        self.description.append(f'With max price: {price_max}')
        self.price_max = price_max
        return self

    def with_min_price(self, price_min: int) -> Self:
        self.description.append(f'With min price: {price_min}')
        self.price_min = price_min
        return self

    def with_min_area(self, area_min: int) -> Self:
        self.description.append(f'With min area: {area_min}')
        self.area_min = area_min
        return self

    def with_max_area(self, area_max: int) -> Self:
        self.description.append(f'With max area: {area_max}')
        self.area_max = area_max
        return self

    def with_page(self, page_idx: int) -> Self:
        self.page = page_idx
        return self

    def with_minimum_build_year(self, year: int) -> Self:
        self.description.append(f'With minimum build year: {year}')
        self.min_built_year = year
        return self

    def in_wola(self):
        self.description.append('In Wola')
        self.locations.append('mazowieckie/warszawa/warszawa/warszawa/wola')
        return self

    def in_mokotow(self):
        self.description.append('In Mokotow')
        self.locations.append('mazowieckie/warszawa/warszawa/warszawa/mokotow')
        return self

    def in_srodmiescie(self):
        self.description.append('In Srodmiescie')
        self.locations.append('mazowieckie/warszawa/warszawa/warszawa/srodmiescie')
        return self

    def in_powisle(self):
        self.description.append('In Powisle')
        self.locations.append('mazowieckie/warszawa/warszawa/warszawa/srodmiescie/powisle')
        return self

    def in_sluzewiec(self):
        self.description.append('In Sluzewiec')
        self.locations.append(
            'mazowieckie/warszawa/warszawa/warszawa/mokotow/sluzewiec'
        )
        return self

    def in_ochota(self):
        self.description.append('In Ochota')
        self.locations.append('mazowieckie/warszawa/warszawa/warszawa/ochota')
        self.search_suffix = 'mieszkanie/warszawa/ochota'
        return self

    def in_sady_zoliborskie(self):
        self.description.append('In Sady Zoliborskie')
        self.locations.append(
            'mazowieckie/warszawa/warszawa/warszawa/zoliborz/sady-zoliborskie'
        )
        return self

    def in_zoliborz(self):
        self.description.append('In Zoliborz')
        self.locations.append(
            'mazowieckie/warszawa/warszawa/warszawa/zoliborz'
        )
        return self

    def compose_url(self):
        if not self.rent_type:
            raise ValueError('What should be rented is not specified.')
        if not self.locations:
            raise ValueError('Please, specify at least one location')

        url = furl(
            f'https://www.otodom.pl/pl/wyniki/wynajem/{self.rent_type}/wiele-lokalizacji'
        )
        locations = '[' + ','.join(self.locations) + ']'

        url.args['distanceRadius'] = 0
        url.args['limit'] = 36
        # url.args["market"] = "ALL"
        # url.args["ownerTypeSingleSelect"] = "ALL"
        url.args['locations'] = locations
        url.args['viewType'] = 'listing'
        url.args['by'] = 'DEFAULT'
        url.args['direction'] = 'DESC'
        url.args['lang'] = 'pl'
        if self.extras:
            url.args['extras'] = '[' + ','.join(self.extras) + ']'
        if self.media:
            url.args['media'] = '[' + ','.join(self.media) + ']'
        if self.min_built_year:
            url.args['buildYearMin'] = self.min_built_year
        if self.page:
            url.args['page'] = self.page
        if self.price_max:
            url.args['priceMax'] = self.price_max
        if self.price_min:
            url.args['priceMin'] = self.price_min
        if self.area_min:
            url.args['areaMin'] = self.area_min
        if self.area_max:
            url.args['areaMax'] = self.area_max

        return str(url)

    def matches_filter(self, item: dict) -> bool:
        # return 'warszawa' in item.get('locationLabel', {}).get('value', '').lower()
        return True


def _specify_common_conditions(f: EstateFilter) -> EstateFilter:
    return (
        f.rent_a_flat()
        .with_max_price(4500)
        .with_min_area(41)
        .with_minimum_build_year(2008)
    )


FILTERS = {
    'wola': (_specify_common_conditions(EstateFilter('wola').in_wola())),
    'mokotow': (_specify_common_conditions(EstateFilter('mokotow').in_mokotow())),
    'ochota': (_specify_common_conditions(EstateFilter('ochota').in_ochota())),
    'sady_zoliborskie': (
        _specify_common_conditions(
            EstateFilter('sady_zoliborskie').in_sady_zoliborskie()
        )
    ),
    'commercial': (
        EstateFilter('commercial')
        .rent_a_commercial_estate()
        .in_ochota()
        .in_wola()
        .in_mokotow()
        .in_srodmiescie()
        .in_powisle()
        .in_zoliborz()
        .with_max_price(15000)
        .with_min_area(100)
    ),
    'polina': (EstateFilter('polina')
               .rent_a_flat()
               .with_max_price(3500)
               .in_wola()
               .in_srodmiescie()
               )
}

assert all(f.name == name for name, f in FILTERS.items())
