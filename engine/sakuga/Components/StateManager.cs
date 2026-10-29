using Godot;
using SakugaEngine.Global;
using SakugaEngine.Resources;

namespace SakugaEngine;

[GlobalClass]
public partial class StateManager : Node
{
	private SakugaActor _owner;

	public int CurrentState;

	public int CurrentStateFrame;

	public void Initialize(SakugaActor owner)
	{
		_owner = owner;
		PlayState((!_owner.IsActive) ? (-1) : 0);
		CurrentStateFrame = -1;
	}

	public void Reset()
	{
		PlayState((!_owner.IsActive) ? (-1) : 0);
		CurrentStateFrame = -1;
	}

	public void PlayState(int state, bool reset = false)
	{
		if (state >= 0)
		{
			FrameDataEvent[] onExitEvents = GetCurrentState().OnExitEvents;
			for (int i = 0; onExitEvents != null && i < onExitEvents.Length; i++)   // Netsu: a state may have none
			{
				onExitEvents[i].RunEvent(ref _owner);
			}
			if (CurrentState != state)
			{
				CurrentState = state;
				CurrentStateFrame = 0;
			}
			else if (reset)
			{
				CurrentStateFrame = 0;
			}
			_owner.Body.UpdateColliders();
			_owner.Body.ResetHits();
			_owner.CancelConditions = CancelCondition.WHIFF_CANCEL | CancelCondition.KARA_CANCEL;
			onExitEvents = GetCurrentState().OnEnterEvents;
			for (int i = 0; onExitEvents != null && i < onExitEvents.Length; i++)
			{
				onExitEvents[i].RunEvent(ref _owner);
			}
		}
	}

	public void RunState()
	{
		CurrentStateFrame++;
		HitboxState[] netsuWindows = GetCurrentState().AnimationData?.Hitboxes;   // Netsu (Oct 28): a window flagged NetsuRehit opens a new hit
		for (int w = 0; netsuWindows != null && w < netsuWindows.Length; w++)
		{
			if (netsuWindows[w] != null && netsuWindows[w].NetsuRehit && netsuWindows[w].AtFrame == CurrentStateFrame)
			{
				_owner.Body.ResetHits();
			}
		}
		if (CurrentStateFrame >= 3)
		{
			_owner.CancelConditions &= ~CancelCondition.KARA_CANCEL;
		}
	}

	public FighterState GetState(int index)
	{
		return _owner.Data.States[index];
	}

	public FighterState GetState(string name)
	{
		return _owner.Data.States[GetStateIndex(name)];
	}

	public FighterState GetCurrentState()
	{
		return _owner.Data.States[CurrentState];
	}

	public StateType CurrentStateType()
	{
		return GetCurrentState().Type;
	}

	public bool StateEnded()
	{
		return CurrentStateFrame >= GetCurrentState().AnimationData.Duration;
	}

	public int GetStateIndex(string name)
	{
		for (int i = 0; i < _owner.Data.States.Length; i++)
		{
			if (_owner.Data.States[i].StateName == name)
			{
				return i;
			}
		}
		GD.Print("State " + name + " not found.");
		return -1;
	}

	public AnimationSettings GetCurrentAnimationSettings()
	{
		if (GetCurrentState().AnimationData == null)
		{
			return null;
		}
		if (GetCurrentState().AnimationData.Animations == null || GetCurrentState().AnimationData.Animations.Length == 0)
		{
			return null;
		}
		if (GetCurrentState().AnimationData.Animations.Length == 1)
		{
			return GetCurrentState().AnimationData.Animations[0];
		}
		int anim = 0;
		for (int i = 0; i < GetCurrentState().AnimationData.Animations.Length; i++)
		{
			int nextFrame = ((i == GetCurrentState().AnimationData.Animations.Length - 1) ? CurrentStateFrame : (GetCurrentState().AnimationData.Animations[i + 1].AtFrame - 1));
			if (CurrentStateFrame >= GetCurrentState().AnimationData.Animations[i].AtFrame && CurrentStateFrame <= nextFrame)
			{
				anim = i;
			}
		}
		return GetCurrentState().AnimationData.Animations[anim];
	}
}
