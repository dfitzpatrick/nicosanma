from __future__ import annotations

import logging
from decimal import Decimal
from functools import partial
from typing import Optional, List, TYPE_CHECKING, Any

import discord
from discord import ui

from bot.dungen import choices, config_constants
from bot.dungen.choices import CAVE_MAP_STYLE_OPTIONS
from bot.dungen.components.buttons import GenerateButton, CallbackModalButton, FinalizeButton, CaveFinalizeButton, \
    UpscaleButton
from bot.dungen.components.generic import GeneratedMapView
from bot.dungen.components.modals import EgressModal, DensityModal
from bot.dungen.components.selects import MultiBooleanSelect, SingleSelect
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
        self.designation = "map"
        super(DungenGenerateView, self).__init__(bot, theme_options, size_options, **kwargs)
        btn_label = "Edit Map" if self.regenerated else "Generate Map"

        self.map_options = MultiBooleanSelect(
            placeholder="Additional Options",
            options=choices.DUNGEON_MAP_OPTIONS,
            default_values=default_map_options,
            custom_id=f"{self.custom_id_prefix}_generated_map_options"
        )
        self.btn_generate = GenerateButton(
            label=btn_label,
            style=discord.ButtonStyle.green,
            custom_id=f"{self.custom_id_prefix}_generated_map_generate_btn",
            row=4
        )
        self.btn_finalize = FinalizeButton(
            label="Finalize",
            style=discord.ButtonStyle.red,
            custom_id=f"{self.custom_id_prefix}_generated_map_finalize_btn",
            row=4
        )
        self.add_item(self.map_options)
        self.add_item(self.btn_generate)
        if self.regenerated:
            self.add_item(self.btn_finalize)

        self.handle_finalized()

    @property
    def default_seed(self):
        return "random"

    def add_upscale_button(self):
        btn_upscale = UpscaleButton(
            always_allow=False,
            label="Upscale & Finalize",
            style=discord.ButtonStyle.red,
            row=4,
            custom_id=f"{self.custom_id_prefix}_generated_map_upscale",
            pre_hook=self.on_upscale,
            error_hook=self.on_apply_error
        )
        self.add_item(btn_upscale)
        return btn_upscale


    async def on_upscale(self, itx: discord.Interaction, button: FinalizeButton):
        await self.edit_button_status(disabled=True)
        self.finalized = True

    async def on_apply_error(self, itx: discord.Interaction, button: UpscaleButton, exception: Any):
        await self.edit_button_status(disabled=False)
        self.finalized = False
        await self.message.edit(embed=self.result_embed_cache, view=self)


    async def generate(self, finalize: bool = False):
        req = DungenAPIRequest(
            seed=self.seed,
            theme=self.theme_select.value,
            max_size=self.size_select.value,
            tile_size=self.tile_size,
            discord_id=config_constants.UPSCALE_TOKEN,
            **self.map_options.to_dict()
        )
        dungen_response = await generate_dungeon(req)

        #if self.regenerated:
        self.seed = dungen_response.seed_string
        self.download_url = dungen_response.full_image_url
        embed = make_map_embed(dungen_response, finalized=finalize)
        self.result_embed_cache = embed
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
            seed_edited=self.seed_edited,
            regenerated=True,
            user_id=self.user_id,
            guild_id=self.guild_id,
            finalized=self.finalized,
            upscaled=self.upscaled,
            user_display_name=self.user_display_name,
            user_avatar_url=self.user_avatar_url

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
                 seed="",
                 default_map_style: Optional[str] = None,
                 default_egress: Optional[str] = None,
                 default_secret_rooms: Optional[List[str]] = None,
                 default_density: Optional[str] = None,
                 theme_applied: bool = False,
                 **kwargs):
        self.designation = "cave"
        super(CaveGeneratedView, self).__init__(bot, theme_options, size_options, seed=seed, **kwargs)
        if not self.regenerated:
            # reset the seed
            self.seed = ""
        self.theme_applied = theme_applied
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
                custom_id=f"{self.custom_id_prefix}_cave_secret_rooms",
                placeholder="Additional Options"
            )
        self.add_item(self.map_style_select)
        self.add_item(self.secret_rooms_select)

        self.density_button = CallbackModalButton(
            DensityModal,
            self.on_density_change,
            label=f"Corridor Density ({self.density_display})",
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
        self.seed = seed
        btn_label = "Edit Cave Layout" if self.regenerated else "Generate Cave Layout"
        if not self.theme_applied:
            self.add_item(GenerateButton(
                label=btn_label,
                style=discord.ButtonStyle.green,
                row=4,
                custom_id=f"{self.custom_id_prefix}_cave_generate"
            ))
        if self.regenerated:
            self.btn_finalize = CaveFinalizeButton(
                label="Apply Theme",
                style=discord.ButtonStyle.red,
                custom_id=f"{self.custom_id_prefix}_generated_map_finalize_btn",
                row=4
            )
            #self.btn_finalize.callback = partial(self.on_apply_theme, button=self.btn_finalize)
            self.add_item(self.btn_finalize)

        self.handle_finalized()

    @property
    def default_seed(self):
        return ""

    @property
    def density_display(self):
        if self.density != "0":
            return Decimal(self.density) / Decimal('0.1')
        return "0"

    def add_upscale_button(self):
        btn_upscale = UpscaleButton(
            always_allow=False,
            label="Upscale (& Apply Theme)",
            style=discord.ButtonStyle.red,
            row=4,
            custom_id=f"{self.custom_id_prefix}_generated_cave_upscale",
            pre_hook=self.on_upscale,
            error_hook=self.on_apply_error
        )
        self.add_item(btn_upscale)
        return btn_upscale

    async def on_density_change(self, itx: discord.Interaction, modal: DensityModal):
        self.density = str(int(modal.density.value) * Decimal('0.1'))
        self.density_button.label = f"Corridor Density ({self.density_display})"
        await itx.response.edit_message(view=self)

    async def on_egress_change(self, itx: discord.Interaction, modal: EgressModal):
        self.egress = modal.egress.value
        self.egress_btn.label = f"Egress ({self.egress})"
        await itx.response.edit_message(view=self)

    async def on_upscale(self, itx: discord.Interaction, button: FinalizeButton):
        await self.on_apply_theme(itx, button)



    async def on_apply_theme(self, itx: discord.Interaction, button: FinalizeButton):
        log.debug("In apply theme")
        await self.edit_button_status(disabled=True)
        self.theme_applied = True
        self.finalized = True

    async def on_apply_error(self, itx: discord.Interaction, button: UpscaleButton, exception: Any):
        await self.edit_button_status(disabled=False)
        await self.message.edit(embed=self.result_embed_cache, view=self)


    async def generate(self, finalize: bool = False):
        other_options = self.secret_rooms_select.to_dict()
        req = CaveAPIRequest(
            seed=self.seed,
            theme=self.theme_select.value,
            max_size=self.size_select.value,
            tile_size=self.tile_size,
            map_style=self.map_style_select.value,
            secret_rooms=other_options.get('secret_rooms', False),
            corridor_density=float(self.density),
            discord_id=config_constants.UPSCALE_TOKEN,
            egress=float(self.egress),
            layout=not finalize
        )
        exclude_seed = req.seed == ''

        dungen_response = await generate_cave(req, exclude_seed=exclude_seed)
        #if self.regenerated:
        self.seed = dungen_response.seed_string
        self.download_url = dungen_response.full_image_url
        embed = make_cave_embed(dungen_response, finalized=self.finalized)
        self.result_embed_cache = embed
        log.debug(str(embed))
        return embed

    @property
    def applying_theme_embed(self):
        embed = discord.Embed(
            title="Applying your Theme Settings",
            description="Please wait. This may take a moment while the image generates"
        )
        embed.set_author(
            name=config_constants.SERVICE_NAME,
            url=config_constants.PATREON_URL,
            icon_url=config_constants.SERVICE_ICON
        )
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
            seed_edited=self.seed_edited,
            regenerated=True,
            default_map_style=self.map_style_select.value,
            default_egress=self.egress,
            default_density=self.density,
            default_secret_rooms=self.secret_rooms_select.values,
            user_id=self.user_id,
            guild_id=self.guild_id,
            theme_applied=self.theme_applied,
            finalized=self.finalized,
            upscaled=self.upscaled,
            user_display_name=self.user_display_name,
            user_avatar_url=self.user_avatar_url

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
    