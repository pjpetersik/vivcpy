from unittest import TestCase

from vivcpy.enums import (
    ColorOfBerrySkin,
    CountryOrRegion,
    Species,
    Utilization,
)


class TestStandardSearchValueEnum(TestCase):
    """Tests for enums inheriting from StandardSearchValueEnum."""

    def test_search_value_is_lowercase_name(self):
        self.assertEqual(ColorOfBerrySkin.GREEN.search_value, "green")
        self.assertEqual(ColorOfBerrySkin.BLACK.search_value, "black")
        self.assertEqual(ColorOfBerrySkin.ROSE.search_value, "rose")

    def test_value_is_display_name(self):
        self.assertEqual(ColorOfBerrySkin.GREEN.value, "BLANC")
        self.assertEqual(ColorOfBerrySkin.BLACK.value, "NOIR")

    def test_country_search_value_is_lowercase_name(self):
        self.assertEqual(CountryOrRegion.FRA.search_value, "fra")
        self.assertEqual(CountryOrRegion.USA.search_value, "usa")

    def test_country_compound_name_search_value(self):
        # Compound names like ARM_AZE become "arm_aze"
        self.assertEqual(CountryOrRegion.ARM_AZE.search_value, "arm_aze")
        self.assertEqual(CountryOrRegion.CENTRAL_ASIA.search_value, "central_asia")

    def test_utilization_search_value_replaces_underscore_with_plus(self):
        self.assertEqual(Utilization.WINE_GRAPE.search_value, "wine+grape")
        self.assertEqual(Utilization.TABLE_GRAPE.search_value, "table+grape")
        self.assertEqual(Utilization.RAISIN_GRAPE.search_value, "raisin+grape")

    def test_utilization_single_word_search_value(self):
        self.assertEqual(Utilization.ROOTSTOCK.search_value, "rootstock")

    def test_utilization_value_is_display_name(self):
        self.assertEqual(Utilization.WINE_GRAPE.value, "WINE GRAPE")
        self.assertEqual(Utilization.ROOTSTOCK.value, "ROOTSTOCK")


class TestSearchValueEnum(TestCase):
    """Tests for enums inheriting from SearchValueEnum (explicit
    VIVC database id + display name)."""

    def test_search_value_is_explicit_vivc_database_id(self):
        self.assertEqual(Species.VITIS_RIPARIA.search_value, "7")
        self.assertEqual(Species.VITIS_LABRUSCA.search_value, "2")
        self.assertEqual(Species.VITIS_RUPESTRIS.search_value, "14")

    def test_search_value_non_numeric_id(self):
        self.assertEqual(Species.VITIS_VINIFERA_SUBSP_VINIFERA.search_value, "VINIFERA")
        self.assertEqual(Species.INTERSPECIFIC_CROSSING.search_value, "INTERSPECIFIC")

    def test_search_value_not_specified(self):
        self.assertEqual(Species.NOT_SPECIFIED.search_value, "0")

    def test_value_is_display_name(self):
        self.assertEqual(Species.VITIS_RIPARIA.value, "VITIS RIPARIA MICHAUX")
        self.assertEqual(
            Species.VITIS_VINIFERA_SUBSP_VINIFERA.value,
            "VITIS VINIFERA LINNÉ SUBSP. VINIFERA",
        )

    def test_search_value_differs_from_name(self):
        # The member name and search_value must not be equal for SearchValueEnum members
        self.assertNotEqual(
            Species.VITIS_RIPARIA.search_value,
            Species.VITIS_RIPARIA.name.lower(),
        )
