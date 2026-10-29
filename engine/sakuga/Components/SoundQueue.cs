using Godot;
using SakugaEngine.Game;

namespace SakugaEngine;

[GlobalClass]
public partial class SoundQueue : AudioStreamPlayer3D
{
	[Export(PropertyHint.None, "")]
	private ushort QueueDelay = 12;

	[Export(PropertyHint.None, "")]
	private AudioStream DefaultSound;

	private bool Queued;

	public ushort QueueTimer;

	private AudioStream BufferedSound;

	// Netsu (Oct 24 2026, night): the last sounds this player started, with the game frame that started them.
	// Online, a rollback runs the last few frames again, and every sound started in them used to start again too
	// (heard twice, or cut off and restarted). A sound already started for that same frame is not started again.
	// Offline the frames only go forward, so this never skips anything.
	private const int NetsuRecent = 8;

	private readonly AudioStream[] _netsuSounds = new AudioStream[NetsuRecent];

	private readonly int[] _netsuFrames = new int[NetsuRecent];

	private int _netsuNext;

	public override void _Ready()
	{
		// Netsu: fighter, assist and hit-effect sounds go through the SFX bus, so Options > Sound > SFX sets their
		// volume (they were on Master: only the master volume changed them)
		if (Bus == "Master" && AudioServer.GetBusIndex("SFX") >= 0)
		{
			Bus = "SFX";
		}
		for (int i = 0; i < NetsuRecent; i++)
		{
			_netsuFrames[i] = int.MinValue;
		}
	}

	public override void _PhysicsProcess(double delta)
	{
		TickQueueTimer();
		PlayQueue();
	}

	public void SimpleQueueSound()
	{
		if (!Queued && !NetsuAlreadyStarted(DefaultSound))
		{
			BufferedSound = DefaultSound;
			Queued = true;
		}
	}

	public void QueueSound(AudioStream sound)
	{
		if (NetsuAlreadyStarted(sound))
		{
			return;
		}
		if (!Queued || base.Stream != sound)
		{
			BufferedSound = sound;
			QueueTimer = 0;
			Queued = true;
		}
	}

	/// <summary>Netsu: true when this sound was already started for the current game frame (a rollback is
	/// running that frame again); otherwise remembers it and returns false.</summary>
	private bool NetsuAlreadyStarted(AudioStream sound)
	{
		if (sound == null || GameManager.Instance == null)
		{
			return false;
		}
		int frame = GameManager.Instance.Frame;
		for (int i = 0; i < NetsuRecent; i++)
		{
			if (_netsuFrames[i] == frame && _netsuSounds[i] == sound)
			{
				return true;
			}
		}
		_netsuSounds[_netsuNext] = sound;
		_netsuFrames[_netsuNext] = frame;
		_netsuNext = (_netsuNext + 1) % NetsuRecent;
		return false;
	}

	public void PlayQueue()
	{
		if (Queued && BufferedSound != null && QueueTimer <= 0)
		{
			base.Stream = BufferedSound;
			Play();
			QueueTimer = QueueDelay;
			Queued = false;
			BufferedSound = null;
		}
	}

	private void TickQueueTimer()
	{
		if (QueueTimer != 0)
		{
			QueueTimer--;
		}
	}
}
