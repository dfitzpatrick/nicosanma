
### Required Environment Variables
`TOKEN` - Discord Bot Token

`DSN` - Postgresql Connection String (NO DATABASE NAMED)
Example: DSN=postgresql://postgres:postgres@localhost:5434

`PATREON_TOKEN` - Patreon Creators Token for Background Tasks
### Optional Environment Variables
`PRODUCTION_DATABASE_NAME` - Postgresql Database Name for Regular Operations (Defaults to nicodb)

`PATREON_POLLING_MINUTES` - Number of Minutes Between Polling Patreon. Defaults to 25.

`PATREON_OVERRIDE_UPSCALE` - Overrides at the bot level who can use the Upscale button. 
```
This is a comma seperated list of Discord ids.
Ex: 84855914615537664, 224734305581137921

Defaults to 84855914615537664
```
`DB_HOST` - Postgresql Host for Running Tests Only

`DB_PORT` - Postgresql Port for Running Tests Only

`DB_USER` - Postgresql User for Running Tests Only

`DB_PWD` - Postgresql Password for Running Tests Only

`TILE_SIZE_REGULAR` - The Default Tile Size to Use (DEFAULT: 70)

`TILE_SIZE_HQ` - The HIGH QUALITY Tile Size to Use (DEFAULT: 140)

`SERVICE_NAME` - The name of the Service that appears on most embeds. (DEFAULT: 'Dungeon Channel')

`SERVICE_ICON` - The icon url that appears on most embeds. (DEFAULT: 'https://dungeonchannel.com/mainimages/patreon/Patreon_Coral.jpg')

`PATREON_URL` - The url link to the Patreon Account (DEFAULT: 'https://www.patreon.com/DungeonChannel')

`VIEW_TIMEOUT` - The time between inactivity on each map or cave before the session is disabled and not more edits can be made. Defaults to 1 day.

`USE_EPHEMERAL` - Whether to send the dungen generators as a private (ephemeral) message. (DEFAULT: True)

```
This uses a text representation to express time
Format is 1w2d1h18m2s  and any combination of that.
DEFAULTS to 1d (1 day)
```

### To Run the Bot
Create a virtual environment.

Install the requirements
To run: `python3 -m bot`

To Sync App Commands to your guild, use the text command `!sync *`
This needs to only be ran once.

### To Use the Bot
/dungen map -- Generates a new map

/dungen cave -- Generates a new cave layout