using Godot;

namespace SakugaEngine.UI;

public partial class ComboCounter : Control
{
	[Export(PropertyHint.None, "")]
	private Color InvalidHitColor = new Color(0f, 0f, 0f);

	private Color DefaultColor;

	public TextureProgressBar StunBar;

	public Label ComboCount;

	[Export(PropertyHint.None, "")]
	private TextureRect Star;

	[Export(PropertyHint.None, "")]
	private bool inverseRotation;

	public override void _Ready()
	{
		StunBar = GetNode<TextureProgressBar>("StunBar");
		ComboCount = GetNode<Label>("ComboCount");
		DefaultColor = StunBar.TintProgress;
	}

	private int _netsuShown = int.MinValue;

	public void UpdateCounter(int stunValue, CombatTracker tracker)
	{
		StunBar.TintProgress = (tracker.invalidHit ? InvalidHitColor : DefaultColor);
		StunBar.Value = stunValue;
		if (tracker.HitCombo != _netsuShown)   // Oct 25: a new string only when the count changes
		{
			_netsuShown = tracker.HitCombo;
			ComboCount.Text = _netsuShown.ToString();
		}
		if (Star != null)
		{
			if (tracker.invalidHit)
			{
				Star.Rotation -= (inverseRotation ? (-0.01f) : 0.01f);
			}
			else if (stunValue > 0)
			{
				Star.Rotation += (inverseRotation ? (-0.03f) : 0.03f) * ((float)tracker.HitCombo * 0.5f);
			}
		}
	}
}
