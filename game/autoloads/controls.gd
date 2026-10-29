extends Node
## CONTROLS (autoload - always running, reach it from anywhere as "Controls")
##
## Sets up every player's buttons when the game starts, Dengeki Bunko
## Fighting Climax style:
##   A / B / C  = attacks (light, medium, heavy)
##   S          = support (call your assist)
##   AB, BC, ABC = macro buttons that press several buttons at once
##   Start      = pause / confirm
##
## Each player gets actions named "p1_a", "p1_start", "p2_up" and so on.
## Use them anywhere:  Input.is_action_pressed("p1_a")
##
## The KEYBOARD / PAD / MENU_KEYS tables below are the DEFAULT layouts.
## Players change them on the Options screen; their changes live in the
## `keyboard`, `pad` and `menu_keys` variables and are saved by GameSettings
## (user://settings.cfg). "Restore Default" goes back to these tables.
## (These actions are created by code, so they will NOT show up in
## Project Settings > Input Map. That's on purpose.)


# ---------------------------------------------------------------------------
# Button "bits" for the fight engine.
# During a match, rollback netcode sends ONE number per player per frame.
# Each button is one bit of that number. get_frame_input() builds it.
# ---------------------------------------------------------------------------
const BIT_UP := 1 << 0
const BIT_DOWN := 1 << 1
const BIT_LEFT := 1 << 2
const BIT_RIGHT := 1 << 3
const BIT_A := 1 << 4
const BIT_B := 1 << 5
const BIT_C := 1 << 6
const BIT_S := 1 << 7
const BIT_START := 1 << 8

## Training mode shortcuts: [action, keyboard key, controller button].
##   training_reset   Q / Back          (hold a direction for a corner, down to swap sides)
##   training_record  R / left stick    (record the dummy; press again to stop)
##   training_play    T / right stick   (play the recording; press again to stop)
const TRAINING_SHORTCUTS := [
	["training_reset", KEY_Q, JOY_BUTTON_BACK],
	["training_record", KEY_R, JOY_BUTTON_LEFT_STICK],
	["training_play", KEY_T, JOY_BUTTON_RIGHT_STICK],
]

## Every action each player gets (becomes "p1_<name>" and "p2_<name>").
const BUTTONS := ["up", "down", "left", "right", "a", "b", "c", "s", "ab", "bc", "abc", "start"]

## Which real buttons each macro presses. Add a new macro here + in the tables.
const MACROS := {
	"ab": BIT_A | BIT_B,
	"bc": BIT_B | BIT_C,
	"abc": BIT_A | BIT_B | BIT_C,
}

## Buttons listed on the Options screen, in order.
const REBIND_KEYBOARD := ["up", "down", "left", "right", "a", "b", "c", "s", "ab", "bc", "abc", "start"]
const REBIND_PAD := ["a", "b", "c", "s", "ab", "bc", "abc", "start"]   # directions stay on D-pad + stick
const REBIND_MENU := ["ui_up", "ui_down", "ui_left", "ui_right", "ui_accept", "ui_cancel"]

## How far a stick/trigger must be pushed to count as pressed (0 to 1).
const DEADZONE := 0.5

## Default keyboard layout per player. Uses PHYSICAL key positions, so it works
## the same on non-English keyboards.
const KEYBOARD := {
	1: {
		"up": KEY_W, "down": KEY_S, "left": KEY_A, "right": KEY_D,
		"a": KEY_J, "b": KEY_K, "c": KEY_L, "s": KEY_I,
		"ab": KEY_U, "bc": KEY_O, "abc": KEY_P,
		"start": KEY_ENTER,
	},
	2: {
		"up": KEY_UP, "down": KEY_DOWN, "left": KEY_LEFT, "right": KEY_RIGHT,
		"a": KEY_KP_4, "b": KEY_KP_5, "c": KEY_KP_6, "s": KEY_KP_8,
		"ab": KEY_KP_7, "bc": KEY_KP_9, "abc": KEY_KP_ADD,
		"start": KEY_KP_ENTER,
	},
}

## Default controller layout (Xbox names; on PlayStation X=Square, Y=Triangle,
## B=Circle, A=Cross). Player 1 uses controller #1, player 2 controller #2.
## {"button": ...} is a button, {"axis": ..., "dir": ...} is a stick/trigger.
const PAD := {
	"up": [{"button": JOY_BUTTON_DPAD_UP}, {"axis": JOY_AXIS_LEFT_Y, "dir": -1.0}],
	"down": [{"button": JOY_BUTTON_DPAD_DOWN}, {"axis": JOY_AXIS_LEFT_Y, "dir": 1.0}],
	"left": [{"button": JOY_BUTTON_DPAD_LEFT}, {"axis": JOY_AXIS_LEFT_X, "dir": -1.0}],
	"right": [{"button": JOY_BUTTON_DPAD_RIGHT}, {"axis": JOY_AXIS_LEFT_X, "dir": 1.0}],
	"a": [{"button": JOY_BUTTON_X}],
	"b": [{"button": JOY_BUTTON_Y}],
	"c": [{"button": JOY_BUTTON_B}],
	"s": [{"button": JOY_BUTTON_A}],
	"ab": [{"button": JOY_BUTTON_RIGHT_SHOULDER}],
	"bc": [{"axis": JOY_AXIS_TRIGGER_RIGHT, "dir": 1.0}],
	"abc": [{"button": JOY_BUTTON_LEFT_SHOULDER}],
	"start": [{"button": JOY_BUTTON_START}],
}

## Default extra keyboard keys for menus. The FIRST key of each list is the one
## shown (and changed) on the Options screen. Godot's built-in "ui_" keys
## (arrows, Enter, Escape) always work too, so menus can never get locked out.
const MENU_KEYS := {
	"ui_up": [KEY_W],
	"ui_down": [KEY_S],
	"ui_left": [KEY_A],
	"ui_right": [KEY_D],
	"ui_accept": [KEY_J, KEY_KP_4, KEY_I, KEY_KP_8],          # A or S confirms (like the select screens)
	"ui_cancel": [KEY_K, KEY_L, KEY_KP_5, KEY_KP_6, KEY_BACKSPACE],  # B or C goes back
}

## Controller buttons for menus, on EVERY controller (player 1 and 2).
## Same rule as the select screens: A / S / Start confirm, B / C go back.
## (Xbox names - X = our A, A = our S, Y = our B, B = our C.)
## These feed Godot's "ui_" actions, which the main menu, the pause menu and
## "press a button" on the results screen (engine GameManager.cs) all use.
const MENU_PAD := {
	"ui_accept": [{"button": JOY_BUTTON_X}, {"button": JOY_BUTTON_A}, {"button": JOY_BUTTON_START}],
	"ui_cancel": [{"button": JOY_BUTTON_Y}, {"button": JOY_BUTTON_B}, {"button": JOY_BUTTON_BACK}],
	"ui_up": [{"button": JOY_BUTTON_DPAD_UP}, {"axis": JOY_AXIS_LEFT_Y, "dir": -1.0}],
	"ui_down": [{"button": JOY_BUTTON_DPAD_DOWN}, {"axis": JOY_AXIS_LEFT_Y, "dir": 1.0}],
	"ui_left": [{"button": JOY_BUTTON_DPAD_LEFT}, {"axis": JOY_AXIS_LEFT_X, "dir": -1.0}],
	"ui_right": [{"button": JOY_BUTTON_DPAD_RIGHT}, {"axis": JOY_AXIS_LEFT_X, "dir": 1.0}],
}

## Names shown on the Options screen for controller inputs.
const PAD_BUTTON_NAMES := {
	JOY_BUTTON_A: "A", JOY_BUTTON_B: "B", JOY_BUTTON_X: "X", JOY_BUTTON_Y: "Y",
	JOY_BUTTON_BACK: "BACK", JOY_BUTTON_GUIDE: "HOME", JOY_BUTTON_START: "START",
	JOY_BUTTON_LEFT_STICK: "LSB", JOY_BUTTON_RIGHT_STICK: "RSB",
	JOY_BUTTON_LEFT_SHOULDER: "LB", JOY_BUTTON_RIGHT_SHOULDER: "RB",
	JOY_BUTTON_DPAD_UP: "D-UP", JOY_BUTTON_DPAD_DOWN: "D-DOWN",
	JOY_BUTTON_DPAD_LEFT: "D-LEFT", JOY_BUTTON_DPAD_RIGHT: "D-RIGHT",
	JOY_BUTTON_MISC1: "SHARE", JOY_BUTTON_TOUCHPAD: "PAD",
}
const PAD_AXIS_NAMES := {JOY_AXIS_TRIGGER_LEFT: "LT", JOY_AXIS_TRIGGER_RIGHT: "RT"}

## Emitted after any layout changes (the Options screen redraws on it).
signal bindings_changed

## Which player pressed a button on the title screen (1 or 2, 0 = unknown).
## Menus can use this to know who is "in control".
var menu_owner := 0

## The CURRENT layouts (start as copies of the tables above).
var keyboard := {}    # player -> {button: Key}
var pad := {}         # player -> {button: [input, ...]}
var menu_keys := {}   # "ui_accept" -> [Key, ...]

var _menu_events: Array = []   # [action, event] pairs we added to the ui_ actions

## Versus side select: which device plays on each side.
## {1: "pad1"/"pad2"/"kb1"/"kb2"/"", 2: ...}   "" = nobody (CPU).
## Empty = the normal setup: side 1 = keyboard 1 + controller 1,
## side 2 = keyboard 2 + controller 2. (scenes/versus/device_select.gd sets it,
## the main menu clears it.)
var side_devices := {}

## Every device the side select knows about, in the order it lists them.
const DEVICES := ["pad1", "pad2", "kb1", "kb2"]


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	for player in [1, 2]:
		reset_keyboard(player, false)
		reset_pad(player, false)
	reset_menu_keys(false)
	for action in MENU_PAD:
		InputMap.action_set_deadzone(action, DEADZONE)
		for pad_input in MENU_PAD[action]:
			var pad_event := _make_pad_event(pad_input, -1)  # -1 = any controller
			if not InputMap.action_has_event(action, pad_event):
				InputMap.action_add_event(action, pad_event)
	rebuild()

	# "pause" is what the fight engine listens for during a match:
	# Enter / Numpad Enter / Escape, or Start on any controller.
	if InputMap.has_action("pause"):
		InputMap.erase_action("pause")
	InputMap.add_action("pause", DEADZONE)
	for key in [KEY_ENTER, KEY_KP_ENTER, KEY_ESCAPE]:
		InputMap.action_add_event("pause", _make_key_event(key))
	var start_button := InputEventJoypadButton.new()
	start_button.button_index = JOY_BUTTON_START
	start_button.device = -1  # any controller
	InputMap.action_add_event("pause", start_button)

	# Training mode shortcuts (game/ui/training/netsu_training_hud.gd), on any keyboard / controller.
	for shortcut in TRAINING_SHORTCUTS:
		var action: String = shortcut[0]
		if InputMap.has_action(action):
			InputMap.erase_action(action)
		InputMap.add_action(action, DEADZONE)
		InputMap.action_add_event(action, _make_key_event(shortcut[1]))
		var button := InputEventJoypadButton.new()
		button.button_index = shortcut[2]
		button.device = -1
		InputMap.action_add_event(action, button)


## Re-creates every player action from the current layouts.
func rebuild() -> void:
	for player in [1, 2]:
		# which keyboard layout / controller drives this side
		var kb_layout: int = player
		var pad_layout: int = player
		if not side_devices.is_empty():
			var device: String = side_devices.get(player, "")
			kb_layout = int(device.substr(2)) if device.begins_with("kb") else 0
			pad_layout = int(device.substr(3)) if device.begins_with("pad") else 0
		for button in BUTTONS:
			var action := "p%d_%s" % [player, button]
			if InputMap.has_action(action):
				InputMap.erase_action(action)
			InputMap.add_action(action, DEADZONE)
			if kb_layout > 0:
				var key = keyboard[kb_layout].get(button)
				if key != null and key != KEY_NONE:
					InputMap.action_add_event(action, _make_key_event(key))
			if pad_layout > 0:
				for pad_input in pad[pad_layout].get(button, []):
					InputMap.action_add_event(action, _make_pad_event(pad_input, pad_layout - 1))
	for pair in _menu_events:
		if InputMap.has_action(pair[0]):
			InputMap.action_erase_event(pair[0], pair[1])
	_menu_events.clear()
	for action in menu_keys:
		for key in menu_keys[action]:
			var event := _make_key_event(key)
			if not InputMap.action_has_event(action, event):
				InputMap.action_add_event(action, event)
				_menu_events.append([action, event])
	bindings_changed.emit()


# --- Sides (Versus) ------------------------------------------------------------------

## Puts a device on each side ("" = CPU). Example: assign_sides("pad2", "kb1").
func assign_sides(p1_device: String, p2_device: String) -> void:
	side_devices = {1: p1_device, 2: p2_device}
	rebuild()


## Back to the normal setup (keyboard 1 + controller 1 = player 1, etc.).
func clear_sides() -> void:
	if side_devices.is_empty():
		return
	side_devices = {}
	rebuild()


## Which device sent this event: "pad1", "pad2", "kb1", "kb2" or "".
## Keyboard keys belong to whichever player's keyboard layout has them; menu-only
## keys (Escape, Enter, arrows...) count as keyboard 1 unless keyboard 2 uses them.
func device_from_event(event: InputEvent) -> String:
	if event is InputEventJoypadButton or event is InputEventJoypadMotion:
		return "pad%d" % (event.device + 1) if event.device in [0, 1] else ""
	if event is InputEventKey:
		var key: int = event.physical_keycode
		for n in [1, 2]:
			if keyboard[n].values().has(key):
				return "kb%d" % n
		return "kb1"
	return ""


## For a keyboard / controller: is this event its left / right / confirm / back?
## Uses that device's own button layout, plus the menu keys.
## `what` is "left", "right", "confirm" or "back".
func device_pressed(event: InputEvent, device: String, what: String) -> bool:
	var ui := {"left": "ui_left", "right": "ui_right", "confirm": "ui_accept", "back": "ui_cancel"}
	if event.is_action_pressed(ui[what], true):
		return true
	var buttons := {"left": ["left"], "right": ["right"], "confirm": ["a", "s", "start"], "back": ["b", "c"]}
	if device.begins_with("kb") and event is InputEventKey and event.pressed and (not event.echo or what in ["left", "right"]):
		var layout: Dictionary = keyboard[int(device.substr(2))]
		for b in buttons[what]:
			if layout.get(b) == event.physical_keycode:
				return true
	return false


## True if that controller is plugged in (keyboards always count as connected).
func device_connected(device: String) -> bool:
	if device.begins_with("pad"):
		return Input.get_connected_joypads().has(int(device.substr(3)) - 1)
	return device != ""


func device_label(device: String) -> String:
	if device.begins_with("pad"):
		return "CONTROLLER " + device.substr(3)
	if device.begins_with("kb"):
		return "KEYBOARD " + device.substr(2)
	return "CPU"


# --- Changing layouts (used by the Options screen) --------------------------------

## Puts `key` on a player's button. Whatever already used that key (either
## player) gets this button's old key instead, so nothing is ever doubled up.
func set_key(player: int, button: String, key: int) -> void:
	var old = keyboard[player].get(button, KEY_NONE)
	for p in [1, 2]:
		for b in keyboard[p]:
			if keyboard[p][b] == key and not (p == player and b == button):
				keyboard[p][b] = old
	keyboard[player][button] = key
	rebuild()


## Puts one controller input on a player's button (swaps like set_key).
func set_pad(player: int, button: String, pad_input: Dictionary) -> void:
	var old: Array = pad[player].get(button, []).duplicate(true)
	for b in pad[player]:
		if b == button:
			continue
		var list: Array = pad[player][b]
		if _has_input(list, pad_input):
			if b in REBIND_PAD:
				pad[player][b] = old
			else:  # a direction: just drop the stolen input
				pad[player][b] = list.filter(func(i): return not _same_input(i, pad_input))
	pad[player][button] = [pad_input]
	rebuild()


## Changes the shown (first) keyboard key of a menu action (swaps like set_key).
func set_menu_key(action: String, key: int) -> void:
	var list: Array = menu_keys[action]
	var old = list[0] if not list.is_empty() else KEY_NONE
	for a in menu_keys:
		if a != action:
			var other: Array = menu_keys[a]
			var at := other.find(key)
			if at >= 0:
				if old == KEY_NONE:
					other.remove_at(at)
				else:
					other[at] = old
	if list.has(key):
		list.erase(key)
	if list.is_empty():
		list.append(key)
	else:
		list[0] = key
	rebuild()


func reset_keyboard(player: int, apply: bool = true) -> void:
	keyboard[player] = KEYBOARD[player].duplicate()
	if apply:
		rebuild()


func reset_pad(player: int, apply: bool = true) -> void:
	pad[player] = PAD.duplicate(true)
	if apply:
		rebuild()


func reset_menu_keys(apply: bool = true) -> void:
	menu_keys = MENU_KEYS.duplicate(true)
	if apply:
		rebuild()


## For GameSettings: the layouts as plain data it can save.
func export_bindings() -> Dictionary:
	return {"keyboard": keyboard.duplicate(true), "pad": pad.duplicate(true), "menu": menu_keys.duplicate(true)}


## For GameSettings: loads saved layouts. Anything missing keeps its default,
## so buttons added in later versions still get a key.
func import_bindings(data: Dictionary) -> void:
	for player in [1, 2]:
		var k = data.get("keyboard", {}).get(player)
		if k is Dictionary:
			for button in k:
				if button in BUTTONS:
					keyboard[player][button] = int(k[button])
		var p = data.get("pad", {}).get(player)
		if p is Dictionary:
			for button in p:
				if button in BUTTONS and p[button] is Array:
					pad[player][button] = p[button]
	var m = data.get("menu")
	if m is Dictionary:
		for action in m:
			if action in MENU_KEYS and m[action] is Array:
				menu_keys[action] = m[action]
	rebuild()


# --- Names for the Options screen ----------------------------------------------------

func key_name(key) -> String:
	if key == null or key == KEY_NONE:
		return "---"
	var physical := int(key) as Key
	var s := ""
	# Numpad keys: name them by position (some systems report them as Home/Left/...
	# when Num Lock is off). Everything else: name it as printed on the player's keyboard.
	if physical < KEY_KP_MULTIPLY or physical > KEY_KP_9:
		s = OS.get_keycode_string(DisplayServer.keyboard_get_keycode_from_physical(physical))
	if s == "":
		s = OS.get_keycode_string(physical)
	if s.begins_with("Kp "):
		s = "Num " + s.substr(3)
	return s


func pad_name(pad_input) -> String:
	if not pad_input is Dictionary:
		return "---"
	if pad_input.has("button"):
		return PAD_BUTTON_NAMES.get(int(pad_input["button"]), "B%d" % int(pad_input["button"]))
	var axis := int(pad_input.get("axis", -1))
	if PAD_AXIS_NAMES.has(axis):
		return PAD_AXIS_NAMES[axis]
	return "AXIS %d%s" % [axis, "+" if pad_input.get("dir", 1.0) > 0 else "-"]


## The input shown for a player's controller button ("---" when unbound).
func pad_binding(player: int, button: String) -> Dictionary:
	var list: Array = pad[player].get(button, [])
	return list[0] if not list.is_empty() else {}


func _has_input(list: Array, pad_input: Dictionary) -> bool:
	for i in list:
		if _same_input(i, pad_input):
			return true
	return false


func _same_input(a: Dictionary, b: Dictionary) -> bool:
	if a.has("button") and b.has("button"):
		return int(a["button"]) == int(b["button"])
	if a.has("axis") and b.has("axis"):
		return int(a["axis"]) == int(b["axis"]) and signf(a.get("dir", 1.0)) == signf(b.get("dir", 1.0))
	return false


# --- Everything else (unchanged) ---------------------------------------------------------

## Alt+Enter or F11 toggles fullscreen anywhere in the game.
func _input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		if event.keycode == KEY_F11 or (event.keycode == KEY_ENTER and event.alt_pressed):
			var settings := get_node_or_null("/root/GameSettings")
			if settings:
				settings.toggle_fullscreen()
			elif DisplayServer.window_get_mode() == DisplayServer.WINDOW_MODE_FULLSCREEN:
				DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_WINDOWED)
			else:
				DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_FULLSCREEN)
			get_viewport().set_input_as_handled()


## Everything a player is holding this frame, packed into one number.
## Opposite directions cancel out (left + right = neither).
## Macros add their buttons (holding AB sets both the A and B bits).
func get_frame_input(player: int) -> int:
	var p := "p%d_" % player
	var bits := 0
	var up := Input.is_action_pressed(p + "up")
	var down := Input.is_action_pressed(p + "down")
	var left := Input.is_action_pressed(p + "left")
	var right := Input.is_action_pressed(p + "right")
	if up and not down:
		bits |= BIT_UP
	if down and not up:
		bits |= BIT_DOWN
	if left and not right:
		bits |= BIT_LEFT
	if right and not left:
		bits |= BIT_RIGHT
	if Input.is_action_pressed(p + "a"):
		bits |= BIT_A
	if Input.is_action_pressed(p + "b"):
		bits |= BIT_B
	if Input.is_action_pressed(p + "c"):
		bits |= BIT_C
	if Input.is_action_pressed(p + "s"):
		bits |= BIT_S
	if Input.is_action_pressed(p + "start"):
		bits |= BIT_START
	for macro in MACROS:
		if Input.is_action_pressed(p + macro):
			bits |= MACROS[macro]
	return bits


## True for a fresh key press, controller button press or mouse click.
## Used by "PRESS ANY BUTTON".
func is_any_press(event: InputEvent) -> bool:
	if event is InputEventKey:
		return event.pressed and not event.echo
	if event is InputEventJoypadButton or event is InputEventMouseButton:
		return event.pressed
	return false


## Which player (1 or 2) this button belongs to, or 0 if it's not one of theirs.
func player_from_event(event: InputEvent) -> int:
	for player in [1, 2]:
		for button in BUTTONS:
			if event.is_action_pressed("p%d_%s" % [player, button]):
				return player
	return 0


func _make_key_event(key: int) -> InputEventKey:
	var event := InputEventKey.new()
	event.physical_keycode = key as Key
	event.device = -1  # any keyboard
	return event


func _make_pad_event(pad_input: Dictionary, device: int) -> InputEvent:
	if pad_input.has("button"):
		var event := InputEventJoypadButton.new()
		event.button_index = int(pad_input["button"])
		event.device = device
		return event
	var motion := InputEventJoypadMotion.new()
	motion.axis = int(pad_input["axis"])
	motion.axis_value = pad_input["dir"]
	motion.device = device
	return motion
