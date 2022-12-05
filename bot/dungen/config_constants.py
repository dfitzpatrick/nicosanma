import os
USE_EPHEMERAL = os.environ.get('USE_EPHEMERAL', 'True').lower() == 'true'
TILE_SIZE_REGULAR = os.environ.get('TILE_SIZE_REGULAR', 70)
TILE_SIZE_HQ = os.environ.get('TILE_SIZE_HQ', 140)
VIEW_TIMEOUT = os.environ.get('VIEW_TIMEOUT', '1d')
PRODUCTION_DATABASE_NAME = os.environ.get('DB_NAME', 'nicodb')
PATREON_POLLING_MINUTES = os.environ.get('PATREON_POLLING_MINUTES', 25)
PATREON_OVERRIDE_UPSCALE = os.environ.get('PATREON_OVERRIDE_UPSCALE', '84855914615537664,')
SERVICE_NAME = os.environ.get('SERVICE_NAME', 'Dungeon Channel')
SERVICE_ICON = os.environ.get('SERVICE_ICON', 'https://dungeonchannel.com/mainimages/patreon/Patreon_Coral.jpg"')
PATREON_URL = os.environ.get('PATREON_URL', 'https://www.patreon.com/DungeonChannel')