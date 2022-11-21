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
    regenerated: bool = False


class MapSerializeable(ViewSerializable):
    default_map_options: Optional[List[str]] = None


class CaveSerialized(ViewSerializable):
    default_map_style: Optional[str] = None
    default_egress: Optional[str] = None
    default_density: Optional[str] = None
    default_secret_rooms: Optional[List[str]] = None



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
    def max_tile_size_fmt(self):
        return self.max_tile_size + " px grid"


class DungenAPIResponse(GeneratedAPIResponse):
    pass

class CaveAPIResponse(GeneratedAPIResponse):
    pass
