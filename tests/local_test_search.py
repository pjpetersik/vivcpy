"""Integration tests that run directly against the VIVC website.

These tests are not part of the standard test suite and must be run explicitly::

    python -m unittest tests.local_test_search
"""

from unittest import TestCase

from vivcpy.search import PassportDataSearch, PassportDataSearchParams
from vivcpy.enums import ColorOfBerrySkin, CountryOrRegion, Species


class TestPassportDataSearch(TestCase):
    def test_search_by_species_and_country(self):
        params = PassportDataSearchParams(
            species=Species.VITIS_VINIFERA_SUBSP_SATIVA,
            country_or_region_of_origin_of_the_variety=CountryOrRegion.FRA,
        )

        variety_iterator = PassportDataSearch(params=params)
        variety = next(iter(variety_iterator))
        self.assertEqual(variety.prime_name, "ABEILLANE")
        self.assertIsNone(variety.color_of_berry_skin)
        self.assertEqual(variety.variety_number_vivc, 10)
        self.assertEqual(
            variety.country_or_region_of_origin_of_the_variety, CountryOrRegion.FRA
        )
        self.assertEqual(variety.species, Species.VITIS_VINIFERA_SUBSP_SATIVA)

    def test_search_by_species_and_country_list(self):
        params = PassportDataSearchParams(
            color_of_berry_skin=ColorOfBerrySkin.RED,
            species=Species.VITIS_VINIFERA_SUBSP_SATIVA,
        )
        varieties = list(PassportDataSearch(params))
        self.assertEqual(len(varieties), 981)
