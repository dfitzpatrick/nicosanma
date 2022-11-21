import os
from datetime import timedelta
TILE_SIZE_REGULAR = os.environ.get('TILE_SIZE_REGULAR', 70)
TILE_SIZE_HQ = os.environ.get('TILE_SIZE_HQ', 140)
VIEW_TIMEOUT = os.environ.get('VIEW_TIMEOUT', '1m')
USER_GENERATIONS_EPHEMERAL = bool(os.environ.get('USER_GENERATIONS_EPHEMERAL', False))

