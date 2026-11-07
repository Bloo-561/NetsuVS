extends Node
## Celdic - lights the fighters to match the stage (visual only, never touches game state or fighter code).
## The fighters are unshaded Sprite3Ds whose colour is multiplied by their modulate. This node finds every
## AnimationViewer in the battle (its exported "Sprites" list) and multiplies the stage's light colour into those
## sprites once, so they take on the warm afternoon sun (Day) or the dusk sky and firelight (Burning). It also
## tints the fighter's own ground shadow (the viewer's "Shadow" sprite) to the stage's shadow colour and depth,
## so the fighters sit on the cobbles instead of floating over them.
## AnimationViewer.SetTint keeps a sprite's own modulate as its base, so super flashes and other tints still work
## on top. Assists and projectiles that appear later are picked up by the rescan.

@export var tint: Color = Color(1.0, 0.97, 0.92)            # light on the fighters (multiply; 1 = untouched)
@export var shadow_color: Color = Color(0.16, 0.15, 0.22, 0.62)   # their contact shadow (rgb tone, alpha = depth)
@export var shadow_scale: float = 1.12                       # a little wider: soft light spreads the shadow
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
				var sh = c.get("Shadow")
				if sh is Sprite3D:
					sh.modulate = shadow_color
					sh.scale = sh.scale * Vector3(shadow_scale, 1.0, shadow_scale)
		if c.get_child_count() > 0:
			_scan(c)
