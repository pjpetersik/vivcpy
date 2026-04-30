# vivcPy

![Tests](https://github.com/pjpetersik/vivcpy/actions/workflows/tests.yaml/badge.svg)
![MyPy](https://github.com/pjpetersik/vivcpy/actions/workflows/mypy.yaml/badge.svg)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A Python connector to the [Vitis International Variety Catalogue (VIVC)](https://www.vivc.de/) database.

## Installation

```bash
pip install vivcpy
```

## Usage

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

