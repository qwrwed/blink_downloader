import asyncio
import logging
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from functools import cached_property
from pathlib import Path

import filedate
import pytz
from blinkpy.auth import Auth
from blinkpy.blinkpy import Blink
from blinkpy.helpers.util import json_load
from dateutil.parser import parse
from tqdm import tqdm
from utils_python import setup_config_logging, get_platform

from blink_downloader.args import ArgsNamespace, get_args

LOGGER = logging.getLogger(__name__)



@dataclass
class BlinkVideo:
    additional_devices: list
    created_at: datetime
    deleted: bool
    device: str
    device_id: int
    device_name: str
    id: int
    media: str
    metadata: str
    network_id: int
    network_name: str
    partial: bool
    source: str
    thumbnail: str
    time_zone: str
    type: str
    updated_at: datetime
    watched: bool

    def __post_init__(self):
        if not isinstance(self.created_at, datetime):
            self.created_at = parse(self.created_at)
        self.created_at = self.created_at.astimezone(pytz.utc)

        if not isinstance(self.updated_at, datetime):
            self.updated_at = parse(self.updated_at)
        self.updated_at = self.updated_at.astimezone(pytz.utc)

    @cached_property
    def created_date(self):
        return self.created_at.date()

    @cached_property
    def filename(self):
        created_at_str = self.created_at.strftime("%Y-%m-%d_%H-%M-%SZ")
        return Path(f"{self.device_name}_{created_at_str}").with_suffix(".mp4")

    @cached_property
    def get_relative_destination(self):
        created_date_str = self.created_date.isoformat()
        return Path(self.device_name, created_date_str, self.filename)

GroupedVideos = dict[str, dict[str, dict[str, BlinkVideo]]]

def group_videos(videos: list[BlinkVideo], cameras: list[str] | None = None):
    if cameras is None:
        cameras = ["all"]

    videos_grouped: GroupedVideos = {}
    for video in videos:
        if video.device_name not in cameras and "all" not in cameras:
            LOGGER.debug("Skipping videos for %s.", video.device_name)
            continue

        if video.deleted:
            LOGGER.debug("%s: %s is marked as deleted.", video.device_name, video.media)
            continue

        device_videos = videos_grouped.setdefault(video.device_name, {})
        date_videos = device_videos.setdefault(video.created_date.isoformat(), {})
        date_videos[video.filename.name] = video

    return videos_grouped


async def download_videos(blink: Blink, videos: GroupedVideos, root_dir: Path, delay=1, debug=False):
    for device_name, device_videos in (pbar1 := tqdm(sorted(videos.items()))):
        pbar1.set_description(f"camera '{device_name}'")
        for date_str, date_videos in (
            pbar2 := tqdm(sorted(device_videos.items()), leave=False)
        ):
            pbar2.set_description(f"date   '{date_str}'")
            for video_filename, video in (
                pbar3 := tqdm(sorted(date_videos.items()), leave=False)
            ):
                pbar3.set_description(f"video  '{video_filename}'")

                address = video.media
                video_path =Path(root_dir, video.get_relative_destination) 
                video_dir = video_path.parent

                if debug:
                    print(
                        f"Camera: {device_name}, Timestamp: {video.created_at}, "
                        f"Address: {address}, Filename: {video_filename}"
                    )
                    continue
                
                
                if not video_dir.is_dir():
                    video_dir.mkdir(exist_ok=True, parents=True)

                if video_path.is_file():
                    LOGGER.info("%s already exists, skipping...", video_filename)
                    continue

                response = await blink.do_http_get(address)
                video_data = await response.read()
                with open(video_path, "wb") as vidfile:
                    vidfile.write(video_data)

                fd = filedate.File(video_path)
                fd.set(created=video.created_at, modified=video.created_at)
                LOGGER.info("Downloaded video to %s", video_filename)

                if delay > 0:
                    time.sleep(delay)


@asynccontextmanager
async def blink_session(blink: Blink):
    await blink.start()
    try:
        yield
    finally:
        await blink.auth.session.close()


async def main(args: ArgsNamespace):
    LOGGER.info("initializing...")
    blink = Blink()
    auth = Auth(await json_load(args.credentials_file))
    blink.auth = auth

    LOGGER.info(f"starting; will download to '{args.output_dir}'...")
    async with blink_session(blink):
        video_data_raw: list[dict] = await blink.get_videos_metadata(
            since=args.since, stop=args.pages
        )
        video_data = [BlinkVideo(**video) for video in video_data_raw]

        video_data_sorted = group_videos(video_data)
        await download_videos(blink, video_data_sorted, args.output_dir)


if __name__ == "__main__":
    if get_platform() == "windows":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    args = get_args()
    setup_config_logging(args.logging_config_path)
    asyncio.run(main(args))
