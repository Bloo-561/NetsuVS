using Godot;

namespace SakugaEngine.Resources;

[GlobalClass]
[Tool]
public partial class SpriteModifier : Resource
{
	[Export(PropertyHint.None, "")]
	public Texture2D Sprite;

	[Export(PropertyHint.None, "")]
	public Vector2 Offset = new Vector2(-56f, -4f);

	[Export(PropertyHint.Range, "0, 360")]
	public int Rotation;

	[Export(PropertyHint.None, "")]
	public bool FlipX;

	[Export(PropertyHint.None, "")]
	public bool FlipY;

	// Netsu: when true this layer is only drawn once the current move has connected
	// (hit or blocked). Used for slash trails so they don't show on a whiff.
	[Export(PropertyHint.None, "")]
	public bool OnlyOnContact;

	// Netsu (Oct 24): stretches this layer (1 = as drawn). The engine scales about the character origin,
	// so the offset is scaled too: the sprite kit writes Offset / Scale.X to keep the layer's start in place.
	// Used to run Leticia's beams across the whole screen from a short piece of the drawn beam.
	[Export(PropertyHint.None, "")]
	public Vector2 Scale = Vector2.One;
}
