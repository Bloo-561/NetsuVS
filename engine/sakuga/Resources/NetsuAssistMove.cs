using Godot;

namespace SakugaEngine.Resources;

/// <summary>
/// Netsu: one way to call an assist (5S, 6S...). Listed in NetsuAssistElement.Moves.
/// The assist character's state does the rest (animation, movement, hitboxes): see
/// actors/assists/&lt;name&gt;/States.
/// </summary>
[GlobalClass]
public partial class NetsuAssistMove : Resource
{
	/// <summary>Shown in the command list ("5S", "6S").</summary>
	[Export(PropertyHint.None, "")]
	public string MoveName = "5S";

	/// <summary>Shown in the command list.</summary>
	[Export(PropertyHint.None, "")]
	public string DisplayName = "";

	/// <summary>0 = S alone (also 2S / 8S), 1 = forward + S (6S), 2 = back + S (4S; uses 5S when the assist has no 4S).</summary>
	[Export(PropertyHint.Enum, "Neutral (5S),Forward (6S),Back (4S)")]
	public int Direction;

	/// <summary>The state the assist plays (its index in the assist's data, 0_TAG_Data.tres).</summary>
	[Export(PropertyHint.None, "")]
	public int StateIndex = 1;

	/// <summary>Where the assist appears: X = units in front of the caller (negative = behind), Y = up. 10000 = 1 m.</summary>
	[Export(PropertyHint.None, "")]
	public Vector2I SpawnOffset = new Vector2I(-9000, 0);

	/// <summary>On: the assist always appears standing on the floor (even if called in the air).</summary>
	[Export(PropertyHint.None, "")]
	public bool OnGround = true;

	/// <summary>Frames the assist gauge takes to refill after the assist has left (60 = 1 second).</summary>
	[Export(PropertyHint.None, "")]
	public int Cooldown = 600;

	/// <summary>The CPU calls this move when the opponent is this far away (units, 10000 = 1 m).</summary>
	[Export(PropertyHint.None, "")]
	public Vector2I AIRange = new Vector2I(0, 60000);

	[Export(PropertyHint.MultilineText)]
	public string Description = "";

	/// <summary>Netsu (Oct 26 evening): on = the assist faces the way the caller is facing (Mary's 6S note always goes
	/// that way); off = toward the opponent.</summary>
	[Export(PropertyHint.None, "")]
	public bool NetsuFaceCaller;

	/// <summary>Netsu (Oct 27): on = this assist stays on screen when its partner is hit (an exception to the rule that
	/// assists leave when the caller is hit).</summary>
	[Export(PropertyHint.None, "")]
	public bool StayWhenPartnerHit;
}
