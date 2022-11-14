from copy import copy, deepcopy
from typing import Optional, List
from uuid import uuid4

import discord
from discord import ui, app_commands
from .choices import DUNGEON_SIZE_OPTIONS, DUNGEN_THEME_OPTIONS, DUNGEON_MAP_OPTIONS, CAVE_MAP_STYLE_OPTIONS
from .schema import DungenAPIRequest
from . import config_constants, choices
from .services import generate_dungeon, make_dungeon_embed
import logging
from typing import Callable

log = logging.getLogger(__name__)
from typing import Type

class CallbackModal(ui.Modal):
    def __init__(self, callback: Callable, **kwargs):
        super(CallbackModal, self).__init__(**kwargs)
        self.callback = callback

    async def on_submit(self, itx: discord.Interaction) -> None:
        await self.callback(itx, self)


class EgressModal(CallbackModal, title="Change Egress"):
    egress = ui.TextInput(label="Enter Egress")


class CallbackModalButton(ui.Button):
    def __init__(self, modal_type: Type[CallbackModal], modal_callback: Callable, **kwargs):
        super(CallbackModalButton, self).__init__(**kwargs)
        self.modal_type = modal_type
        self.modal_callback = modal_callback

    async def callback(self, itx: discord.Interaction) -> None:
        await itx.response.send_modal(self.modal_type(self.modal_callback))


class SeedModal(ui.Modal, title='Change Seed'):

    seed = ui.TextInput(label="Enter new Seed Value")

    def __init__(self, view: 'GeneratedMapView'):
        super(SeedModal, self).__init__()

        self.view = view

    async def on_submit(self, itx: discord.Interaction):
        self.view.seed = self.seed.value
        self.view.seed_button.label = f"Change Seed ({self.seed.value.capitalize()})"
        await itx.response.edit_message(view=self.view)

class DensityModal(CallbackModal, title='Change Corridor Density'):

    density = ui.TextInput(label="Enter a value 0, 0.1, 0.2 ... 1")

    def __init__(self, view: 'CaveGeneratedView'):
        super(DensityModal, self).__init__()
        self.view = view
        #self.view.density.default = str(self.view.density)

    async def on_submit(self, itx: discord.Interaction):
        self.view.density = self.density.value
        self.view.density_button.label = f"Corridor Density ({self.density.value})"
        await itx.response.edit_message(view=self.view)

class MultiBooleanSelect(ui.Select):
    def __init__(self, options: List[discord.SelectOption], default_values: Optional[List[str]] = None, **kwargs):
        opts = deepcopy(options)
        super(MultiBooleanSelect, self).__init__(options=opts, min_values=0, max_values=len(options), **kwargs)
        for opt in self.get_options_by_values(default_values or []):
            opt.default = True
            self._values.append(opt.value)

    async def callback(self, itx: discord.Interaction) -> None:
        log.debug("select clicked")
        self.reset_defaults()
        await itx.response.defer()
        log.debug("select deferred")

    def to_dict(self):
        result = {}
        for key in [o.value for o in self.options]:
            result[key] = key in self.values
        return result

    def reset_defaults(self):
        for opt in self.options:
            if opt.default:
                opt.default = False

    def get_options_by_values(self, values: List[str]):
        return (opt for opt in self.options if opt.value in values)


class SingleSelect(ui.Select):

    def __init__(self, options: List[discord.SelectOption], default_value: Optional[str] = None, **kwargs):
        opts = deepcopy(options)
        super(SingleSelect, self).__init__(options=opts, min_values=1, max_values=1, **kwargs)
        self.idx = self.find_select_option_index_by_value(self.options, default_value) or 0
        self.options[self.idx].default = True
        self._values = [self.options[self.idx].value]

    async def callback(self, itx: discord.Interaction) -> None:
        # Reset default
        self.options[self.idx].default = False
        await itx.response.defer()

    @property
    def value(self):
        return self.values[0]

    @staticmethod
    def find_select_option_index_by_value(options: List[discord.SelectOption], value: str) -> Optional[int]:
        for idx, so in enumerate(options):
            if so.value == value:
                return idx


class GeneratedMapView(ui.View):
    def __init__(self,
                 theme_options: List[discord.SelectOption],
                 size_options: List[discord.SelectOption],
                 custom_id_prefix: str = str(uuid4()),
                 default_theme: Optional[str] = None,
                 default_size: Optional[str] = None,
                 download_url: Optional[str] = None,
                 tile_size: int = config_constants.TILE_SIZE_REGULAR,
                 seed: str = "random",
                 seed_editable=True,
                 regenerated=False,
                 ):

        super(GeneratedMapView, self).__init__()
        self.custom_id_prefix = custom_id_prefix
        self.theme_select = SingleSelect(
            theme_options,
            default_value=default_theme,
            custom_id=f"{custom_id_prefix}_generated_map_theme"
        )
        self.size_select = SingleSelect(
            size_options,
            default_value=default_size,
            custom_id=f"{custom_id_prefix}_generated_map_size"
        )
        self.seed = seed
        self.tile_size = tile_size
        self.regenerated = regenerated
        self.seed_button = ui.Button(
            label=f"Change Seed ({self.seed.capitalize()})",
            style=discord.ButtonStyle.blurple,
            row=4,
            custom_id=f"{custom_id_prefix}_generated_map_seed"
        )
        self.seed_button.callback = self.seed_button_callback

        self.add_item(self.theme_select)
        self.add_item(self.size_select)

        if seed_editable:
            self.add_item(self.seed_button)
        if download_url:
            self.add_item(ui.Button(
                label="Download",
                url=download_url,
                row=4)
            )

    async def seed_button_callback(self, itx: discord.Interaction):
        await itx.response.send_modal(SeedModal(self))


class GenerateDungenButton(ui.Button):
    def __init__(self, **kwargs):
        super(GenerateDungenButton, self).__init__(**kwargs)

    async def callback(self, itx: discord.Interaction):
        view: DungenGenerateView = self.view
        await itx.response.defer()

        req = DungenAPIRequest(
            seed=view.seed,
            theme=view.theme_select.value,
            max_size=int(view.size_select.value),
            tile_size=view.tile_size,
            **view.options_select.to_dict()
        )
        dungen_response = await generate_dungeon(req)
        embed = make_dungeon_embed(dungen_response)
        updated_view = DungenGenerateView(
            theme_options=DUNGEN_THEME_OPTIONS,
            size_options=DUNGEON_SIZE_OPTIONS,
            default_theme=view.theme_select.value,
            default_size=view.size_select.value,
            default_options=view.options_select.values,
            tile_size=view.tile_size,
            seed=dungen_response.seed_string,
            seed_editable=False,
            download_url=dungen_response.full_image_url,
            regenerated=True
        )
        if view.regenerated:
            await itx.followup.edit_message(itx.message.id, embed=embed, view=updated_view)
        else:
            await itx.followup.send(embed=embed, view=updated_view)


class DungenGenerateView(GeneratedMapView):
    def __init__(self,
                 theme_options: List[discord.SelectOption],
                 size_options: List[discord.SelectOption],
                 default_options: Optional[List[str]] = None,
                 **kwargs):
        super(DungenGenerateView, self).__init__(theme_options, size_options, **kwargs)
        self.options_select = MultiBooleanSelect(
            DUNGEON_MAP_OPTIONS,
            default_values=default_options,
            placeholder="Choose Map Options"
        )
        self.add_item(self.options_select)

        btn_label = "Re-Generate Map" if self.regenerated else "Generate Map"
        self.add_item(GenerateDungenButton(label=btn_label, style=discord.ButtonStyle.green, row=4))


class CaveGeneratedView(GeneratedMapView):
    def __init__(self,
                 theme_options: List[discord.SelectOption],
                 size_options: List[discord.SelectOption],
                 default_map_style: Optional[str] = None,
                 default_egress: Optional[str] = None,
                 default_options: Optional[str] = None,
                 default_density: Optional[str] = None,
                 **kwargs):
        super(CaveGeneratedView, self).__init__(theme_options, size_options, **kwargs)
        self.density = default_density or "0"
        self.egress = default_egress or "1"
        self.map_style_select = SingleSelect(CAVE_MAP_STYLE_OPTIONS, default_value=default_map_style)
        #self.corridor_select = SingleSelect(choices.CAVE_CORRIDOR_DENSITY_OPTIONS, default_value=default_corridor)
        #self.egress_select = SingleSelect(choices.CAVE_EGRESS_OPTIONS, default_value=default_egress)
        self.secret_rooms_select = MultiBooleanSelect(choices.CAVE_OTHER_OPTIONS, default_values=default_options)
        self.add_item(self.map_style_select)

        self.density_button = CallbackModalButton(
            DensityModal,
            self.on_density_change,
            label=f"Corridor Density ({self.density})",
            style=discord.ButtonStyle.blurple,
            row=4,
            custom_id=f"{self.custom_id_prefix}_generated_map_density"
        )
        self.add_item(self.density_button)


        self.egress_btn = ui.Button(
            label=f"Egress ({self.egress})",
            style=discord.ButtonStyle.blurple,
            row=4,
            custom_id=f"{self.custom_id_prefix}_generated_map_egress",
        )
        self.egress_btn.callback = lambda itx: itx.response.send_modal(EgressModal(self.on_egress_change))
        self.egress_btn = CallbackModalButton(
            EgressModal,
            self.on_egress_change,
            label=f"Egress ({self.egress})",
            style=discord.ButtonStyle.blurple,
            row=4,
            custom_id=f"{self.custom_id_prefix}_generated_map_egress",
        )
        self.add_item(self.egress_btn)

    async def on_density_change(self, itx: discord.Interaction, modal: DensityModal):
        self.density = modal.density.value
        self.density_button.label = f"Corridor Density ({self.density})"
        await itx.response.edit_message(view=self)

    async def on_egress_change(self, itx: discord.Interaction, modal: EgressModal):
        self.egress = modal.egress.value
        self.egress_btn.label = f"Egress ({self.egress})"
        await itx.response.edit_message(view=self)
