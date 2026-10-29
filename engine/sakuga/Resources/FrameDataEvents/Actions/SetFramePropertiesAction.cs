using Godot;
using SakugaEngine.Global;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class SetFramePropertiesAction : FrameDataAction
{
	[Export(PropertyHint.None, "")]
	private FrameProperties Properties;

	[Export(PropertyHint.None, "")]
	private ParameterChange ChangeMode;

	public override void Execute(ref SakugaActor Actor)
	{
		switch (ChangeMode)
		{
		case ParameterChange.SET:
			Actor.FrameProperties = Properties;
			break;
		case ParameterChange.ADD:
			Actor.FrameProperties |= Properties;
			break;
		case ParameterChange.SUBTRACT:
			Actor.FrameProperties &= (FrameProperties)(byte)(~(int)Properties);
			break;
		}
	}
}
