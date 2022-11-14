from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

class GeneratedAPIRequest(BaseModel):
    seed: str
    theme: str
    max_size: int
    tile_size: int

class DungenAPIRequest(GeneratedAPIRequest):
    multi_level: bool = False
    trap: bool = False

class CaveAPIRequest(GeneratedAPIRequest):
    map_style: str
    corridor_density: float = 0
    egress: float = 1.0

class DungenAPIResponse(BaseModel):
    image_url: str
    max_tile_size: str
    file_size: str
    seed_string: str
    pixel_size: str
    path_text: Optional[str] = None

    @property
    def full_image_url(self):
        base = "https://dungen.app"
        return self.image_url.replace("..", base)

    @property
    def file_size_fmt(self):
        return self.file_size + "MB"

    @property
    def max_tile_size_fmt(self):
        return self.max_tile_size + " px grid"

