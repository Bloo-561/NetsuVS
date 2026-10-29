using Godot;
using SakugaEngine.Resources;

namespace SakugaEngine;

public partial class AudioManager : Node
{
	[Export(PropertyHint.None, "")]
	private AudioStreamPlayer Announcer;

	[Export(PropertyHint.None, "")]
	private AudioStreamPlayer Menu;

	[Export(PropertyHint.None, "")]
	private AudioStreamPlayer BGM;

	[Export(PropertyHint.None, "")]
	private SoundsList AnnouncerClips;

	[Export(PropertyHint.None, "")]
	private SoundsList MenuClips;

	public static AudioManager Instance { get; private set; }

	public override void _Ready()
	{
		Instance = this;
	}

	public void PlayAnnouncerClip(int soundIndex)
	{
		if (AnnouncerClips != null && soundIndex >= 0)
		{
			Announcer.Stream = AnnouncerClips.Sounds[soundIndex];
			Announcer.Play();
		}
	}

	public void PlayMenuClip(int soundIndex)
	{
		if (MenuClips != null && soundIndex >= 0)
		{
			Menu.Stream = MenuClips.Sounds[soundIndex];
			Menu.Play();
		}
	}

	public void PlayBGM(AudioStream song)
	{
		if (song != null)
		{
			if (BGM.Playing)
			{
				StopBGM();
			}
			BGM.Stream = song;
			BGM.Play();
		}
	}

	public void StopBGM()
	{
		BGM.Stop();
	}

	public bool PlayingBGM()
	{
		return BGM.Playing;
	}
}
