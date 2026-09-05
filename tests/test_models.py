from unittest import TestCase
from unittest.mock import patch
from vivcpy.enums import ColorOfBerrySkin, Species
from vivcpy.models import Variety


class TestVarietyAnd(TestCase):
    """Tests for the Variety.__and__ merge method."""

    def _make_variety(self, **kwargs) -> Variety:
        defaults = {"prime_name": "RIESLING", "variety_number_vivc": 10077}
        return Variety(**{**defaults, **kwargs})

    @patch("vivcpy.models.logging.warning")
    def test_self_values_take_precedence(self, mock_logging):
        a = self._make_variety(breeder="Alice", taste="sweet")
        b = self._make_variety(breeder="Bob", taste="dry")
        result = a & b
        self.assertEqual(result.breeder, "Alice")
        self.assertEqual(result.taste, "sweet")
        self.assertEqual(mock_logging.call_count, 2)

    def test_falls_back_to_other_when_none(self):
        a = self._make_variety(breeder=None, taste=None)
        b = self._make_variety(breeder="Bob", taste="dry")
        result = a & b
        self.assertEqual(result.breeder, "Bob")
        self.assertEqual(result.taste, "dry")

    def test_mixed_merge(self):
        a = self._make_variety(
            color_of_berry_skin=ColorOfBerrySkin.GREEN,
            species=None,
        )
        b = self._make_variety(
            color_of_berry_skin=None,
            species=Species.VITIS_VINIFERA_SUBSP_VINIFERA,
        )
        result = a & b
        self.assertEqual(result.color_of_berry_skin, ColorOfBerrySkin.GREEN)
        self.assertEqual(result.species, Species.VITIS_VINIFERA_SUBSP_VINIFERA)

    def test_both_none_stays_none(self):
        a = self._make_variety(breeder=None)
        b = self._make_variety(breeder=None)
        result = a & b
        self.assertIsNone(result.breeder)

    def test_identity_fields_preserved(self):
        a = self._make_variety()
        b = self._make_variety()
        result = a & b
        self.assertEqual(result.prime_name, "RIESLING")
        self.assertEqual(result.variety_number_vivc, 10077)

    def test_raises_on_different_prime_name(self):
        a = self._make_variety(prime_name="RIESLING")
        b = self._make_variety(prime_name="MERLOT")
        with self.assertRaises(ValueError):
            a & b

    def test_raises_on_different_vivc_number(self):
        a = self._make_variety(variety_number_vivc=1)
        b = self._make_variety(variety_number_vivc=2)
        with self.assertRaises(ValueError):
            a & b
