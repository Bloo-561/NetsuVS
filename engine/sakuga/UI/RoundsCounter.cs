using Godot;

namespace SakugaEngine.UI;

public partial class RoundsCounter : Control
{
	[Export(PropertyHint.None, "")]
	private int RoundsLimit = 2;

	[Export(PropertyHint.None, "")]
	public Control[] RoundViews;

	public void Setup()
	{
		for (int i = 0; i < RoundsLimit; i++)
		{
			RoundViews[i].Visible = false;
		}
	}

	public void ShowRounds(int roundsCount)
	{
		for (int i = 0; i < RoundsLimit; i++)
		{
			if (roundsCount - 1 == i)
			{
				RoundViews[i].Visible = true;
			}
		}
	}
}
