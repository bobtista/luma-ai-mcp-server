import asyncio
import logging
import sys
from pathlib import Path

import click

from .server import serve


@click.command()
@click.option("--api-key", envvar="LUMA_API_KEY", help="Luma API key")
@click.option("-v", "--verbose", count=True)
def main(api_key: str | None, verbose: bool) -> None:
    """MCP Luma Server - Luma AI video generation functionality for MCP"""

    logging_level = logging.WARN
    if verbose == 1:
        logging_level = logging.INFO
    elif verbose >= 2:
        logging_level = logging.DEBUG

    logging.basicConfig(level=logging_level, stream=sys.stderr)
    asyncio.run(serve(api_key))


if __name__ == "__main__":
    main()
