from __future__ import annotations

import discord
from discord import app_commands

DUNGEON_SIZE_CHOICES = [
    app_commands.Choice(name='(Size) Mini', value=4),
    app_commands.Choice(name='(Size) Tiny', value=6),
    app_commands.Choice(name='(Size) Small', value=16),
    app_commands.Choice(name='(Size) Medium', value=40),
    app_commands.Choice(name='(Size) Large', value=80),
    app_commands.Choice(name='(Size) Huge', value=120),
]
CAVE_SIZE_OPTIONS = [
    discord.SelectOption(label="(Size) Mini", value="12"),
    discord.SelectOption(label="(Size) Tiny", value="20"),
    discord.SelectOption(label="(Size) Small", value="30"),
    discord.SelectOption(label="(Size) Medium", value="40", default=True),
    discord.SelectOption(label="(Size) Large", value="50"),
]
CAVE_MAP_STYLE_OPTIONS = [
    discord.SelectOption(label="(Layout) Small Rooms", value="s_rooms"),
    discord.SelectOption(label="(Layout) Large Rooms", value="l_rooms", default=True),
    discord.SelectOption(label="(Layout) Large Area", value="l_area"),
]
CAVE_THEME_OPTIONS = [
    discord.SelectOption(label="(Theme) Original", value="original")
]
CAVE_CORRIDOR_DENSITY_OPTIONS = [
    discord.SelectOption(label=f"{x} Corridor Density", value=str(x))
    for x in [f"{x*0.1:.1f}" for x in range(0, 11)]
]
CAVE_EGRESS_OPTIONS = [
    discord.SelectOption(label=str(x), value=str(x))
    for x in range(0, 10)
]
CAVE_OTHER_OPTIONS = [
    discord.SelectOption(label="Remove Un-Connected Rooms", value="secret_rooms")
]
DUNGEON_SIZE_OPTIONS = [
    discord.SelectOption(label='(Size) Mini', value='4'),
    discord.SelectOption(label='(Size) Tiny', value='6'),
    discord.SelectOption(label='(Size) Small', value='16'),
    discord.SelectOption(label='(Size) Medium', value='40', default=True),
    discord.SelectOption(label='(Size) Large', value='80'),
    discord.SelectOption(label='(Size) Huge', value='120'),
]

DUNGEON_MAP_OPTIONS = [
    discord.SelectOption(label="Multi-level", value="multi_level"),
    discord.SelectOption(label="Special Rooms", value="trap"),
]
DUNGEN_THEME_OPTIONS = [
    discord.SelectOption(label='(Theme) Original', value='original'),
    discord.SelectOption(label='(Theme) Ice Temple', value='ice_temple'),
    discord.SelectOption(label='(Theme) Stylized Gray', value='stylized_gray'),
    discord.SelectOption(label='(Theme) Paper White', value='black_white'),
    discord.SelectOption(label='(Theme) Stylized White', value='stylized_white'),
    discord.SelectOption(label='(Theme) Classic Blue', value='classic_blue'),
    discord.SelectOption(label='(Theme) Virtual World', value='virtual_world'),
    discord.SelectOption(label='(Theme) Mask for Image Editors', value='mask'),
]
THEME_CHOICES = [app_commands.Choice(name=opt.label, value=opt.value) for opt in DUNGEN_THEME_OPTIONS]