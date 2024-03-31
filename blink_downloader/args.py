from datetime import datetime
from pathlib import Path

from configargparse import ArgumentParser, Namespace
from utils_python import get_platform

from blink_downloader.utils import datetime_to_str


class ArgsNamespace(Namespace):
    output_dir: Path
    since: str
    pages: int
    credentials_file: Path
    arrange: bool


def get_args():
    parser = ArgumentParser()
    parser.add_argument(
        "-c",
        "--app-config-path",
        is_config_file=True,
        default="config/app.yaml",
        help="Path to app config file",
        type=Path,
    )
    parser.add_argument(
        "-l",
        "--logging-config-path",
        default=f"config/logging_{get_platform()}.cfg",
        help="Path to logging config file (default: %(default)r)",
        type=Path,
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        default="./downloads",
        type=Path,
        help="default: '%(default)s'",
    )
    parser.add_argument(
        "-s",
        "--since",
        default=datetime_to_str(
            datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        ),
        type=str,
        help="default: '%(default)s'",
    )
    parser.add_argument(
        "-p",
        "--pages",
        default=10,
        type=int,
        help="default: %(default)s",
    )
    parser.add_argument(
        "-f",
        "--credentials-file",
        default="config/credentials.json",
        type=Path,
        help="default: '%(default)s'",
    )
    return parser.parse_args(namespace=ArgsNamespace())
