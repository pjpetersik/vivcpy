"""Command-line interface for searching the VIVC grape variety database.

Exposes the :mod:`vivcpy` library as a single CLI surface:

- Given search parameters, it queries the VIVC passport search by any
  combination of prime name, berry colour, country, utilization, species, and
  seed formation, returning the matching varieties, optionally expanded into
  full passport records with ``--details``.
- Given ``-id``, it returns the full passport record for that VIVC number.

Output is written as plain text or JSON to stdout, or to a file via
``--output``.

Usage:
    vivc -id N [--format {text,json}] [--output FILE]
    vivc [-name NAME] [-color COLOR] [-country COUNTRY] [-utilization UTIL]
        [-species SPECIES] [-seeds FORMATION] [--details] [--per-page N]
        [--format {text,json}] [--output FILE]
"""

import argparse
import contextlib
import json
import sys
from collections.abc import Callable, Iterable, Iterator, Sequence
from dataclasses import fields
from enum import Enum
from pathlib import Path
from typing import Any, TextIO, TypeVar

import requests

from vivcpy.enums import (
    ColorOfBerrySkin,
    CountryOrRegion,
    FormationOfSeeds,
    Species,
    Utilization,
)
from vivcpy.models import Variety
from vivcpy.search import (
    PassportDataSearch,
    PassportDataSearchParams,
    PassportDataViewSearch,
)

DEFAULT_PER_PAGE = 500
MAX_NAMES_IN_ERROR = 20
# A VIVC number that is known to exist; used only to tell a genuine empty result
# apart from the search endpoint answering every query with "No results found".
CANARY_VIVC_NUMBER = 4572
SEARCH_TEXT_FIELDS: tuple[str, ...] = (
    "variety_number_vivc",
    "prime_name",
    "color_of_berry_skin",
    "country_or_region_of_origin_of_the_variety",
    "species",
    "utilization",
)
SEARCH_FILTER_DESTS: tuple[str, ...] = (
    "prime_name",
    "color",
    "country",
    "utilization",
    "species",
    "formation_of_seeds",
)

EnumT = TypeVar("EnumT", bound=Enum)


def _enum_argument(enum_cls: type[EnumT], param_name: str) -> Callable[[str], EnumT]:
    """Build an argparse ``type`` callable that resolves a string to an enum.

    A token is accepted if it matches a member name, the display value, or the
    raw VIVC search value (case-insensitively), so ``--color GREEN``,
    ``--color BLANC``, and ``--color green`` all resolve to
    :attr:`ColorOfBerrySkin.GREEN`.

    Args:
        enum_cls: The enum type to resolve against.
        param_name: Option name used in error messages.

    Returns:
        A callable suitable for ``argparse.add_argument(type=...)``.
    """

    def parse(raw: str) -> EnumT:
        token = raw.strip().casefold()
        candidates: list[tuple[str, EnumT]] = []
        for member in enum_cls:
            if token == member.name.casefold():
                return member
            display = member.value
            if isinstance(display, str):
                candidates.append((display.casefold(), member))
            raw_value = getattr(member, "search_value", None)
            if isinstance(raw_value, str):
                candidates.append((raw_value.casefold(), member))
        for candidate, member in candidates:
            if token == candidate:
                return member

        names = [member.name for member in enum_cls]
        preview = ", ".join(names[:MAX_NAMES_IN_ERROR])
        if len(names) > MAX_NAMES_IN_ERROR:
            preview = f"{preview}, ..."
        msg = f"unknown {param_name} {raw!r}; expected one of: {preview}"
        raise argparse.ArgumentTypeError(msg)

    return parse


def _one_or_many(values: Sequence[Any] | None) -> Any:
    """Collapse argparse ``append`` values into a scalar or list.

    Args:
        values: Values collected by an ``action="append"`` argument.

    Returns:
        ``None`` when empty, the single value when one is given, otherwise the
        full list (matching :data:`vivcpy.types.OneOrMany`).
    """
    if not values:
        return None
    if len(values) == 1:
        return values[0]
    return list(values)


def _jsonable(value: Any) -> Any:
    """Recursively convert a ``Variety`` field value into a JSON-safe value."""
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    return value


def variety_to_dict(variety: Variety) -> dict[str, Any]:
    """Convert a :class:`~vivcpy.models.Variety` into a JSON-safe dict.

    Args:
        variety: The variety to serialize.

    Returns:
        A dict keyed by field name; enums become their display value and lists
        are serialized element-wise.
    """
    return {f.name: _jsonable(getattr(variety, f.name)) for f in fields(variety)}


def _text_value(value: Any) -> str:
    """Render a single ``Variety`` field value as plain text."""
    if value is None:
        return ""
    if isinstance(value, Enum):
        return str(value.value)
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, list):
        return "; ".join(_text_value(item) for item in value)
    return str(value)


def _format_search_text(varieties: Iterable[Variety]) -> Iterator[str]:
    """Yield a tab-separated search table with a header row."""
    yield "\t".join(SEARCH_TEXT_FIELDS)
    for variety in varieties:
        yield "\t".join(
            _text_value(getattr(variety, name)) for name in SEARCH_TEXT_FIELDS
        )


def _format_record_text(variety: Variety) -> Iterator[str]:
    """Yield a single passport record as ``field: value`` lines."""
    for f in fields(variety):
        yield f"{f.name}: {_text_value(getattr(variety, f.name))}"


def _write_lines(lines: Iterable[str], stream: TextIO) -> None:
    """Write each line to ``stream`` followed by a newline."""
    for line in lines:
        stream.write(f"{line}\n")


def _dump_json(payload: Any, stream: TextIO) -> None:
    """Write ``payload`` as indented UTF-8 JSON followed by a newline."""
    json.dump(payload, stream, indent=2, ensure_ascii=False)
    stream.write("\n")


@contextlib.contextmanager
def _open_output(path: str | None) -> Iterator[TextIO]:
    """Yield stdout, or the file at ``path`` opened for writing."""
    if path is None:
        yield sys.stdout
        return
    with Path(path).open("w", encoding="utf-8") as handle:
        yield handle


def _add_output_arguments(parser: argparse.ArgumentParser) -> None:
    """Add the shared ``--format`` and ``--output`` options to a subparser."""
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text).",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        metavar="FILE",
        help="Write to FILE instead of stdout.",
    )


def build_parser() -> argparse.ArgumentParser:
    """Build the ``vivc`` argument parser.

    Returns:
        The configured argument parser. ``-id`` selects single-record mode;
        any search parameter selects search mode.
    """
    parser = argparse.ArgumentParser(
        description="Search the VIVC grape variety database from the command line.",
    )
    parser.add_argument(
        "-id",
        "--id",
        dest="vivc_id",
        type=int,
        metavar="N",
        help="Fetch the full passport record for this VIVC number.",
    )
    parser.add_argument(
        "-name",
        "--prime-name",
        dest="prime_name",
        help="Prime (variety) name to search for.",
    )
    parser.add_argument(
        "-color",
        "--color",
        action="append",
        type=_enum_argument(ColorOfBerrySkin, "color"),
        metavar="COLOR",
        help="Berry skin colour (repeatable).",
    )
    parser.add_argument(
        "-country",
        "--country",
        action="append",
        type=_enum_argument(CountryOrRegion, "country"),
        metavar="COUNTRY",
        help="Country or region of origin (repeatable).",
    )
    parser.add_argument(
        "-utilization",
        "--utilization",
        action="append",
        type=_enum_argument(Utilization, "utilization"),
        metavar="UTILIZATION",
        help="Utilization, e.g. WINE_GRAPE (repeatable).",
    )
    parser.add_argument(
        "-species",
        "--species",
        action="append",
        type=_enum_argument(Species, "species"),
        metavar="SPECIES",
        help="Species (repeatable).",
    )
    parser.add_argument(
        "-seeds",
        "--formation-of-seeds",
        dest="formation_of_seeds",
        action="append",
        type=_enum_argument(FormationOfSeeds, "formation-of-seeds"),
        metavar="FORMATION",
        help="Seed formation (repeatable).",
    )
    parser.add_argument(
        "--details",
        action="store_true",
        help="Fetch the full passport record for each result.",
    )
    parser.add_argument(
        "--per-page",
        type=int,
        default=DEFAULT_PER_PAGE,
        help=f"Results per page (default: {DEFAULT_PER_PAGE}).",
    )
    _add_output_arguments(parser)
    return parser


def _search_endpoint_degraded() -> bool:
    """Report whether VIVC's search endpoint is answering every query with nothing.

    VIVC sometimes returns HTTP 200 with an empty result page for every
    passport search while its record endpoint keeps working. This probes a
    known VIVC number so a genuine no-match is not confused with an outage.

    Returns:
        ``True`` only when the canary variety is retrievable from the record
        endpoint but is missing from the search endpoint.
    """
    try:
        PassportDataViewSearch(CANARY_VIVC_NUMBER).get_variety()
    except (IndexError, ValueError, requests.RequestException):
        return False

    probe = PassportDataSearch(
        PassportDataSearchParams(variety_number_vivc=CANARY_VIVC_NUMBER),
        per_page=5,
    )
    return next(iter(probe), None) is None


def _run_search(args: argparse.Namespace) -> int:
    """Execute the ``search`` subcommand and return an exit code."""
    params = PassportDataSearchParams(
        prime_name=args.prime_name,
        color_of_berry_skin=_one_or_many(args.color),
        country_or_region_of_origin_of_the_variety=_one_or_many(args.country),
        utilization=_one_or_many(args.utilization),
        species=_one_or_many(args.species),
        formation_of_seeds=_one_or_many(args.formation_of_seeds),
    )
    search = PassportDataSearch(params, per_page=args.per_page, details=args.details)
    results = list(search)

    if not results:
        if _search_endpoint_degraded():
            print(
                "vivc: VIVC search appears to be down: the search returned no "
                f"results even for the known variety VIVC {CANARY_VIVC_NUMBER}, "
                "while its record endpoint still responds. Retry later, or use "
                "'vivc -id <N>' for a direct record lookup.",
                file=sys.stderr,
            )
            return 1
        print(
            "vivc: no matching varieties found for the given search parameters.",
            file=sys.stderr,
        )

    with _open_output(args.output) as stream:
        if args.format == "json":
            _dump_json([variety_to_dict(v) for v in results], stream)
        else:
            _write_lines(_format_search_text(results), stream)
    return 0


def _run_record(args: argparse.Namespace) -> int:
    """Execute the ``record`` subcommand and return an exit code."""
    variety = PassportDataViewSearch(args.vivc_id).get_variety()
    with _open_output(args.output) as stream:
        if args.format == "json":
            _dump_json(variety_to_dict(variety), stream)
        else:
            _write_lines(_format_record_text(variety), stream)
    return 0


def _run(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    """Dispatch to record or search mode based on the supplied arguments."""
    if args.vivc_id is not None:
        if any(getattr(args, name) for name in SEARCH_FILTER_DESTS):
            parser.error("-id/--id cannot be combined with search parameters.")
        return _run_record(args)

    if not any(getattr(args, name) for name in SEARCH_FILTER_DESTS):
        parser.error("provide -id/--id or at least one search parameter.")
    return _run_search(args)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the ``vivc`` CLI.

    Args:
        argv: Argument list (excluding the program name). Defaults to
            ``sys.argv[1:]``.

    Returns:
        Process exit code: ``0`` on success, ``1`` when the VIVC request or
        response could not be handled.
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(_run(args, parser))
    except requests.RequestException as error:
        print(f"vivc: request to VIVC failed: {error}", file=sys.stderr)
        return 1
    except (IndexError, ValueError) as error:
        print(f"vivc: could not read VIVC response: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
