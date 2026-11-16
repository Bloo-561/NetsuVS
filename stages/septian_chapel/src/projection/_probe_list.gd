extends SceneTree
func _initialize() -> void:
	var l = load("res://data/stage_list.tres")
	for e in l.elements: print("LIST ", e.Name, " | ", e.ScenePath, " | ", e.Thumbnail != null)
	quit()
