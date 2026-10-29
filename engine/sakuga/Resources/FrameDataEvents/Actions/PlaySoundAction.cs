using Godot;
using SakugaEngine.Global;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class PlaySoundAction : FrameDataAction
{
	[Export(PropertyHint.None, "")]
	public SoundType SoundType;

	[Export(PropertyHint.None, "")]
	public int Source;

	[Export(PropertyHint.None, "")]
	public int Index;

	[Export(PropertyHint.None, "")]
	public bool IsRandom;

	[Export(PropertyHint.None, "")]
	public int Range;

	[Export(PropertyHint.None, "")]
	public int FromExtraVariable = -1;

	public override void Execute(ref SakugaActor Actor)
	{
		if (Actor.Parameters.SoundSources != null && Actor.Parameters.SoundSources.Length != 0 && Actor.SFXList != null && Actor.VoiceLines != null)
		{
			int ind = (IsRandom ? RNG.Next(Index, Range) : Index);
			if (FromExtraVariable >= 0)
			{
				ind = Actor.Parameters.Variables[FromExtraVariable].CurrentValue;
				Actor.Parameters.Variables[FromExtraVariable].ChangeBehavior(CustomVariableBehaviorTarget.ON_USE);
			}
			AudioStream selectedSound = null;
			switch (SoundType)
			{
			case SoundType.SFX:
				selectedSound = Actor.SFXList.Sounds[ind];
				break;
			case SoundType.VOICE:
				selectedSound = Actor.VoiceLines.Sounds[ind];
				break;
			}
			Actor.Parameters.SoundSources[Source].QueueSound(selectedSound);
		}
	}
}
