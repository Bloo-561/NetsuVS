extends SceneTree
func _initialize() -> void:
	var st: Node = load("res://stages/septian_chapel/septian_chapel_trails.tscn").instantiate()
	var m: ShaderMaterial = st.get_node("Floor").get_surface_override_material(0)
	print("PROBE shader=", m.shader.resource_path)
	for n in ["tex_grass", "tex_cobble", "light_tex", "grass_a"]:
		var v = m.get_shader_parameter(n)
		print("PROBE ", n, " = ", v, " ", (v.get_size() if v is Texture2D else ""))
	print("PROBE uniforms ", m.shader.get_shader_uniform_list().size())
	quit()
