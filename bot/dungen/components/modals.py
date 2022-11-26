from __future__ import annotations

import logging
from typing import Callable, TYPE_CHECKING

import discord
from discord import ui

if TYPE_CHECKING:
    from bot.dungen.components.generic import GeneratedMapView

log = logging.getLogger(__name__)


class CallbackModal(ui.Modal):
    def __init__(self, callback: Callable, validation_failed = False, **kwargs):
        super(CallbackModal, self).__init__(**kwargs)
        self.callback = callback

    def validate(self) -> bool:
        raise NotImplementedError

    async def on_submit(self, itx: discord.Interaction) -> None:
        if self.validate():
            await self.callback(itx, self)
        else:
            raise ValueError


class EgressModal(CallbackModal, title="Change Egress"):
    egress = ui.TextInput(label="Enter Egress between 0 and 9")

    def __init__(self, callback: Callable, validation_failed = False, **kwargs):
        super(EgressModal, self).__init__(callback, validation_failed, **kwargs)

    def validate(self) -> bool:
        try:
            value = float(self.egress.value)
            return value in range(0, 10) or value in map(float, range(0, 10))
        except (ValueError, TypeError):
            return False


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
    density = ui.TextInput(label="Enter Density between 0 and 10")

    def validate(self) -> bool:
        try:
            value = int(self.density.value)
            return value in range(11)
        except (ValueError, TypeError):
            return False