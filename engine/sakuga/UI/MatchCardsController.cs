using Godot;
using SakugaEngine.Game;
using SakugaEngine.Global;
using SakugaEngine.Resources;

namespace SakugaEngine.UI;

public partial class MatchCardsController : Control
{
	[Export(PropertyHint.None, "")]
	private AnimationPlayer animator;

	[Export(PropertyHint.None, "")]
	private Label RoundLabel;

	[Export(PropertyHint.None, "")]
	private Label KO_Label;

	[Export(PropertyHint.None, "")]
	private string RoundName = "Round";

	[Export(PropertyHint.None, "")]
	private RoundNamingOrder RoundNaming;

	[Export(PropertyHint.None, "")]
	private string[] KO_Names = new string[4] { "K.O.", "PERFECT!", "Double K.O.", "Time Up!" };

	[ExportGroup("Animation References", "")]
	[Export(PropertyHint.None, "")]
	private MatchAnimation[] Animations;

	[Export(PropertyHint.None, "")]
	private int CatchPhraseAnimation;

	[Export(PropertyHint.None, "")]
	private int RoundStartAnimation = 1;

	[Export(PropertyHint.None, "")]
	private int KOAnimationDefault = 2;

	[Export(PropertyHint.None, "")]
	private int KOAnimationP1 = 2;

	[Export(PropertyHint.None, "")]
	private int KOAnimationP2 = 3;

	[Export(PropertyHint.None, "")]
	private int WinAnimationP1 = 4;

	[Export(PropertyHint.None, "")]
	private int WinAnimationP2 = 5;

	[Export(PropertyHint.None, "")]
	private int DrawAnimation = 6;

	public int CurrentAnimation = -1;

	public int Frame;

	public void Render()
	{
		if (CurrentAnimation < 0)
		{
			animator.Play("RESET");
			return;
		}
		if (CurrentAnimation == RoundStartAnimation && Frame == 100)
		{
			AudioManager.Instance.PlayAnnouncerClip(GetCurrentAnimation().AnnouncerLineIndex + 6);
		}
		animator.Play(GetCurrentAnimation().Name);
		animator.Seek((float)Frame / 60f, update: true);
	}

	public void Run()
	{
		if (CurrentAnimation >= 0)
		{
			if (Frame < GetCurrentAnimation().Duration)
			{
				Frame++;
				return;
			}
			Frame = 0;
			CurrentAnimation = -1;
		}
	}

	public void PlayCatchPhraseAnimation()
	{
		CurrentAnimation = CatchPhraseAnimation;
		Frame = 0;
		AudioManager.Instance.PlayAnnouncerClip(GetCurrentAnimation().AnnouncerLineIndex);
	}

	public void PlayRoundStartAnimation(int currentRound, bool final)
	{
		CurrentAnimation = RoundStartAnimation;
		Frame = 0;
		if (final)
		{
			SetRoundLabel("Final " + RoundName);
			AudioManager.Instance.PlayAnnouncerClip(GetCurrentAnimation().AnnouncerLineIndex + 5);
			return;
		}
		switch (RoundNaming)
		{
		case RoundNamingOrder.N:
			SetRoundLabel($"{RoundName} {currentRound + 1}");
			break;
		case RoundNamingOrder.Nth:
		{
			string placing = "";
			placing = currentRound switch
			{
				0 => "st", 
				1 => "nd", 
				2 => "rd", 
				_ => "th", 
			};
			SetRoundLabel($"{currentRound + 1}{placing} {RoundName}");
			break;
		}
		}
		AudioManager.Instance.PlayAnnouncerClip(GetCurrentAnimation().AnnouncerLineIndex + currentRound);
	}

	public void PlayKnockoutAnimation(int playerIndex, int koType)
	{
		SetKOLabel(KO_Names[koType]);
		switch (playerIndex)
		{
		case 0:
			CurrentAnimation = KOAnimationP1;
			break;
		case 1:
			CurrentAnimation = KOAnimationP2;
			break;
		default:
			CurrentAnimation = KOAnimationDefault;
			break;
		}
		Frame = 0;
		AudioManager.Instance.PlayAnnouncerClip(GetCurrentAnimation().AnnouncerLineIndex + koType);
	}

	private void SetRoundLabel(string text)
	{
		RoundLabel.SetDeferred(Label.PropertyName.Text, text);
	}

	private void SetKOLabel(string text)
	{
		KO_Label.SetDeferred(Label.PropertyName.Text, text);
	}

	public void PlayPlayerWinAnimation(int playerIndex)
	{
		switch (playerIndex)
		{
		case 0:
			CurrentAnimation = WinAnimationP1;
			AudioManager.Instance.PlayAnnouncerClip(GetCurrentAnimation().AnnouncerLineIndex + GameManager.Instance.Match.P1SelectedCharacter);
			break;
		case 1:
			CurrentAnimation = WinAnimationP2;
			AudioManager.Instance.PlayAnnouncerClip(GetCurrentAnimation().AnnouncerLineIndex + GameManager.Instance.Match.P2SelectedCharacter);
			break;
		default:
			CurrentAnimation = DrawAnimation;
			AudioManager.Instance.PlayAnnouncerClip(GetCurrentAnimation().AnnouncerLineIndex);
			break;
		}
		Frame = 0;
	}

	public MatchAnimation GetCurrentAnimation()
	{
		return Animations[CurrentAnimation];
	}

	public bool AnimationEnded()
	{
		return Frame >= GetCurrentAnimation().Duration;
	}

	public uint GetStateDelay()
	{
		return (uint)(GetCurrentAnimation().Duration - GetCurrentAnimation().DelaySubtract);
	}
}
