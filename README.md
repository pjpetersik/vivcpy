# vivcPy 🍇

![Tests](https://github.com/pjpetersik/vivcpy/actions/workflows/tests.yaml/badge.svg)
![MyPy](https://github.com/pjpetersik/vivcpy/actions/workflows/mypy.yaml/badge.svg)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A Python library for retrieving passport data from the [Vitis International Variety Catalogue (VIVC)](https://www.vivc.de/) via web scraping. Its goal is to strengthen the digital ecosystem and interoperability within the viticulture sector by making variety data easily accessible. The VIVC variety number serves as a unique identifier to unambiguously reference grape varieties across digital tools, and this package allows you to programmatically retrieve and integrate that data into your workflows.

The same lookups are available from the command line through the bundled `vivc` command; see [Command-line interface](#command-line-interface).

Currently, only passport data is covered. However, the VIVC database contains much more data that is not yet supported. Contributions are welcome!

## Installation

```bash
pip install vivcpy
```
This installs the `vivc` command (and a `vivcpy` alias) alongside the library.

> [!WARNING]
> This library is still in early development. Breaking changes may occur between versions, so pinning to a specific version is recommended.

## Library usage

```python
from vivcpy.search import PassportDataSearch, PassportDataSearchParams
from vivcpy.enums import ColorOfBerrySkin, Species

params = PassportDataSearchParams(
    color_of_berry_skin=ColorOfBerrySkin.RED,
    species=Species.VITIS_VINIFERA_SUBSP_SATIVA,
)

for variety in PassportDataSearch(params):
    print(variety.prime_name)
```

Collect all results into a list:

```python
varieties = list(PassportDataSearch(params))
```

## Command-line interface

The package also installs a `vivc` command (with a `vivcpy` alias) that exposes
the same lookups as a single CLI surface. Passing `-id` returns one full
passport record; passing any search parameter runs a search. Every search
parameter is optional, so you can query by any combination of them.

```bash
# Fetch one passport record by VIVC number
vivc -id 4572

# Search by name and print a tab-separated table
vivc -name Riesling

# Search by any parameter (repeatable flags allow multiple values)
vivc -country FRA -color RED -utilization WINE_GRAPE --format json

# Expand each search hit into a full passport record
vivc -name Regent --details --output regent.json --format json

# Equivalent to the console script
python -m vivcpy -id 4572 --format json
```

Search flags: `-name`/`--prime-name`, `-color`/`--color`,
`-country`/`--country`, `-utilization`/`--utilization`,
`-species`/`--species`, and `-seeds`/`--formation-of-seeds`. The enum-valued
flags accept the member name (`GREEN`), the display value (`BLANC`), or the raw
VIVC search value (`green`).

Output is written to stdout by default. Use `--format {text,json}` to choose the
encoding and `-o FILE`/`--output FILE` to write to a file instead.

### When a search returns nothing

VIVC's search endpoint occasionally answers every request with HTTP 200 and "no
results" while its record endpoint keeps working. To avoid reporting that as an
empty result, `vivc` probes a known variety before trusting an empty search:

- VIVC search looks degraded: an explanatory message goes to stderr and the
  command exits `1` (nothing is written to stdout or the output file).
- A genuine no-match: a short note goes to stderr and the command exits `0`.

The record lookup (`vivc -id <N>`) is unaffected by search outages.

## Development

Install dev dependencies:

```bash
pip install -e ".[dev]"
```

Run tests:

```bash
python -m unittest tests
```

Format code:

```bash
black vivcpy tests
```
