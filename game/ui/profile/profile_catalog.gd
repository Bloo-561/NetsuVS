class_name ProfileCatalog
extends RefCounted
## PROFILE CATALOG (Nov 4 2026): every profile ICON and TITLE a player can pick in Main Menu > CUSTOMIZE, and the
## look of each title's name plate. What the player picked is saved in GameSettings "profile" ("icon", "title",
## "menu_character"); online it goes to the other players with the lobby's "hi" (game/autoloads/online_room.gd).
##
## TO ADD AN ICON: one line in ICONS.
##   {"id": "flan_wink", "name": "Wink", "group": "FLAN", "path": "res://actors/flan/Artwork/Portrait-Flan.png",
##    "rect": Rect2(60, 40, 560, 560)}
##   id    unique, lower case, letters / digits / _ (it's what gets saved and sent online: never rename one)
##   name  shown under the icon;  group: the heading it's shown with (a fighter's name, GAME, ASSIST, ART...)
##   path  any picture in the project
##   rect  the square of the picture to show, in the picture's own pixels (open it in an image editor and read the
##         corner and size off). Rect2() = the biggest square from the top middle.
##   "fit": true   show the whole picture letterboxed instead of a square crop (wide logos).
##   "unlocked"    optional, see below.
##
## TO ADD A TITLE: one line in TITLES:
##   {"id": "flan_main", "text": "Big Bang Brawler", "about": "...", "style": "star"}
##   text  what the plate says;  about: one line shown when it's picked;  style: a key of STYLES (the colours and the
##         little pictures drawn on the plate: NetsuTitlePlate draws them). A new style = a new STYLES entry (and, for
##         a new picture, a "motif" case in netsu_title_plate.gd _motif()).
##
## LOCKING (for later): every entry may have "unlocked": true / false, or a rule name (a String) that is_unlocked()
## checks ("beta" below). Leave it out = unlocked. Locked titles and icons show as "?" in the pickers and can't be set.
## Right now everything is unlocked (every rule returns true).

## What a new player has.
const DEFAULT_ICON := "logo_vs"
const DEFAULT_TITLE := "challenger"

const ICONS := [
	# --- The game ---
	{"id": "logo_vs", "name": "Netsu VS", "group": "GAME", "path": "res://assets/ui/logo/icon.png", "rect": Rect2()},
	{"id": "logo_full", "name": "Netsu VS Logo", "group": "GAME", "path": "res://assets/ui/logo/netsu_vs_logo.png",
		"rect": Rect2(), "fit": true},
	# --- Cecilia ---
	{"id": "cec_smile", "name": "Smile", "group": "CECILIA", "path": "res://actors/cecilia/Artwork/Cecilia_Select_Portrait.png",
		"rect": Rect2(120, 40, 560, 560)},
	{"id": "cec_focus", "name": "Focus", "group": "CECILIA", "path": "res://actors/cecilia/Artwork/Cecilia_Select_Icon.png",
		"rect": Rect2(200, 60, 900, 900)},
	{"id": "cec_iaido", "name": "Iaido", "group": "CECILIA", "path": "res://actors/cecilia/Artwork/CutIn_EX.png",
		"rect": Rect2(950, 60, 520, 520)},
	{"id": "cec_thunder", "name": "Thunder Plunge", "group": "CECILIA", "path": "res://actors/cecilia/Artwork/CutIn_Super.png",
		"rect": Rect2(200, 40, 640, 640)},
	{"id": "cec_pixel", "name": "Pixel", "group": "CECILIA", "path": "res://actors/cecilia/Artwork/Cecilia_Portrait.png",
		"rect": Rect2(80, 0, 560, 560)},
	{"id": "cec_chibi", "name": "Chibi", "group": "CECILIA", "path": "res://actors/cecilia/Artwork/ceciliachibi.png",
		"rect": Rect2(18, 0, 100, 100)},
	# --- Flan ---
	{"id": "fln_wink", "name": "Wink", "group": "FLAN", "path": "res://actors/flan/Artwork/Portrait-Flan.png",
		"rect": Rect2(60, 40, 560, 560)},
	{"id": "fln_starfist", "name": "Star Fist", "group": "FLAN", "path": "res://actors/flan/Artwork/CutIn_EX.png",
		"rect": Rect2(760, 60, 520, 520)},
	{"id": "fln_fistup", "name": "Fist Up", "group": "FLAN", "path": "res://actors/flan/Artwork/HUD_Portrait.png",
		"rect": Rect2(60, 0, 400, 400)},
	{"id": "fln_pixel", "name": "Pixel", "group": "FLAN", "path": "res://actors/flan/Artwork/Flan_Portrait.png",
		"rect": Rect2(40, 0, 560, 560)},
	{"id": "fln_chibi", "name": "Chibi", "group": "FLAN", "path": "res://actors/flan/Artwork/flanchibi.png",
		"rect": Rect2(18, 0, 100, 100)},
	# --- Leticia ---
	{"id": "let_smirk", "name": "Smirk", "group": "LETICIA", "path": "res://actors/leticia/Artwork/Leticia_Select_Portrait.png",
		"rect": Rect2(180, 0, 520, 520)},
	{"id": "let_close", "name": "Close-Up", "group": "LETICIA", "path": "res://actors/leticia/Artwork/Leticia_Select_Icon.png",
		"rect": Rect2(300, 40, 700, 700)},
	{"id": "let_crossfire", "name": "Crossfire", "group": "LETICIA", "path": "res://actors/leticia/Artwork/CutIn_EX.png",
		"rect": Rect2(900, 20, 460, 460)},
	{"id": "let_guns", "name": "Dual Guns", "group": "LETICIA", "path": "res://actors/leticia/Artwork/Gallery/Leticia_DualGuns.png",
		"rect": Rect2(180, 0, 700, 700)},
	{"id": "let_stardrive", "name": "Stardrive", "group": "LETICIA", "path": "res://actors/leticia/Artwork/CutIn_Super.png",
		"rect": Rect2(340, 20, 440, 440)},
	# --- Noah ---
	{"id": "noa_hood", "name": "Hood", "group": "NOAH", "path": "res://actors/noah/Artwork/Noah_Select_Portrait.png",
		"rect": Rect2(120, 0, 560, 560)},
	{"id": "noa_void", "name": "Void Grasp", "group": "NOAH", "path": "res://actors/noah/Artwork/CutIn_EX.png",
		"rect": Rect2(300, 120, 440, 440)},
	{"id": "noa_arm", "name": "Devil Arm", "group": "NOAH", "path": "res://actors/noah/Artwork/Noah_Select_Icon.png",
		"rect": Rect2(60, 0, 480, 480)},
	{"id": "noa_glance", "name": "Glance", "group": "NOAH", "path": "res://actors/noah/Artwork/Noah_WinRender.png",
		"rect": Rect2(330, 240, 280, 280)},
	# --- Assists ---
	{"id": "ast_mary", "name": "Mary", "group": "ASSIST", "path": "res://actors/assists/mary/Artwork/Icon.png", "rect": Rect2()},
	{"id": "ast_adin", "name": "Adin", "group": "ASSIST", "path": "res://actors/assists/adin/Artwork/Icon.png", "rect": Rect2()},
	{"id": "ast_eren", "name": "Eren", "group": "ASSIST", "path": "res://actors/assists/eren/Artwork/Icon.png", "rect": Rect2()},
	{"id": "ast_harie", "name": "Harie", "group": "ASSIST", "path": "res://actors/assists/harie/Artwork/Icon.png", "rect": Rect2()},
	# --- Art added later goes here (group "ART", or a fighter's name) ---
]

const TITLES := [
	{"id": "cecilia_main", "text": "Eight Leaves, One Blade", "style": "sakura",
		"about": "For Cecilia mains: her sword style, in sakura and lightning."},
	{"id": "flan_main", "text": "Big Bang Brawler", "style": "star",
		"about": "For Flan mains: fists full of starlight."},
	{"id": "leticia_main", "text": "Stardrive Gunslinger", "style": "comet",
		"about": "For Leticia mains: twin guns, a board and a comet's tail."},
	{"id": "noah_main", "text": "Beyond the Event Horizon", "style": "void",
		"about": "For Noah mains: shadow waves and black holes."},
	{"id": "beta_tester", "text": "Beta Tester", "style": "tester", "unlocked": "beta",
		"about": "Played Netsu VS before it was finished."},
	{"id": "netsu", "text": "Netsu no Kiseki", "style": "ember",
		"about": "The campaign this game was born from."},
	{"id": "party", "text": "One of the Party", "style": "d20",
		"about": "Rolled the dice in the campaign."},
	{"id": "challenger", "text": "Challenger", "style": "plain",
		"about": "Everyone starts here."},
	{"id": "king", "text": "King of the Hill", "style": "crown",
		"about": "Winner stays on."},
	{"id": "backup", "text": "Trusted Backup", "style": "shield",
		"about": "Mary, Adin, Eren and Harie have your back."},
	{"id": "scholar", "text": "Frame Data Scholar", "style": "frames",
		"about": "Lives in Training mode."},
	{"id": "rollback", "text": "Rollback Wanderer", "style": "rollback",
		"about": "Fights friends from far away."},
]

## A title plate's look. accent = border / motif colour, deep = the plate's fill, ink = the lettering, motif = the
## little pictures drawn at both ends (netsu_title_plate.gd _motif()).
const STYLES := {
	"sakura": {"accent": Color(1.0, 0.42, 0.58), "deep": Color(0.32, 0.03, 0.1), "ink": Color(1.0, 0.93, 0.95), "motif": "sakura"},
	"star": {"accent": Color(1.0, 0.8, 0.3), "deep": Color(0.26, 0.15, 0.02), "ink": Color(1.0, 0.97, 0.86), "motif": "star"},
	"comet": {"accent": Color(0.38, 0.86, 1.0), "deep": Color(0.02, 0.14, 0.32), "ink": Color(0.92, 0.98, 1.0), "motif": "comet"},
	"void": {"accent": Color(0.74, 0.46, 1.0), "deep": Color(0.1, 0.03, 0.2), "ink": Color(0.96, 0.92, 1.0), "motif": "void"},
	"tester": {"accent": Color(0.42, 1.0, 0.72), "deep": Color(0.02, 0.18, 0.14), "ink": Color(0.9, 1.0, 0.96), "motif": "tester"},
	"ember": {"accent": Color(1.0, 0.56, 0.22), "deep": Color(0.3, 0.07, 0.02), "ink": Color(1.0, 0.95, 0.88), "motif": "ember"},
	"d20": {"accent": Color(0.86, 0.66, 0.98), "deep": Color(0.12, 0.06, 0.26), "ink": Color(0.98, 0.95, 1.0), "motif": "d20"},
	"plain": {"accent": Color(0.62, 0.8, 1.0), "deep": Color(0.04, 0.08, 0.24), "ink": Color(0.97, 0.97, 1.0), "motif": "plain"},
	"crown": {"accent": Color(1.0, 0.86, 0.42), "deep": Color(0.05, 0.1, 0.32), "ink": Color(1.0, 0.96, 0.84), "motif": "crown"},
	"shield": {"accent": Color(0.72, 0.84, 0.98), "deep": Color(0.08, 0.12, 0.24), "ink": Color(0.96, 0.98, 1.0), "motif": "shield"},
	"frames": {"accent": Color(0.3, 0.82, 1.0), "deep": Color(0.02, 0.1, 0.22), "ink": Color(0.92, 0.98, 1.0), "motif": "frames"},
	"rollback": {"accent": Color(1.0, 0.36, 0.48), "deep": Color(0.08, 0.06, 0.26), "ink": Color(0.97, 0.95, 1.0), "motif": "rollback"},
	"locked": {"accent": Color(0.5, 0.54, 0.66), "deep": Color(0.06, 0.07, 0.14), "ink": Color(0.7, 0.72, 0.82), "motif": "plain"},
}

## Tests / previews: ids listed here count as locked whatever their entry says.
static var force_locked: Array = []

static var _textures := {}


# --- Looking things up -------------------------------------------------------------------------------------

## The icon entry for an id (unknown / empty = the default icon: an old or newer game's id still shows something).
static func icon(id: String) -> Dictionary:
	for e in ICONS:
		if e["id"] == id:
			return e
	return ICONS[0]


static func title(id: String) -> Dictionary:
	for e in TITLES:
		if e["id"] == id:
			return e
	return {}


static func has_icon(id: String) -> bool:
	for e in ICONS:
		if e["id"] == id:
			return true
	return false


static func has_title(id: String) -> bool:
	return not title(id).is_empty()


static func style(id: String) -> Dictionary:
	return STYLES.get(id, STYLES["plain"])


## Unlocked? `unlocked` true / false, or a rule name (all rules are open for now: add the checks here later).
static func is_unlocked(entry: Dictionary) -> bool:
	if entry.is_empty() or str(entry.get("id", "")) in force_locked:
		return false
	var u = entry.get("unlocked", true)
	if u is bool:
		return u
	match str(u):
		"beta":
			return true   # later: e.g. a flag in user://, or the build's version
		_:
			return true


## The picture for an icon: the square crop (an AtlasTexture), or the whole picture for "fit" icons. Cached.
static func icon_texture(id: String) -> Texture2D:
	var e := icon(id)
	var key: String = e["id"]
	if _textures.has(key):
		return _textures[key]
	var tex: Texture2D = null
	if ResourceLoader.exists(e["path"]):
		var src = load(e["path"])
		if src is Texture2D:
			if bool(e.get("fit", false)):
				tex = src
			else:
				var r: Rect2 = e.get("rect", Rect2())
				if r.size.x <= 0.0 or r.size.y <= 0.0:
					var ts: Vector2 = src.get_size()
					var side := minf(ts.x, ts.y)
					r = Rect2((ts.x - side) / 2.0, 0, side, side)
				var crop := AtlasTexture.new()
				crop.atlas = src
				crop.region = r
				tex = crop
	_textures[key] = tex
	return tex


## Puts an icon in a TextureRect (the right stretch for square crops and for letterboxed "fit" icons).
static func apply_icon(rect: TextureRect, id: String) -> void:
	rect.texture = icon_texture(id)
	rect.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	rect.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED if bool(icon(id).get("fit", false)) \
		else TextureRect.STRETCH_KEEP_ASPECT_COVERED


## An id that came from somewhere else (the settings file, another computer): a short lower-case word, else "".
static func clean_id(value) -> String:
	if not (value is String or value is StringName):
		return ""
	var s := str(value).strip_edges().to_lower()
	if s.length() > 32:
		return ""
	for ch in s:
		if not (ch >= "a" and ch <= "z") and not (ch >= "0" and ch <= "9") and ch != "_":
			return ""
	return s


# --- This player's profile (GameSettings "profile") -------------------------------------------------------

static func _settings() -> Node:
	var tree := Engine.get_main_loop() as SceneTree
	return tree.root.get_node_or_null("GameSettings") if tree else null


static func my_icon() -> String:
	var gs := _settings()
	var id := clean_id(gs.get_value("profile", "icon")) if gs else ""
	return id if has_icon(id) else DEFAULT_ICON


static func my_title() -> String:
	var gs := _settings()
	var id := clean_id(gs.get_value("profile", "title")) if gs else ""
	return id if has_title(id) else DEFAULT_TITLE


## The name the other players see (the ONLINE > NAME setting), "" = none set.
static func my_name() -> String:
	var gs := _settings()
	return str(gs.get_value("online", "name")).strip_edges() if gs else ""


## "random" or a roster index (int).
static func my_menu_character():
	var gs := _settings()
	var v = gs.get_value("profile", "menu_character") if gs else "random"
	if v is int or v is float:
		return int(v)
	return "random"
