class_name DevFixtures
extends Resource
## DEV FIXTURES (Nov 11) - the test match used when a scene is run on its own (F6 / "Run Current Scene").
## Edit data/dev_fixtures.tres in the Inspector. DevBoot (game/autoloads/dev_boot.gd) reads it.
## Only used in the editor and debug builds, and only when the scene you launched is NOT the main scene
## (title screen), so playing the game normally (F5) is never affected.
##
## The fighter / assist / stage lists below follow data/roster.tres, data/assist_list.tres and
## data/stage_list.tres. If you add or reorder entries there, update the names here too.

## Off = run scenes on their own with no test match filled in (as before Nov 11).
@export var enabled: bool = true

@export_group("Match")
## Game mode for the test match (the battle, VS screen and character select use it).
@export_enum("Training", "Versus", "Arcade") var mode: String = "Training"
## Versus / Arcade: player 2 is a person on player 2's controls (off = CPU). Training: always the dummy.
@export var p2_is_human: bool = false

@export_group("Player 1")
@export_enum("Cecilia", "Flan", "Leticia", "Noah") var p1_fighter: int = 0
## Colour index (0 = the first palette).
@export_range(0, 9) var p1_color: int = 0
@export_enum("Mary", "Adin", "Eren", "Harie") var p1_assist: int = 0

@export_group("Player 2")
@export_enum("Cecilia", "Flan", "Leticia", "Noah") var p2_fighter: int = 3
## Colour index; -1 = automatic (the alternate colour in a mirror match).
@export_range(-1, 9) var p2_color: int = -1
@export_enum("Mary", "Adin", "Eren", "Harie") var p2_assist: int = 2

@export_group("Stage and music")
@export_enum("Thors Training Hall - Morning", "Thors Training Hall - Dusk", "Crimson Abyss",
	"Depths of the Old Schoolhouse", "Celdic - Day", "Celdic - Burning", "The GeoFront", "North Ambria",
	"Ordis Royal Manor - Day", "Ordis Royal Manor - Ruined", "Old Schoolhouse -Entrance-", "Roer",
	"Septian Chapel", "Septian Chapel - Trails") var stage: int = 0
## -2 = the P1 fighter's theme (auto), -1 = random, 0+ = a song index in data/soundtrack.tres.
@export_range(-2, 40) var music: int = -2

@export_group("Fake online room")
## Online lobby run on its own (F6): a fake room with bots instead of the real connection
## (game/systems/dev/fake_online.gd). CREATE LOBBY, and the bots join.
@export var fake_online: bool = true
## How many bots join your fake lobby (1-7).
@export_range(1, 7) var fake_players: int = 2
## Seconds a bot takes to pick and press ready.
@export_range(0.1, 60.0, 0.1) var fake_pick_seconds: float = 2.0
## Seconds before a match between two bots is decided (random winner).
@export_range(1.0, 120.0, 0.5) var fake_fight_seconds: float = 10.0
