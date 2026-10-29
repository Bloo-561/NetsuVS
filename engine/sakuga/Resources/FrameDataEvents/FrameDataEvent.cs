using Godot;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class FrameDataEvent : Resource
{
	[Export(PropertyHint.None, "")]
	public FrameDataCondition[] Conditions;

	[Export(PropertyHint.None, "")]
	public FrameDataAction[] Actions;

	public void RunEvent(ref SakugaActor Actor)
	{
		if (CheckConditions(ref Actor))
		{
			ExecuteActions(ref Actor);
		}
	}

	private bool CheckConditions(ref SakugaActor Actor)
	{
		if (Conditions == null || Conditions.Length == 0)
		{
			return true;
		}
		FrameDataCondition[] conditions = Conditions;
		for (int i = 0; i < conditions.Length; i++)
		{
			if (!conditions[i].Check(ref Actor))
			{
				return false;
			}
		}
		return true;
	}

	private void ExecuteActions(ref SakugaActor Actor)
	{
		FrameDataAction[] actions = Actions;
		for (int i = 0; actions != null && i < actions.Length; i++)   // Netsu: an event may have no actions
		{
			actions[i].Execute(ref Actor);
		}
	}
}
