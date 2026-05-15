# vivcPy 🍇

![Tests](https://github.com/pjpetersik/vivcpy/actions/workflows/tests.yaml/badge.svg)
![MyPy](https://github.com/pjpetersik/vivcpy/actions/workflows/mypy.yaml/badge.svg)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A Python library for retrieving passport data from the [Vitis International Variety Catalogue (VIVC)](https://www.vivc.de/). Its goal is to strengthen the digital ecosystem and interoperability within the viticulture sector by making variety data easily accessible. The VIVC variety number serves as a unique identifier to unambiguously reference grape varieties across digital tools, and this package allows you to programmatically retrieve and integrate that data into your workflows.

Currently, only passport data is covered. However, the VIVC database contains much more data that is not yet supported. Contributions are welcome!

## Installation

```bash
pip install vivcpy
```
> [!WARNING]
> This library is still in early development. Breaking changes may occur between versions, so pinning to a specific version is recommended.

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

