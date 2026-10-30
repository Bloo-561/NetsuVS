extends Node
## North Ambria - lights the fighters for the storm (visual only, never touches game state or fighter code).
## The fighters are unshaded Sprite3Ds whose colour is multiplied by their modulate (the palette shaders multiply
## it in too). This node finds every AnimationViewer in the battle (its exported "Sprites" list) and multiplies
## the stage's light into those sprites' modulate once. AnimationViewer.SetTint keeps a sprite's own modulate as
## its base, so the super flash and the other tints still work on top. Assists and projectiles that appear later
## are picked up by the rescan. Afterimages, auras and the white flash keep their own colours.
## Reusable: drop it in any stage scene and set the tint.

@export var tint: Color = Color(0.82, 0.87, 0.97)    # cold blue-grey storm light (multiply; 1 = untouched)
@export var rescan_seconds: float = 0.5

var _done := {}
var _wait := 0.0

func _process(delta: float) -> void:
	_wait -= delta
	if _wait > 0.0:
		return
	_wait = rescan_seconds
	_scan(get_tree().root)

func _scan(n: Node) -> void:
	for c in n.get_children():
		var id := c.get_instance_id()
		if not _done.has(id):
			var sprites = c.get("Sprites")
			if sprites is Array and sprites.size() > 0 and sprites[0] is Sprite3D:
				_done[id] = true
				for sp in sprites:
					if sp is Sprite3D:
						sp.modulate = sp.modulate * tint
		if c.get_child_count() > 0:
			_scan(c)
