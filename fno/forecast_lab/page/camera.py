"""The page's picture (story FL1-1c): a port, and headless Chromium behind it. Chromium draws the page in a tall
window and the empty page background below the content is trimmed, so the picture is the whole page. A failure
raises `PictureFailed`; the caller then posts the HTML file and a text summary, and says so (never silently)."""

from __future__ import annotations

import subprocess
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path

CHROMIUM = Path("/opt/pw-browsers/chromium")
WIDTH, TALL, SCALE = 1100, 4000, 2  # CSS pixels wide, the window's height, device pixels per CSS pixel
PAGE_RGB = (247, 247, 249)  # the page background (#f7f7f9): what is trimmed
MARGIN = 24  # CSS pixels of background kept below the content
TIMEOUT_SECONDS = 90


class PictureFailed(RuntimeError):
    """The picture could not be made; the reason is in the message."""


class PageCamera(ABC):
    @abstractmethod
    def picture(self, html: str, out: Path) -> Path:
        """Write a PNG of `html` to `out`, or raise `PictureFailed`."""


class ChromiumCamera(PageCamera):
    def __init__(self, executable: Path = CHROMIUM, width: int = WIDTH, scale: int = SCALE):
        self.executable, self.width, self.scale = executable, width, scale

    def picture(self, html: str, out: Path) -> Path:
        if not self.executable.exists():
            raise PictureFailed(f"no Chromium at {self.executable}")
        with tempfile.TemporaryDirectory() as folder:
            page, raw = Path(folder) / "page.html", Path(folder) / "raw.png"
            page.write_text(html, encoding="utf-8")
            self._shoot(page, raw)
            try:
                trim(raw, out, MARGIN * self.scale)
            except (OSError, ValueError, ImportError) as error:  # no Pillow, or a picture it cannot read
                raise PictureFailed(f"the picture could not be trimmed: {_named(error)}") from error
        return out

    def _shoot(self, page: Path, raw: Path) -> None:
        command = [str(self.executable), "--headless=new", "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
                   "--disable-extensions", "--no-first-run", f"--window-size={self.width},{TALL}",
                   f"--force-device-scale-factor={self.scale}", f"--screenshot={raw}", page.as_uri()]  # fmt: skip
        try:
            done = subprocess.run(command, capture_output=True, text=True, timeout=TIMEOUT_SECONDS, check=False)
        except (OSError, subprocess.TimeoutExpired) as error:
            raise PictureFailed(f"Chromium did not finish: {type(error).__name__}") from error
        if not raw.exists():
            raise PictureFailed(f"Chromium wrote no picture (exit {done.returncode})")


def _named(error: Exception) -> str:
    """The error's kind, and for an import the module that is missing (23 Oct: a bare "ImportError" hid which)."""
    module = error.name if isinstance(error, ImportError) else None
    return f"{type(error).__name__} (module {module})" if module else type(error).__name__


def trim(raw: Path, out: Path, margin: int) -> None:
    """Cut the page background off the bottom, keeping `margin` pixels; a page taller than the window is kept whole."""
    from PIL import Image, ImageChops

    with Image.open(raw) as image:
        rgb = image.convert("RGB")
        content = ImageChops.difference(rgb, Image.new("RGB", rgb.size, PAGE_RGB)).getbbox()
        bottom = content[3] if content else rgb.size[1]
        rgb.crop((0, 0, rgb.size[0], min(rgb.size[1], bottom + margin))).save(out, optimize=True)
