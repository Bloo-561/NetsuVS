using Godot;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class AddGravityAction : FrameDataAction
{
	[Export(PropertyHint.None, "")]
	private bool SetValue;

	[Export(PropertyHint.None, "")]
	private bool UseDefault;

	[Export(PropertyHint.None, "")]
	private int Force;

	public override void Execute(ref SakugaActor Actor)
	{
		if (Actor.Body != null)
		{
			if (SetValue)
			{
				int def = 260000;
				// Nov 3 (TamaDeez): someone being hit uses the juggle gravity (GameManager.NetsuJuggleGravity) instead
				if (UseDefault && SakugaEngine.Game.GameManager.Instance != null && Actor.StateManager != null
					&& Actor.StateManager.CurrentStateType() == SakugaEngine.Global.StateType.HIT_REACTION)
				{
					def = SakugaEngine.Game.GameManager.Instance.NetsuJuggleGravity;
				}
				Actor.Body.CurrentGravity = (UseDefault ? def : Force);
			}
			Actor.Body.AddGravity();
		}
	}
}
