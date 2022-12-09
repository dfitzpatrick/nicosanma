from __future__ import annotations

from typing import Optional, Union, Literal, List

from pydantic import BaseModel


class ViewSerializable(BaseModel):
    custom_id_prefix: str
    tile_size: int
    seed: str
    default_theme: Optional[str] = None
    default_size: Optional[str] = None
    download_url: Optional[str] = None
    seed_editable: bool = True
    seed_edited: bool = False
    regenerated: bool = False
    user_id: Optional[int] = None
    guild_id: Optional[int] = None
    finalized: bool = False
    upscaled: bool = False
    user_display_name: Optional[str] = None
    user_avatar_url: Optional[str] = None



class MapSerializeable(ViewSerializable):
    default_map_options: Optional[List[str]] = None


class CaveSerialized(ViewSerializable):
    default_map_style: Optional[str] = None
    default_egress: Optional[str] = None
    default_density: Optional[str] = None
    default_secret_rooms: Optional[List[str]] = None
    theme_applied: bool = False


class GeneratedAPIRequest(BaseModel):
    seed: str
    theme: str
    max_size: int
    tile_size: int
    discord_id: str


class DungenAPIRequest(GeneratedAPIRequest):
    multi_level: bool = False
    trap: bool = False


class CaveAPIRequest(GeneratedAPIRequest):
    map_style: str
    corridor_density: float = 0
    egress: float = 1.0
    secret_rooms: bool
    layout: bool = True


class GeneratedAPIResponse(BaseModel):
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
    def tile_size(self):
        # Parse strings to get max tile size (pixel size / max_tile_size
        try:
            pixel_size = int(self.pixel_size.split()[0])
            max_size = int(self.max_tile_size.split()[0])
            tile_size = pixel_size / max_size
            return f"{tile_size:.0f}px grid"
        except (ValueError, TypeError):
            return "Unknown px Grid"


    @property
    def max_tile_size_fmt(self):
        return f"{self.max_tile_size} ({self.tile_size})"


class DungenAPIResponse(GeneratedAPIResponse):
    pass


class CaveAPIResponse(GeneratedAPIResponse):
    pass
