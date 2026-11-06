"""Download the source files, keeping only companies from the registry file."""
import dataclasses
import http.client
import io
import json
import shutil
import time
from pathlib import Path
from urllib.request import Request, urlopen

from registry_filter import FilterStats, filter_registry


class DownloadError(Exception):
    pass


def _save_filtered_registry(response, part_path):
    stats = FilterStats()
    text = io.TextIOWrapper(response, encoding="utf-8", newline="\n")
    with open(part_path, "w", encoding="utf-8") as output:
        for line in filter_registry(text, stats):
            output.write(line + "\n")
    return stats


def _save_as_is(response, part_path):
    with open(part_path, "wb") as output:
        shutil.copyfileobj(response, output)


def download(source, dest_dir, opener=urlopen, retries=3, wait_seconds=10):
    """Save one source in dest_dir and return its path. An existing file is kept."""
    dest_dir = Path(dest_dir)
    final_path = dest_dir / source.key
    if final_path.exists():
        return final_path

    part_path = dest_dir / f"{source.key}.part"
    request = Request(source.url, headers={"User-Agent": "Mozilla/5.0"})

    for attempt in range(1, retries + 1):
        try:
            with opener(request, timeout=120) as response:
                if source.kind == "firms":
                    stats = _save_filtered_registry(response, part_path)
                    stats_path = dest_dir / f"{source.key}.stats.json"
                    stats_path.write_text(json.dumps(dataclasses.asdict(stats)))
                else:
                    _save_as_is(response, part_path)
            part_path.rename(final_path)
            return final_path
        except (OSError, http.client.HTTPException) as error:
            part_path.unlink(missing_ok=True)
            if attempt == retries:
                raise DownloadError(
                    f"Could not download {source.key} from {source.url}: {error}"
                ) from error
            time.sleep(wait_seconds)
