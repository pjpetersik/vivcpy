"""Unit tests for the :mod:`vivcpy.cli` command-line interface.

These tests mock the VIVC network calls in ``vivcpy.cli`` so they run offline.
Live end-to-end checks against the VIVC website live in ``local_test_search``.
"""

from __future__ import annotations

import argparse
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

import requests

from vivcpy.cli import (
    _enum_argument,
    _one_or_many,
    _search_endpoint_degraded,
    build_parser,
    main,
    variety_to_dict,
)
from vivcpy.enums import (
    ColorOfBerrySkin,
    CountryOrRegion,
    FormationOfSeeds,
    Species,
    Utilization,
)
from vivcpy.models import Variety


def sample_variety() -> Variety:
    """Return a fully populated :class:`Variety` for assertions."""
    return Variety(
        prime_name="REGENT",
        variety_number_vivc=4572,
        color_of_berry_skin=ColorOfBerrySkin.BLACK,
        country_or_region_of_origin_of_the_variety=CountryOrRegion.DEU,
        species=Species.VITIS_VINIFERA_SUBSP_SATIVA,
        utilization=[Utilization.WINE_GRAPE],
        synonyms=["GEILWEILERHOF 67-198-3", "GF.67-198-3"],
        loci_for_resistance=["Ren3", "Ren9"],
    )


class TestEnumArgument(unittest.TestCase):
    """CLI-UNIT-001: ``_enum_argument`` resolves member names, values, search values."""

    def test_resolves_by_member_name(self):
        parse = _enum_argument(ColorOfBerrySkin, "color")
        self.assertEqual(parse("GREEN"), ColorOfBerrySkin.GREEN)
        self.assertEqual(parse("black"), ColorOfBerrySkin.BLACK)

    def test_resolves_by_display_value(self):
        parse = _enum_argument(ColorOfBerrySkin, "color")
        self.assertEqual(parse("BLANC"), ColorOfBerrySkin.GREEN)

    def test_resolves_by_search_value(self):
        parse = _enum_argument(Species, "species")
        self.assertEqual(parse("7"), Species.VITIS_RIPARIA)
        self.assertEqual(parse("vinifera"), Species.VITIS_VINIFERA_SUBSP_VINIFERA)

    def test_rejects_unknown_value(self):
        parse = _enum_argument(ColorOfBerrySkin, "color")
        with self.assertRaises(argparse.ArgumentTypeError):
            parse("chartreuse")


class TestOneOrMany(unittest.TestCase):
    """CLI-UNIT-002: ``_one_or_many`` collapses append values."""

    def test_none_when_empty(self):
        self.assertIsNone(_one_or_many(None))
        self.assertIsNone(_one_or_many([]))

    def test_scalar_for_single(self):
        self.assertEqual(_one_or_many([ColorOfBerrySkin.RED]), ColorOfBerrySkin.RED)

    def test_list_for_many(self):
        self.assertEqual(
            _one_or_many([ColorOfBerrySkin.RED, ColorOfBerrySkin.GREEN]),
            [ColorOfBerrySkin.RED, ColorOfBerrySkin.GREEN],
        )


class TestVarietyToDict(unittest.TestCase):
    """CLI-UNIT-003: ``variety_to_dict`` produces JSON-safe values."""

    def test_enums_become_display_values_and_lists_serialize(self):
        data = variety_to_dict(sample_variety())
        self.assertEqual(data["color_of_berry_skin"], "NOIR")
        self.assertEqual(data["country_or_region_of_origin_of_the_variety"], "GERMANY")
        self.assertEqual(data["utilization"], ["WINE GRAPE"])
        self.assertEqual(data["loci_for_resistance"], ["Ren3", "Ren9"])
        json.dumps(data)  # must not raise


class TestParser(unittest.TestCase):
    """CLI-UNIT-004: parser wiring defaults and validation."""

    def test_search_defaults(self):
        args = build_parser().parse_args(["-name", "Riesling"])
        self.assertEqual(args.format, "text")
        self.assertIsNone(args.output)
        self.assertFalse(args.details)
        self.assertIsNone(args.vivc_id)

    def test_id_flag(self):
        args = build_parser().parse_args(["-id", "4572"])
        self.assertEqual(args.vivc_id, 4572)

    def test_invalid_format_rejected(self):
        with self.assertRaises(SystemExit):
            build_parser().parse_args(["-name", "X", "--format", "yaml"])

    def test_no_arguments_errors(self):
        with self.assertRaises(SystemExit):
            main([])

    def test_id_with_search_parameter_errors(self):
        with self.assertRaises(SystemExit):
            main(["-id", "4572", "-name", "X"])


class TestSearchCommand(unittest.TestCase):
    """CLI-UNIT-005: search parameters map to params and render output."""

    def test_text_output_has_header_and_row(self):
        with patch("vivcpy.cli.PassportDataSearch") as search:
            search.return_value.__iter__.return_value = iter([sample_variety()])
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                code = main(["-name", "Regent"])

        self.assertEqual(code, 0)
        lines = buffer.getvalue().splitlines()
        self.assertTrue(lines[0].startswith("variety_number_vivc\tprime_name"))
        self.assertEqual(lines[1].split("\t")[:3], ["4572", "REGENT", "NOIR"])

    def test_params_passed_to_library(self):
        with patch("vivcpy.cli.PassportDataSearch") as search:
            search.return_value.__iter__.return_value = iter([sample_variety()])
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                main(
                    [
                        "-name",
                        "Merlot",
                        "-color",
                        "RED",
                        "-country",
                        "FRA",
                        "--details",
                    ]
                )

        params = search.call_args.args[0]
        request_params = params.to_requests_params()
        self.assertEqual(request_params["PassportSearch[leitname]"], "Merlot")
        self.assertIsNone(request_params["PassportSearch[kenn_nr]"])
        self.assertEqual(request_params["PassportSearch[color][]"], "red")
        self.assertEqual(request_params["PassportSearch[country][]"], "fra")
        self.assertTrue(search.call_args.kwargs["details"])

    def test_json_output(self):
        with patch("vivcpy.cli.PassportDataSearch") as search:
            search.return_value.__iter__.return_value = iter([sample_variety()])
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                main(["-name", "Regent", "--format", "json"])

        payload = json.loads(buffer.getvalue())
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["prime_name"], "REGENT")

    def test_repeated_flag_becomes_list(self):
        with patch("vivcpy.cli.PassportDataSearch") as search:
            search.return_value.__iter__.return_value = iter([sample_variety()])
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                main(["-color", "GREEN", "-color", "BLACK"])

        params = search.call_args.args[0]
        self.assertEqual(
            params.to_requests_params()["PassportSearch[color][]"],
            ["green", "black"],
        )


class TestSearchEndpointProbe(unittest.TestCase):
    """CLI-UNIT-009: the search endpoint probe distinguishes outage from empty."""

    def test_flags_outage_when_canary_missing_from_search(self):
        with (
            patch("vivcpy.cli.PassportDataViewSearch") as view,
            patch("vivcpy.cli.PassportDataSearch") as search,
        ):
            view.return_value.get_variety.return_value = sample_variety()
            search.return_value.__iter__.return_value = iter([])
            self.assertTrue(_search_endpoint_degraded())

    def test_healthy_when_canary_found(self):
        with (
            patch("vivcpy.cli.PassportDataViewSearch") as view,
            patch("vivcpy.cli.PassportDataSearch") as search,
        ):
            view.return_value.get_variety.return_value = sample_variety()
            search.return_value.__iter__.return_value = iter([sample_variety()])
            self.assertFalse(_search_endpoint_degraded())

    def test_inconclusive_when_canary_record_unavailable(self):
        with (
            patch("vivcpy.cli.PassportDataViewSearch") as view,
            patch("vivcpy.cli.PassportDataSearch") as search,
        ):
            view.return_value.get_variety.side_effect = IndexError("no rows")
            self.assertFalse(_search_endpoint_degraded())
            search.assert_not_called()


class TestEmptySearchReporting(unittest.TestCase):
    """CLI-UNIT-010: an empty search reports an outage or a genuine no-match."""

    def test_reports_outage_and_exits_one(self):
        with (
            patch("vivcpy.cli.PassportDataSearch") as search,
            patch("vivcpy.cli._search_endpoint_degraded", return_value=True),
        ):
            search.return_value.__iter__.return_value = iter([])
            stderr = io.StringIO()
            with redirect_stdout(io.StringIO()), redirect_stderr(stderr):
                code = main(["-name", "Regent"])
        self.assertEqual(code, 1)
        self.assertIn("appears to be down", stderr.getvalue())

    def test_reports_genuine_no_match_and_exits_zero(self):
        with (
            patch("vivcpy.cli.PassportDataSearch") as search,
            patch("vivcpy.cli._search_endpoint_degraded", return_value=False),
        ):
            search.return_value.__iter__.return_value = iter([])
            stderr = io.StringIO()
            buffer = io.StringIO()
            with redirect_stdout(buffer), redirect_stderr(stderr):
                code = main(["-name", "NotAGrape"])
        self.assertEqual(code, 0)
        self.assertIn("no matching varieties", stderr.getvalue())
        self.assertTrue(buffer.getvalue().startswith("variety_number_vivc"))


class TestRecordCommand(unittest.TestCase):
    """CLI-UNIT-006: ``-id`` fetches and renders one passport record."""

    def test_text_output(self):
        with patch("vivcpy.cli.PassportDataViewSearch") as view:
            view.return_value.get_variety.return_value = sample_variety()
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                code = main(["-id", "4572"])

        self.assertEqual(code, 0)
        self.assertIn("prime_name: REGENT", buffer.getvalue())
        self.assertIn(
            "synonyms: GEILWEILERHOF 67-198-3; GF.67-198-3", buffer.getvalue()
        )
        view.assert_called_once_with(4572)

    def test_json_output(self):
        with patch("vivcpy.cli.PassportDataViewSearch") as view:
            view.return_value.get_variety.return_value = sample_variety()
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                main(["-id", "4572", "--format", "json"])

        payload = json.loads(buffer.getvalue())
        self.assertEqual(payload["variety_number_vivc"], 4572)
        self.assertEqual(payload["color_of_berry_skin"], "NOIR")


class TestOutputFile(unittest.TestCase):
    """CLI-UNIT-007: ``--output`` writes to a file instead of stdout."""

    def test_writes_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "out.json"
            with patch("vivcpy.cli.PassportDataSearch") as search:
                search.return_value.__iter__.return_value = iter([sample_variety()])
                code = main(
                    ["-name", "Regent", "--format", "json", "--output", str(target)]
                )

            self.assertEqual(code, 0)
            payload = json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual(payload[0]["prime_name"], "REGENT")


class TestMainErrorHandling(unittest.TestCase):
    """CLI-UNIT-008: network and parse failures return exit code 1."""

    def test_request_exception_returns_one(self):
        with patch("vivcpy.cli.PassportDataSearch") as search:
            search.side_effect = requests.RequestException("boom")
            with redirect_stdout(io.StringIO()):
                code = main(["-name", "X"])
        self.assertEqual(code, 1)

    def test_unparseable_record_returns_one(self):
        with patch("vivcpy.cli.PassportDataViewSearch") as view:
            view.return_value.get_variety.side_effect = IndexError("no rows")
            with redirect_stdout(io.StringIO()):
                code = main(["-id", "99999"])
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
