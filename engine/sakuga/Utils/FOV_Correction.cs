using System;
using Godot;

namespace SakugaEngine.Utils;

public partial class FOV_Correction : Node3D
{
	[Export(PropertyHint.Range, "0, 1")]
	private float intensity = 0.5f;

	private Camera3D camera;

	public override void _Ready()
	{
		camera = GetViewport().GetCamera3D();
	}

	public override void _Process(double delta)
	{
		if (camera != null)
		{
			float targetX = Mathf.Lerp(base.GlobalPosition.X, camera.GlobalPosition.X, intensity);
			Vector3 LookTarget = new Vector3(targetX, base.GlobalPosition.Y, camera.GlobalPosition.Z);
			LookAt(LookTarget, Vector3.Up);
			RotateObjectLocal(Vector3.Up, (float)Math.PI);
		}
	}
}
