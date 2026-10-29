extends Node
## The battle HUD came from Mahou, which was built for a 1280x720 screen.
## While a battle is running, Godot lays the UI out at 1280x720 (it still
## fills the whole window), then switches back to our 1920x1080 for menus.
## Once we redo the HUD at 1920x1080, delete this node from battle.tscn.

const BATTLE_UI_SIZE := Vector2i(1280, 720)

var _previous_size := Vector2i.ZERO


func _enter_tree() -> void:
	var window := get_window()
	_previous_size = window.content_scale_size
	window.content_scale_size = BATTLE_UI_SIZE


func _exit_tree() -> void:
	get_window().content_scale_size = _previous_size
