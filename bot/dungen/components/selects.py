from copy import deepcopy
from typing import List, Optional

import discord
from discord import ui
import logging

log = logging.getLogger(__name__)


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
    def value(self) -> str:
        return self.values[0]

    @staticmethod
    def find_select_option_index_by_value(options: List[discord.SelectOption], value: str) -> Optional[int]:
        for idx, so in enumerate(options):
            if so.value == value:
                return idx