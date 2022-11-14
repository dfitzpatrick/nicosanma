from __future__ import annotations

from discord import app_commands
import discord
DUNGEON_SIZE_CHOICES = [
    app_commands.Choice(name='Mini', value=4),
    app_commands.Choice(name='Tiny', value=6),
    app_commands.Choice(name='Small', value=16),
    app_commands.Choice(name='Medium', value=40),
    app_commands.Choice(name='Large', value=80),
    app_commands.Choice(name='Huge', value=120),
]
CAVE_SIZE_OPTIONS = [
    discord.SelectOption(label="Mini", value="12"),
    discord.SelectOption(label="Tiny", value="20"),
    discord.SelectOption(label="Small", value="30"),
    discord.SelectOption(label="Medium", value="40"),
    discord.SelectOption(label="Large", value="50"),
]
CAVE_MAP_STYLE_OPTIONS = [
    discord.SelectOption(label="Small Rooms", value="s_rooms"),
    discord.SelectOption(label="Large Rooms", value="l_rooms"),
    discord.SelectOption(label="Large Area", value="l_area"),
]
CAVE_THEME_OPTIONS = [
    discord.SelectOption(label="Original", value="original")
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
    discord.SelectOption(label="Secret Rooms", value="secret_rooms")
]
DUNGEON_SIZE_OPTIONS = [discord.SelectOption(label=c.name, value=str(c.value)) for c in DUNGEON_SIZE_CHOICES]
DUNGEON_MAP_OPTIONS = [
    discord.SelectOption(label="Multi-level", value="multi_level"),
    discord.SelectOption(label="Trap", value="trap"),
]

DUNGEN_THEME_OPTIONS = [
    discord.SelectOption(label='Original', value='original'),
    discord.SelectOption(label='Ice Temple', value='ice_temple'),
    discord.SelectOption(label='Stylized Gray', value='stylized_gray'),
    discord.SelectOption(label='Black / White / Paper', value='black_white'),
    discord.SelectOption(label='Virtual World', value='virtual_world'),
]

THEME_CHOICES = [app_commands.Choice(name=opt.label, value=opt.value) for opt in DUNGEN_THEME_OPTIONS]