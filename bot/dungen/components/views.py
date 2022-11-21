from __future__ import annotations
from typing import Optional, List, Union, TYPE_CHECKING

import discord
from discord import ui
from bot.dungen.choices import CAVE_MAP_STYLE_OPTIONS
from bot.dungen.components.buttons import GenerateButton, CallbackModalButton
from bot.dungen.components.generic import GeneratedMapView
from bot.dungen.components.modals import EgressModal, DensityModal
from bot.dungen.components.selects import MultiBooleanSelect, SingleSelect
from bot.dungen import choices
import logging


from bot.dungen.schema import DungenAPIRequest, CaveAPIRequest, CaveSerialized, MapSerializeable
from bot.dungen.services import generate_dungeon, make_map_embed, generate_cave, make_cave_embed
if TYPE_CHECKING:
    from bot.bot import DungenBot

log = logging.getLogger(__name__)

class DungenGenerateView(GeneratedMapView):


    def __init__(self,
                 bot: DungenBot,
                 theme_options: List[discord.SelectOption],
                 size_options: List[discord.SelectOption],
                 default_map_options: Optional[List[str]] = None,
                 **kwargs
                 ):
        super(DungenGenerateView, self).__init__(bot, theme_options, size_options, **kwargs)
        self.designation = "map"
        btn_label = "Re-Generate Map" if self.regenerated else "Generate Map"

        self.map_options = MultiBooleanSelect(
            options=choices.DUNGEON_MAP_OPTIONS,
            default_values=default_map_options,
            custom_id=f"{self.custom_id_prefix}_generated_map_options"
        )
        self.btn_generate = GenerateButton(
            label=btn_label,
            style=discord.ButtonStyle.green,
            custom_id=f"{self.custom_id_prefix}_generated_map_generate_btn"
        )
        self.add_item(self.map_options)
        self.add_item(self.btn_generate)

    async def generate(self):
        req = DungenAPIRequest(
            seed=self.seed,
            theme=self.theme_select.value,
            max_size=self.size_select.value,
            tile_size=self.tile_size,
            **self.map_options.to_dict()
        )
        dungen_response = await generate_dungeon(req)
        self.seed = dungen_response.seed_string
        self.download_url = dungen_response.full_image_url
        embed = make_map_embed(dungen_response)
        return embed

    def to_dict(self):
        return MapSerializeable(
            default_map_options=self.map_options.values,
            custom_id_prefix=self.custom_id_prefix,
            default_theme=self.theme_select.value,
            default_size=self.size_select.value,
            download_url=self.download_url,
            tile_size=self.tile_size,
            seed=self.seed,
            seed_editable=False,
            regenerated=True
        ).dict()

    def as_new_view(self, **extras):
        other = {**self.to_dict(), **extras}
        return DungenGenerateView(
            bot=self.bot,
            theme_options=choices.DUNGEN_THEME_OPTIONS,
            size_options=choices.DUNGEON_SIZE_OPTIONS,
            timeout=None,
            message=self.message,
            **other
        )



class CaveGeneratedView(GeneratedMapView):
    def __init__(self,
                 bot: DungenBot,
                 theme_options: List[discord.SelectOption],
                 size_options: List[discord.SelectOption],
                 default_map_style: Optional[str] = None,
                 default_egress: Optional[str] = None,
                 default_secret_rooms: Optional[List[str]] = None,
                 default_density: Optional[str] = None,
                 **kwargs):
        super(CaveGeneratedView, self).__init__(bot, theme_options, size_options, **kwargs)
        self.designation = "cave"
        self.density = default_density or "0"
        self.egress = default_egress or "1"
        self.map_style_select = SingleSelect(
            CAVE_MAP_STYLE_OPTIONS,
            default_value=default_map_style,
            custom_id=f"{self.custom_id_prefix}_cave_map_style"
        )
        self.secret_rooms_select = MultiBooleanSelect(
                choices.CAVE_OTHER_OPTIONS,
                default_values=default_secret_rooms,
                custom_id=f"{self.custom_id_prefix}_cave_secret_rooms"
            )
        self.add_item(self.map_style_select)
        self.add_item(self.secret_rooms_select)

        self.density_button = CallbackModalButton(
            DensityModal,
            self.on_density_change,
            label=f"Corridor Density ({self.density})",
            style=discord.ButtonStyle.blurple,
            row=4,
            custom_id=f"{self.custom_id_prefix}_cave_density"
        )
        self.add_item(self.density_button)

        self.egress_btn = ui.Button(
            label=f"Egress ({self.egress})",
            style=discord.ButtonStyle.blurple,
            row=4,
            custom_id=f"{self.custom_id_prefix}_cave_egress",
        )
        self.egress_btn.callback = lambda itx: itx.response.send_modal(EgressModal(self.on_egress_change))
        self.egress_btn = CallbackModalButton(
            EgressModal,
            self.on_egress_change,
            label=f"Egress ({self.egress})",
            style=discord.ButtonStyle.blurple,
            row=4,
            custom_id=f"{self.custom_id_prefix}_cave_egress_modal",
        )
        self.add_item(self.egress_btn)

        btn_label = "Re-Generate Cave" if self.regenerated else "Generate Cave"
        self.add_item(GenerateButton(
            label=btn_label,
            style=discord.ButtonStyle.green,
            row=4,
            custom_id=f"{self.custom_id_prefix}_cave_generate"
        ))

    async def on_density_change(self, itx: discord.Interaction, modal: DensityModal):
        self.density = modal.density.value
        self.density_button.label = f"Corridor Density ({self.density})"
        await itx.response.edit_message(view=self)

    async def on_egress_change(self, itx: discord.Interaction, modal: EgressModal):
        self.egress = modal.egress.value
        self.egress_btn.label = f"Egress ({self.egress})"
        await itx.response.edit_message(view=self)

    async def generate(self):
        req = CaveAPIRequest(
            seed=self.seed,
            theme=self.theme_select.value,
            max_size=self.size_select.value,
            tile_size=self.tile_size,
            map_style=self.map_style_select.value,
            corridor_density=float(self.density),
            egress=float(self.egress)
        )
        dungen_response = await generate_cave(req)
        self.seed = dungen_response.seed_string
        self.download_url = dungen_response.full_image_url
        embed = make_cave_embed(dungen_response)
        return embed

    def to_dict(self):
        return CaveSerialized(
            custom_id_prefix=self.custom_id_prefix,
            default_theme=self.theme_select.value,
            default_size=self.size_select.value,
            download_url=self.download_url,
            tile_size=self.tile_size,
            seed=self.seed,
            seed_editable=False,
            regenerated=True,
            default_map_style=self.map_style_select.value,
            default_egress=self.egress,
            default_density=self.density,
            default_secret_rooms=self.secret_rooms_select.values,
        ).dict()

    def as_new_view(self, **extras):
        other = {**self.to_dict(), **extras}
        return CaveGeneratedView(
            bot=self.bot,
            theme_options=choices.CAVE_THEME_OPTIONS,
            size_options=choices.CAVE_SIZE_OPTIONS,
            timeout=None,
            message=self.message,
            **other
        )