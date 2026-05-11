from unittest import TestCase

from vivcpy.enums import ColorOfBerrySkin
from vivcpy.search import PassportDataSearchParams


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
