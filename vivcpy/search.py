import requests
import time

from bs4 import BeautifulSoup
from dataclasses import dataclass, fields
from typing import Iterator

from vivcpy.enums import (
    BaseSearchValueEnum,
    ColorOfBerrySkin,
    CountryOrRegion,
    Species,
    Utilization,
)
from vivcpy.models import Variety
from vivcpy.types import E, OneOrMany
from typing import Optional

BASE_URL = "https://www.vivc.de/index.php"


def enum_or_none(raw_str: str, enum_class: type[E]) -> E | None:
    return enum_class(raw_str) if raw_str else None


SEARCH_PARAMS_KEY_MAP: dict[str, str] = {
    "prime_name": "PassportSearch[leitname]",
    "variety_number_vivc": "PassportSearch[kenn_nr]",
    "color_of_berry_skin": "PassportSearch[color][]",
    "country_or_region_of_origin_of_the_variety": "PassportSearch[country][]",
    "utilization": "PassportSearch[utilization2][]",
    "species": "PassportSearch[gattung_id2][]",
}


@dataclass
class PassportDataSearchParams:
    prime_name: Optional[str] = None
    variety_number_vivc: Optional[int] = None
    color_of_berry_skin: Optional[OneOrMany[ColorOfBerrySkin]] = None
    country_or_region_of_origin_of_the_variety: Optional[OneOrMany[CountryOrRegion]] = (
        None
    )
    utilization: Optional[OneOrMany[Utilization]] = None
    species: Optional[OneOrMany[Species]] = None

    def to_requests_params(self) -> dict[str, str | list[str]]:
        """Return search fields as a dict of request query parameters.

        Field names are mapped via SEARCH_PARAMS_KEY_MAP and enum values
        are resolved to their underlying strings.
        """
        return {
            SEARCH_PARAMS_KEY_MAP[f.name]: self._to_request_value(getattr(self, f.name))
            for f in fields(self)
        }

    def _to_request_value(
        self, value: OneOrMany[BaseSearchValueEnum | str]
    ) -> OneOrMany[str]:
        """Convert a field value to its request query string representation."""
        if isinstance(value, list):
            return [
                v.search_value if isinstance(v, BaseSearchValueEnum) else v
                for v in value
                if v is not None
            ]
        elif isinstance(value, BaseSearchValueEnum):
            return value.search_value
        elif isinstance(value, str) or isinstance(value, int) or value is None:
            return value
        else:
            msg = f"Unexpected type of for value argument: {type(value)}"
            raise TypeError(msg)


class PassportDataSearch:
    """Iterable that fetches Variety results from the VIVC passport search."""

    def __init__(self, params: PassportDataSearchParams, per_page=500):
        """Initialize with search parameters and optional page size.

        Parameters
        ----------
        params : PassportDataSearchParams
            Filters to apply to the VIVC passport search.
        per_page : int, optional
            Number of results per page, by default 500.
        """
        self.search_params = params
        self.per_page = per_page

    def url_params(self, page=1) -> dict:
        """Build the query parameter dict for a given page number."""
        return {
            **self.search_params.to_requests_params(),
            "page": page,
            "per-page": self.per_page,
            "r": "passport/result",
        }

    def _parse_varieties(self, soup: BeautifulSoup) -> list[Variety]:
        """Extract Variety objects from a parsed results page."""
        rows = soup.find_all("table")[0].find_all("tr")[3:]
        variety_list: list = []

        if rows[0].text == "No results found.":
            return variety_list

        for row in rows:
            td_tags = row.find_all("td")

            a_tags_utilization = td_tags[3].find_all("a")
            utilization_list = [Utilization(a_tag.text) for a_tag in a_tags_utilization]
            utilization = utilization_list if len(utilization_list) > 0 else None

            year_of_crossing = td_tags[10].text
            year_of_crossing = int(year_of_crossing) if year_of_crossing else None
            variety = Variety(
                prime_name=td_tags[0].text,
                color_of_berry_skin=enum_or_none(td_tags[1].text, ColorOfBerrySkin),
                variety_number_vivc=int(td_tags[2].text),
                utilization=utilization,
                country_or_region_of_origin_of_the_variety=enum_or_none(
                    td_tags[4].text, CountryOrRegion
                ),
                species=enum_or_none(td_tags[5].text, Species),
                prime_name_of_parent_1=td_tags[6].text,
                prime_name_of_parent_2=td_tags[7].text,
                breeder=td_tags[9].text,
                year_of_crossing=year_of_crossing,
            )
            variety_list.append(variety)
        return variety_list

    def __iter__(self) -> Iterator[Variety]:
        """Yield varieties across all result pages."""
        # first page
        response = requests.get(BASE_URL, params=self.url_params(page=1))
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        yield from self._parse_varieties(soup)

        # further pages
        last_page_link = soup.find_all("li", {"class": "last"})

        if last_page_link:
            a_tags = last_page_link[0].find("a")
            if a_tags is None:
                return

            data_page = a_tags.get("data-page")
            if not isinstance(data_page, str):
                return

            n_pages = int(data_page) + 1

            for page in range(2, n_pages + 1):
                time.sleep(3)  # wait 3 seconds before the next request
                response = requests.get(BASE_URL, params=self.url_params(page=page))
                response.raise_for_status()
                soup = BeautifulSoup(response.content, "html.parser")
                yield from self._parse_varieties(soup)
