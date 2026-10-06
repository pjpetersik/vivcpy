"""Enable ``python -m vivcpy`` (the ``vivc`` CLI) to run."""

from vivcpy.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
