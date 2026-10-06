from unittest import TestCase

from bs4 import BeautifulSoup

from vivcpy.enums import ColorOfBerrySkin
from vivcpy.models import Variety
from vivcpy.search import PassportDataSearchParams, PassportDataViewSearch


class TestPassportDataSearchParams(TestCase):
    def test_default_params(self):
        params = PassportDataSearchParams()
        result = params.to_requests_params()
        self.assertEqual(
            result,
            {
                "PassportSearch[kenn_nr]": None,
                "PassportSearch[leitname]": None,
                "PassportSearch[color][]": None,
                "PassportSearch[country][]": None,
                "PassportSearch[utilization2][]": None,
                "PassportSearch[gattung_id2][]": None,
                "PassportSearch[samenausbildungs][]": None,
            },
        )

    def test_prime_name_only(self):
        params = PassportDataSearchParams(prime_name="Riesling")
        result = params.to_requests_params()
        self.assertEqual(result["PassportSearch[leitname]"], "Riesling")
        self.assertIsNone(result["PassportSearch[kenn_nr]"])
        self.assertIsNone(result["PassportSearch[color][]"])

    def test_variety_number_only(self):
        params = PassportDataSearchParams(variety_number_vivc=12345)
        result = params.to_requests_params()
        self.assertEqual(result["PassportSearch[kenn_nr]"], 12345)

    def test_single_color(self):
        params = PassportDataSearchParams(color_of_berry_skin=ColorOfBerrySkin.GREEN)
        result = params.to_requests_params()
        self.assertEqual(result["PassportSearch[color][]"], "green")

    def test_multiple_colors(self):
        params = PassportDataSearchParams(
            color_of_berry_skin=[
                ColorOfBerrySkin.GREEN,
                ColorOfBerrySkin.BLACK,
            ]
        )
        result = params.to_requests_params()
        self.assertEqual(result["PassportSearch[color][]"], ["green", "black"])

    def test_all_params(self):
        params = PassportDataSearchParams(
            prime_name="Merlot",
            variety_number_vivc=42,
            color_of_berry_skin=ColorOfBerrySkin.RED,
        )
        result = params.to_requests_params()
        self.assertEqual(result["PassportSearch[leitname]"], "Merlot")
        self.assertEqual(result["PassportSearch[kenn_nr]"], 42)
        self.assertEqual(result["PassportSearch[color][]"], "red")

    def test_to_request_value_raises_on_unexpected_type(self):
        params = PassportDataSearchParams()
        with self.assertRaises(TypeError):
            params._to_request_value(set())

    def test_empty_color_list(self):
        params = PassportDataSearchParams(color_of_berry_skin=[])
        result = params.to_requests_params()
        self.assertEqual(result["PassportSearch[color][]"], [])


MAIN_TABLE_TD_COUNT = 26


def passport_main_table_html() -> str:
    """Build a minimal passport detail table accepted by ``_parse_variety``."""
    cells = [""] * MAIN_TABLE_TD_COUNT
    cells[0] = "TESTVINE"
    cells[2] = "4572"
    return (
        "<table><tr>" + "".join(f"<td>{cell}</td>" for cell in cells) + "</tr></table>"
    )


def synonyms_table_html(names: list[str]) -> str:
    """Build the VIVC synonyms table, whose cells are nested in a wrapper cell."""
    inner = "".join(f"<td>{name}</td>" for name in names)
    return (
        f"<table><thead><tr><th>Synonyms: {len(names)}</th></tr></thead><tbody>"
        f'<tr><td class="w5"><table><tr></tr><tr>{inner}</tr></table></td></tr>'
        "</tbody></table>"
    )


class TestPassportDataViewSynonyms(TestCase):
    """Regression tests for the passport view synonyms table."""

    def _parse_variety(self, synonyms_html: str) -> Variety:
        soup = BeautifulSoup(passport_main_table_html() + synonyms_html, "html.parser")
        return PassportDataViewSearch(4572)._parse_variety(soup)

    def test_multiple_synonyms_exclude_wrapper_concatenation(self):
        variety = self._parse_variety(
            synonyms_table_html(["MERLAU BLANC", "MERLAUT BLANC", "MERLOT BIANCO"])
        )
        self.assertEqual(
            variety.synonyms, ["MERLAU BLANC", "MERLAUT BLANC", "MERLOT BIANCO"]
        )

    def test_single_synonym_is_not_duplicated(self):
        variety = self._parse_variety(synonyms_table_html(["BLAUER TRAMINER"]))
        self.assertEqual(variety.synonyms, ["BLAUER TRAMINER"])

    def test_no_synonyms_returns_none(self):
        variety = self._parse_variety(synonyms_table_html([]))
        self.assertIsNone(variety.synonyms)

    def test_missing_synonyms_table_returns_none(self):
        variety = self._parse_variety("")
        self.assertIsNone(variety.synonyms)
