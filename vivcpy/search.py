import requests
import time

from bs4 import BeautifulSoup
from dataclasses import dataclass, fields
from typing import Iterator

from vivcpy.enums import (
    BaseSearchValueEnum,
    ColorOfBerrySkin,
    CountryOrRegion,
    FormationOfSeeds,
    SexOfFlowers,
    Species,
    Utilization,
)
from vivcpy.models import Variety
from vivcpy.types import E, OneOrMany
from typing import Optional

BASE_URL = "https://www.vivc.de/index.php"
SLEEP_SECONDS = 1  # seconds to sleep before requests to not overload the server
SEARCH_PARAMS_KEY_MAP: dict[str, str] = {
    "prime_name": "PassportSearch[leitname]",
    "variety_number_vivc": "PassportSearch[kenn_nr]",
    "color_of_berry_skin": "PassportSearch[color][]",
    "country_or_region_of_origin_of_the_variety": "PassportSearch[country][]",
    "utilization": "PassportSearch[utilization2][]",
    "species": "PassportSearch[gattung_id2][]",
    "formation_of_seeds": "PassportSearch[samenausbildungs][]",
}


def empty_string_to_none(raw_str: str) -> str | None:
    raw_str = raw_str.strip()
    return raw_str if raw_str else None


def enum_or_none(raw_str: str, enum_class: type[E]) -> E | None:
    raw_str_or_none = empty_string_to_none(raw_str)
    return enum_class(raw_str_or_none) if raw_str_or_none else None


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
    formation_of_seeds: Optional[OneOrMany[FormationOfSeeds]] = None

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

    def __init__(
        self,
        params: PassportDataSearchParams,
        per_page: int = 500,
        details: bool = False,
    ):
        """Initialize with search parameters and optional page size.

        Parameters
        ----------
        params : PassportDataSearchParams
            Filters to apply to the VIVC passport search.
        per_page : int, optional
            Number of results per page, by default 500.
        details: bool, optional
            Perform a additional requests using the `PassportDataViewSearch` class
            to retrieve more information on the varieties.
        """
        self.search_params = params
        self.per_page = per_page
        self.details = details

    def __iter__(self) -> Iterator[Variety]:
        """Yield varieties across all result pages."""
        # first page
        soup = self._get_soup(1)
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
                soup = self._get_soup(page)
                yield from self._parse_varieties(soup)

    def _get_soup(self, page: int) -> BeautifulSoup:
        time.sleep(
            SLEEP_SECONDS
        )  # wait before the request to not overload the VIVC server
        response = requests.get(BASE_URL, params=self._url_params(page=page))
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        return soup

    def _url_params(self, page: int) -> dict:
        """Build the query parameter dict for a given page number."""
        return {
            **self.search_params.to_requests_params(),
            "page": page,
            "per-page": self.per_page,
            "r": "passport/result",
        }

    def _parse_varieties(self, soup: BeautifulSoup) -> Iterator[Variety]:
        """Extract Variety objects from a parsed results page."""
        rows = soup.find_all("table")[0].find_all("tr")[3:]

        if rows[0].text.strip() in ["No results found.", ""]:
            return

        for row in rows:
            td_tags = row.find_all("td")
            try:
                raw_variety_number_vivc = td_tags[2].text.strip()
                variety_number_vivc = int(raw_variety_number_vivc)
            except ValueError:
                msg = (
                    "VIVC number could not be parsed into an integer, "
                    f"got: {raw_variety_number_vivc}"
                )
                raise ValueError(msg)

            a_tags_utilization = td_tags[3].find_all("a")
            utilization_list = [Utilization(a_tag.text) for a_tag in a_tags_utilization]
            utilization = utilization_list if len(utilization_list) > 0 else None

            year_of_crossing_str = td_tags[10].text
            year_of_crossing = (
                int(year_of_crossing_str) if year_of_crossing_str else None
            )

            variety = Variety(
                prime_name=td_tags[0].text,
                color_of_berry_skin=enum_or_none(td_tags[1].text, ColorOfBerrySkin),
                variety_number_vivc=variety_number_vivc,
                utilization=utilization,
                country_or_region_of_origin_of_the_variety=enum_or_none(
                    td_tags[4].text, CountryOrRegion
                ),
                species=enum_or_none(td_tags[5].text, Species),
                prime_name_of_parent_1=empty_string_to_none(td_tags[6].text),
                prime_name_of_parent_2=empty_string_to_none(td_tags[7].text),
                breeder=empty_string_to_none(td_tags[9].text),
                year_of_crossing=year_of_crossing,
            )
            if self.details:
                detail_variety = PassportDataViewSearch(
                    variety.variety_number_vivc
                ).get_variety()
                variety = detail_variety & variety
            yield variety


class PassportDataViewSearch:
    """Fetch detailed passport data for a single variety by its VIVC number.

    Named after the ``r=passport/view`` URL parameter used by the VIVC website.
    """

    def __init__(self, variety_number_vivc: int):
        self.variety_number_vivc = variety_number_vivc

    def get_variety(self) -> Variety:
        soup = self._get_soup()
        return self._parse_variety(soup)

    def _get_soup(self) -> BeautifulSoup:
        time.sleep(
            SLEEP_SECONDS
        )  # wait before the request to not overload the VIVC server
        response = requests.get(BASE_URL, params=self._url_params())
        soup = BeautifulSoup(response.content, "html.parser")
        return soup

    def _url_params(self):
        return {
            "id": self.variety_number_vivc,
            "r": "passport/view",
        }

    def _parse_variety(self, soup: BeautifulSoup) -> Variety:
        tables = soup.find_all("table")
        td_tags = tables[0].find_all("td")

        variety_number_vivc = int(td_tags[2].text)
        if variety_number_vivc != self.variety_number_vivc:
            msg = (
                f"Retrieved VIVC number ({variety_number_vivc}) "
                f"is not equal to requested VIVC number ({self.variety_number_vivc})."
            )
            raise ValueError(msg)

        year_of_crossing_str = td_tags[16].text.strip()
        year_of_crossing = int(year_of_crossing_str) if year_of_crossing_str else None

        year_of_selection_str = td_tags[17].text.strip()
        year_of_selection = (
            int(year_of_selection_str) if year_of_selection_str else None
        )

        loci_for_resistance_str = empty_string_to_none(td_tags[25].text)
        loci_for_resistance = (
            loci_for_resistance_str.split("\n") if loci_for_resistance_str else None
        )

        synonyms_table = next(
            (
                table
                for table in tables
                if (thead := table.find("thead"))
                and thead.text.strip().startswith("Synonyms")
            ),
            None,
        )
        synonyms = (
            [td.text for td in synonyms_table.find_all("td")]
            if synonyms_table
            else None
        )

        return Variety(
            prime_name=td_tags[0].text.strip(),
            color_of_berry_skin=enum_or_none(td_tags[1].text.strip(), ColorOfBerrySkin),
            variety_number_vivc=variety_number_vivc,
            country_or_region_of_origin_of_the_variety=enum_or_none(
                td_tags[3].text, CountryOrRegion
            ),
            species=enum_or_none(td_tags[4].text, Species),
            pedigree_as_given_by_breeder_bibliography=empty_string_to_none(
                td_tags[5].text
            ),
            pedigree_confirmed_by_markers=empty_string_to_none(td_tags[6].text),
            prime_name_of_parent_1=empty_string_to_none(td_tags[8].text),
            prime_name_of_parent_2=empty_string_to_none(td_tags[9].text),
            offspring=td_tags[11].text.strip() == "YES",
            breeder=empty_string_to_none(td_tags[12].text),
            breeder_institute_code=empty_string_to_none(td_tags[13].text),
            breeder_contact_address=empty_string_to_none(td_tags[14].text),
            year_of_crossing=year_of_crossing,
            year_of_selection=year_of_selection,
            year_of_protection=empty_string_to_none(td_tags[18].text),
            formation_of_seeds=enum_or_none(td_tags[19].text.strip(), FormationOfSeeds),
            sex_of_flowers=enum_or_none(td_tags[20].text.strip(), SexOfFlowers),
            taste=empty_string_to_none(td_tags[21].text),
            chlorotype=empty_string_to_none(td_tags[22].text),
            loci_for_resistance=loci_for_resistance,
            synonyms=synonyms,
        )
