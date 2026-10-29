using Godot;
using SakugaEngine.Collision;
using SakugaEngine.Game;
using SakugaEngine.Global;

namespace SakugaEngine.Utils;

public partial class HitboxViewer : Node3D
{
	[Export(PropertyHint.None, "")]
	private Sprite3D[] hitboxGraphics;

	[Export(PropertyHint.None, "")]
	private PhysicsBody body;

	public override void _Process(double delta)
	{
		if (body != null)
		{
			base.Visible = GameManager.Instance != null && GameManager.Instance.ShowHitboxes;
			base.GlobalPosition = GlobalFunctions.ToScaledVector3(body.FixedPosition);
			base.GlobalRotation = Vector3.Zero;
			UpdateHitboxes();
			UpdatePushbox();
		}
	}

	public void UpdateHitboxes()
	{
		for (int j = 0; j < hitboxGraphics.Length; j++)
		{
			// (Oct 24: j < body.Hitboxes.Length too: a hitbox file with more boxes than the body's HitboxesLimit
			// threw every frame while the boxes were shown; the body ignores the extra boxes, so they aren't drawn)
			if (body.CurrentHitbox == null || body.CurrentHitbox.HitboxData == null || body.CurrentHitbox.HitboxData.Hitboxes == null || j >= body.CurrentHitbox.HitboxData.Hitboxes.Length || body.Hitboxes == null || j >= body.Hitboxes.Length)
			{
				hitboxGraphics[j].Hide();
				continue;
			}
			hitboxGraphics[j].Visible = body.Hitboxes[j].Active;
			switch (body.CurrentHitbox.HitboxData.Hitboxes[j].HitboxType)
			{
			case HitboxType.HURTBOX:
				hitboxGraphics[j].SortingOffset = 1f;
				hitboxGraphics[j].Modulate = new Color(0f, 1f, 0f);
				break;
			case HitboxType.HITBOX:
				hitboxGraphics[j].SortingOffset = 2f;
				hitboxGraphics[j].Modulate = new Color(1f, 0f, 0f);
				break;
			case HitboxType.PROJECTILE:
				hitboxGraphics[j].SortingOffset = 2f;
				hitboxGraphics[j].Modulate = new Color(1f, 0.64f, 0f);
				break;
			case HitboxType.PROXIMITY_BLOCK:
				hitboxGraphics[j].SortingOffset = 4f;
				hitboxGraphics[j].Modulate = new Color(1f, 0f, 1f);
				break;
			case HitboxType.THROW:
				hitboxGraphics[j].SortingOffset = 2f;
				hitboxGraphics[j].Modulate = new Color(0f, 0f, 1f);
				break;
			case HitboxType.COUNTER:
				hitboxGraphics[j].SortingOffset = 2f;
				hitboxGraphics[j].Modulate = new Color(0.5f, 0.5f, 0.5f);
				break;
			case HitboxType.DEFLECT:
				hitboxGraphics[j].SortingOffset = 2f;
				hitboxGraphics[j].Modulate = new Color(1f, 0f, 0.5f);
				break;
			}
			hitboxGraphics[j].GlobalPosition = GlobalFunctions.ToScaledVector3(body.Hitboxes[j].Center);
			hitboxGraphics[j].Scale = GlobalFunctions.ToScaledVector3(body.Hitboxes[j].Size, 1f);
		}
	}

	public void UpdatePushbox()
	{
		int collisionViewer = hitboxGraphics.Length - 1;
		hitboxGraphics[collisionViewer].Visible = body.Pushbox.Active;
		hitboxGraphics[collisionViewer].SortingOffset = 3f;
		hitboxGraphics[collisionViewer].Modulate = new Color(1f, 1f, 0f);
		hitboxGraphics[collisionViewer].GlobalPosition = GlobalFunctions.ToScaledVector3(body.Pushbox.Center);
		hitboxGraphics[collisionViewer].Scale = GlobalFunctions.ToScaledVector3(body.Pushbox.Size, 1f);
	}
}
