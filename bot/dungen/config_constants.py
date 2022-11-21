import os
from datetime import timedelta
TILE_SIZE_REGULAR = os.environ.get('TILE_SIZE_REGULAR', 70)
TILE_SIZE_HQ = os.environ.get('TILE_SIZE_HQ', 140)
VIEW_TIMEOUT = os.environ.get('VIEW_TIMEOUT', '1d')
PRODUCTION_DATABASE_NAME = os.environ.get('DB_NAME', 'nicodb')
PATREON_POLLING_MINUTES = os.environ.get('PATREON_POLLING_MINUTES', 25)
