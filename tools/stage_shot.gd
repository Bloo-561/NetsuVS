# Renders a stage scene from the fight-camera positions and saves PNGs, then quits.
#   Godot --path <project> --rendering-method gl_compatibility --resolution 1920x1080 -s res://tools/stage_shot.gd -- scene=res://... out=<abs dir> tag=x
extends SceneTree
const CAMS = {"near": Vector3(0, 1.4, 6.5), "mid": Vector3(0, 1.9, 9.5), "far": Vector3(0, 3.35, 16),
	"near_right": Vector3(9.3, 1.4, 6.5), "far_left": Vector3(-4.75, 3.35, 16), "jump_far": Vector3(0, 6.5, 16)}
func _initialize() -> void:
	var a := {}
	for s in OS.get_cmdline_user_args():
		var kv: PackedStringArray = s.split("=", true, 1)
		if kv.size() == 2: a[kv[0]] = kv[1]
	var st: Node = load(a["scene"]).instantiate()
	root.add_child(st)
	var cam := Camera3D.new(); cam.fov = 30.0; cam.far = 1500.0; root.add_child(cam); cam.current = true
	for i in 30: await process_frame
	for n in CAMS:
		cam.position = CAMS[n]
		for i in 8: await process_frame
		await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png(a["out"].path_join(a.get("tag", "shot") + "_" + n + ".png"))
	quit()
