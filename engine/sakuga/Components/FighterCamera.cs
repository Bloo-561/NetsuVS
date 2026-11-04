using Godot;
using SakugaEngine.Game;
using SakugaEngine.Global;

namespace SakugaEngine;

public partial class FighterCamera : Camera3D
{
	[Export(PropertyHint.None, "")]
	private AudioListener3D Listener;

	[Export(PropertyHint.None, "")]
	public CameraFocus CurrentFocus;

	[Export(PropertyHint.None, "")]
	public Vector3 nearOffset = new Vector3(2.7f, 1.4f, 6.5f);

	[Export(PropertyHint.None, "")]
	public Vector3 farOffset = new Vector3(7.25f, 3.35f, 16f);

	[Export(PropertyHint.None, "")]
	public float nearDistance = 4f;

	[Export(PropertyHint.None, "")]
	public float farDistance = 16f;

	[Export(PropertyHint.None, "")]
	public float nearFlatOffset = 0.25f;

	[Export(PropertyHint.None, "")]
	public float farFlatOffset = 0.62f;

	private Camera3D charCam;

	/// <summary>Netsu (Oct 28): room (metres, each side) kept past the two fighters when the bigger view closes in.</summary>
	[Export(PropertyHint.None, "")]
	public float NetsuViewMargin = 0.5f;

	// Netsu: the EX / super pause (GameManager.NetsuPause, Oct 24 late; reworked Oct 25 after Under Night
	// In-Birth): the camera moves in a little, about the fighter who did it: she stays where she is on the screen
	// (the point at NetsuZoomHeight above her feet doesn't move) and everything grows around her, the opponent
	// included (still in view). Then it goes back as the fight goes on. Presentation only (from the match state).

	/// <summary>How much bigger everything looks at the closest point of an EX move's pause (1 = no zoom;
	/// Under Night In-Birth's is about 1.15-1.2).</summary>
	[Export(PropertyHint.None, "")]
	public float NetsuZoomFactor = 1.18f;

	/// <summary>The same for a super (3 bars): a little closer.</summary>
	[Export(PropertyHint.None, "")]
	public float NetsuZoomFactorSuper = 1.3f;

	/// <summary>Height above her feet (metres) of the point that stays put on the screen (about her waist).</summary>
	[Export(PropertyHint.None, "")]
	public float NetsuZoomHeight = 0.7f;

	/// <summary>How fast the camera closes in / goes back (share of the way per frame).</summary>
	[Export(PropertyHint.None, "")]
	public float NetsuZoomIn = 0.14f;

	[Export(PropertyHint.None, "")]
	public float NetsuZoomOut = 0.065f;

	private float _netsuZoom;
	private Vector3 _netsuFocus;
	private float _netsuFactor = 1.18f;   // the zoom of the pause going on (or the last one, while it eases back)

	// Netsu (Oct 25): the sky. When both fighters are high in the air (Flan's Big Bang Crash carries her opponent into
	// the sky on her fist), the camera pulls back to show the stage dropping away below them, frames the two of them
	// and follows them faster (they move fast). And on every stage it stops at that stage's own top (the stage list's
	// StageElement.NetsuCameraTop: under a ceiling, or before the scenery ends), so there the fighters fly off the
	// top of the screen instead. Presentation only (worked out from the match state).

	/// <summary>Height of the LOWER fighter's feet (metres) where the camera starts pulling back (normal jumps and
	/// launches stay under it: only both fighters high up at once moves it).</summary>
	[Export(PropertyHint.None, "")]
	public float NetsuSkyFrom = 4.5f;

	/// <summary>...and where it has pulled back all the way.</summary>
	[Export(PropertyHint.None, "")]
	public float NetsuSkyFull = 9f;

	/// <summary>How much further back it goes then (metres; it's 6.5 m away from close fighters).</summary>
	[Export(PropertyHint.None, "")]
	public float NetsuSkyPullback = 4f;

	/// <summary>Height above the middle of the two fighters' feet (metres) that it centres on up there.</summary>
	[Export(PropertyHint.None, "")]
	public float NetsuSkyAim = 0.8f;

	/// <summary>How fast it follows them up and down up there (share of the way per frame; on the ground 1/6).</summary>
	[Export(PropertyHint.None, "")]
	public float NetsuSkyFollow = 0.34f;

	/// <summary>How fast it changes into / out of that (share per frame).</summary>
	[Export(PropertyHint.None, "")]
	public float NetsuSkyEase = 0.05f;

	/// <summary>When the lower fighter is above this (metres) and the higher one above NetsuSkyFrom, the camera keeps
	/// both in the picture (it doesn't lag behind them)...</summary>
	[Export(PropertyHint.None, "")]
	public float NetsuSkyKeepFrom = 2.5f;

	/// <summary>...the higher fighter's head: this far above her feet (metres)...</summary>
	[Export(PropertyHint.None, "")]
	public float NetsuSkyHead = 1.9f;

	/// <summary>...and the lower fighter's feet, with this much room under them (metres; the HUD covers the bottom).</summary>
	[Export(PropertyHint.None, "")]
	public float NetsuSkyFeet = 0.6f;

	/// <summary>How fast the camera goes back to frame both fighters in a state that shows the stage (metres per frame)...</summary>
	[Export(PropertyHint.None, "")]
	public float NetsuCineOut = 0.3f;

	/// <summary>...and comes in again (metres per frame).</summary>
	[Export(PropertyHint.None, "")]
	public float NetsuCineIn = 0.08f;

	private float _netsuSky;
	private float _netsuCineZ;
	private float _netsuTop = 25f;

	/// <summary>Netsu: the highest the camera may go on this stage (metres, its eye height; 0 or less = only the
	/// engine's 25 m). GameManager.CreateStage passes the stage list's StageElement.NetsuCameraTop.</summary>
	public void NetsuSetStageTop(float top)
	{
		_netsuTop = top > 0f ? top : 25f;
	}

	private static bool NetsuShowsStage(SakugaActor a)
	{
		SakugaEngine.Resources.FighterState st = a?.StateManager?.GetCurrentState();
		return st != null && (st.NetsuShowStage || st.NetsuFrameBoth);   // Nov 3: NetsuFrameBoth frames them without clearing the backdrop
	}

	private const float DELTA = 1f / 6f;

	private float _wallLimit = GlobalFunctions.ToScaledFloat(GlobalVariables.WallLimit);   // c26: follows the stage width (was 120000)

	private float _ceilingLimit = GlobalFunctions.ToScaledFloat(250000);

	private float _groundLimit;

	// Netsu: screen shake (visual only). Call FighterCamera.Shake(amplitude, frames).
	private static float _shakeAmp;
	private static int _shakeFrames;
	private static int _shakeTotal;
	private Vector3 _lastShake = Vector3.Zero;

	public static void Shake(float amplitude, int frames)
	{
		if (frames <= 0 || amplitude <= 0f) return;
		if (amplitude >= _shakeAmp * ((float)_shakeFrames / Mathf.Max(1, _shakeTotal)))
		{
			_shakeAmp = amplitude;
			_shakeFrames = frames;
			_shakeTotal = frames;
		}
	}

	public override void _Ready()
	{
		charCam = GetNode<Camera3D>("../CanvasLayer/ViewportContainer/Viewport_Foreground/CharacterCamera");
	}

	private bool _netsuSnap;

	/// <summary>Netsu: on the next update, go straight to the fighters instead of easing over
	/// (Training mode's position reset).</summary>
	public void NetsuSnap()
	{
		_netsuSnap = true;
	}

	public void UpdateCamera(SakugaActor player1, SakugaActor player2)
	{
		if (player1 == null || player2 == null)
		{
			return;
		}
		Vector3 _p1Position = GlobalFunctions.ToScaledVector3(player1.Body.FixedPosition);
		Vector3 _p2Position = GlobalFunctions.ToScaledVector3(player2.Body.FixedPosition);
		float pl = (Mathf.Clamp(Mathf.Abs(_p2Position.X - _p1Position.X), nearDistance, farDistance) - nearDistance) / (farDistance - nearDistance);
		// Netsu (Oct 28): the bigger view (GlobalVariables.NetsuViewZoom): the camera sits closer, and its height and the
		// side margin shrink with it so the fighters stay framed the same way. It never goes closer than it takes to
		// keep both fighters in the picture (so far apart it is the old view).
		float netsuZm = GlobalVariables.NetsuZoomNow;
		float netsuR = 1f;
		float netsuDirectZ = 0f;   // > 0: the distance worked out straight from how far apart they are (the leash view)
		float netsuHalfW = 0f;     // half the width of the picture at that distance
		if (netsuZm > 1f)
		{
			float origZ = CurrentFocus == CameraFocus.CENTER ? Mathf.Lerp(nearOffset.Z, farOffset.Z, pl) : nearOffset.Z;
			float zNew = origZ / netsuZm;
			if (CurrentFocus == CameraFocus.CENTER)
			{
				Vector2 vp = GetViewport().GetVisibleRect().Size;
				float aspect = vp.Y > 0f ? vp.X / vp.Y : 16f / 9f;
				float tanHalf = Mathf.Tan(Mathf.DegToRad(base.Fov * 0.5f));
				float zFit = (Mathf.Abs(_p2Position.X - _p1Position.X) * 0.5f + NetsuViewMargin) / (tanHalf * aspect);
				if (GlobalVariables.NetsuMaxSeparation > 0)
				{
					// Oct 28: with the max-distance leash both fighters always fit, so frame them tight: as close
					// as the near view, and only backing off as they spread (at the leash they are at the screen edges)
					zNew = Mathf.Max(nearOffset.Z / netsuZm, zFit);
					netsuDirectZ = zNew;
					netsuHalfW = zNew * tanHalf * aspect;
				}
				else
				{
					zNew = Mathf.Max(zNew, Mathf.Min(origZ, zFit));
				}
			}
			netsuR = zNew / origZ;
		}
		float FinalYOffset = nearOffset.Y * netsuR;
		float FinalZOffset = (0f - nearOffset.Z) * netsuR;
		float BoundsAdd = nearOffset.X * netsuR;
		float FlatOffset = nearFlatOffset;
		float finalCamY = FinalYOffset;
		float actualCenter = (_p1Position.X + _p2Position.X) / 2f;
		switch (CurrentFocus)
		{
		case CameraFocus.CENTER:
			FinalYOffset = Mathf.Lerp(nearOffset.Y, farOffset.Y, pl) * netsuR;
			FinalZOffset = Mathf.Lerp(0f - nearOffset.Z, 0f - farOffset.Z, pl) * netsuR;
			BoundsAdd = Mathf.Lerp(nearOffset.X, farOffset.X, pl) * netsuR;
			if (netsuDirectZ > 0f)
			{
				FinalZOffset = 0f - netsuDirectZ;
				FinalYOffset = netsuDirectZ * nearOffset.Y / nearOffset.Z;   // same camera height for the distance
				BoundsAdd = netsuHalfW * 0.93f;
				finalCamY = FinalYOffset;
			}
			FlatOffset = Mathf.Lerp(nearFlatOffset, farFlatOffset, pl);
			if (Mathf.Max(_p1Position.Y, _p2Position.Y) >= FinalYOffset)
			{
				finalCamY = Mathf.Max(_p1Position.Y, _p2Position.Y);
			}
			break;
		case CameraFocus.PLAYER1:
			actualCenter = _p1Position.X;
			if (_p1Position.Y >= FinalYOffset)
			{
				finalCamY = _p1Position.Y;
			}
			break;
		case CameraFocus.PLAYER2:
			actualCenter = _p2Position.X;
			if (_p2Position.Y >= FinalYOffset)
			{
				finalCamY = _p2Position.Y;
			}
			break;
		}
		// Netsu: both fighters high in the air: pull back, frame the two of them (see NetsuSkyFrom)
		float netsuLowY = Mathf.Min(_p1Position.Y, _p2Position.Y);
		float netsuSkyGoal = CurrentFocus == CameraFocus.CENTER ? Mathf.Clamp((netsuLowY - NetsuSkyFrom) / Mathf.Max(0.01f, NetsuSkyFull - NetsuSkyFrom), 0f, 1f) : 0f;
		_netsuSky = _netsuSnap ? netsuSkyGoal : Mathf.MoveToward(_netsuSky, netsuSkyGoal, NetsuSkyEase);
		float sky = _netsuSky * _netsuSky * (3f - 2f * _netsuSky);
		if (sky > 0f)
		{
			float netsuHighY = Mathf.Max(_p1Position.Y, _p2Position.Y);
			finalCamY = Mathf.Lerp(finalCamY, (netsuLowY + netsuHighY) * 0.5f + NetsuSkyAim, sky);
			FinalZOffset -= NetsuSkyPullback * sky;
		}
		// Netsu: a state that shows the stage (FighterState.NetsuShowStage: Flan's Big Bang Crash, Leticia's Crimson
		// Waltz) frames both fighters whole: the camera goes back as far as it takes (quickly out, slowly in again)
		bool netsuCine = CurrentFocus == CameraFocus.CENTER && (NetsuShowsStage(player1) || NetsuShowsStage(player2));
		float netsuCineGoal = 0f;
		if (netsuCine)
		{
			float spanTop = Mathf.Max(_p1Position.Y, _p2Position.Y) + NetsuSkyHead;
			float spanBottom = netsuLowY - NetsuSkyFeet;
			netsuCineGoal = (spanTop - spanBottom) * 0.5f / Mathf.Tan(Mathf.DegToRad(base.Fov * 0.5f));
		}
		_netsuCineZ = _netsuSnap ? netsuCineGoal : Mathf.MoveToward(_netsuCineZ, netsuCineGoal, netsuCineGoal > _netsuCineZ ? NetsuCineOut : NetsuCineIn);
		if (_netsuCineZ > 0f - FinalZOffset)
		{
			FinalZOffset = 0f - _netsuCineZ;
		}
		// Netsu: the EX / super pause: close in on the fighter who did it (and back out once the fight goes on)
		GameManager gm = GameManager.Instance;
		bool pausing = gm != null && gm.NetsuPause > 0 && gm.NetsuPauseSide >= 0 && gm.NetsuPauseSide <= 1;
		if (pausing)
		{
			SakugaActor who = gm.NetsuPauseSide == 0 ? player1 : player2;
			_netsuFocus = GlobalFunctions.ToScaledVector3(who.Body.FixedPosition);
			_netsuFactor = gm.NetsuPauseIsSuper ? NetsuZoomFactorSuper : NetsuZoomFactor;
		}
		_netsuZoom = Mathf.MoveToward(_netsuZoom, pausing ? 1f : 0f, pausing ? NetsuZoomIn : NetsuZoomOut);
		float zk = _netsuZoom * _netsuZoom * (3f - 2f * _netsuZoom);
		if (zk > 0f)
		{
			// a dolly in by s about her: the camera comes s times closer and slides towards her by the same share,
			// so the point at her waist keeps its place on the screen
			float s = Mathf.Lerp(1f, Mathf.Max(1f, _netsuFactor), zk);
			float baseZ = Mathf.Max(0.5f, 0f - FinalZOffset);
			float pivotX = _netsuFocus.X;
			float pivotY = _netsuFocus.Y + NetsuZoomHeight;
			actualCenter = pivotX + (actualCenter - pivotX) / s;
			finalCamY = pivotY + (finalCamY - pivotY) / s;
			BoundsAdd /= s;          // the view is narrower: it may go nearer the walls
			FlatOffset /= s;
			FinalYOffset = Mathf.Min(FinalYOffset, finalCamY - _groundLimit);   // and lower, towards the floor
			FinalZOffset = 0f - baseZ / s;
		}
		base.Position -= _lastShake;
		Vector3 newCamPosition = new Vector3(actualCenter, finalCamY, 0f);
		float netsuBottom = _groundLimit + FinalYOffset;
		float netsuTop = Mathf.Max(netsuBottom, Mathf.Min(_ceilingLimit - FinalYOffset, _netsuTop));   // Netsu: the stage's top
		Vector3 clampedCamPosition = new Vector3(Mathf.Clamp(newCamPosition.X, 0f - _wallLimit + BoundsAdd, _wallLimit - BoundsAdd), Mathf.Clamp(newCamPosition.Y, netsuBottom, netsuTop), 0f);
		float netsuFollow = _netsuSnap || netsuDirectZ > 0f ? 1f : Mathf.Lerp(1f / 6f, 1f, zk);   // Netsu: a Training reset jumps straight there; the pause's close-up follows her exactly
		float netsuFollowY = Mathf.Max(netsuFollow, Mathf.Lerp(1f / 6f, NetsuSkyFollow, sky));   // Netsu: faster up in the sky
		_netsuSnap = false;
		float netsuY = Mathf.Lerp(base.Position.Y, newCamPosition.Y, netsuFollowY);
		float netsuHighY2 = Mathf.Max(_p1Position.Y, _p2Position.Y);
		bool netsuBothUp = netsuCine || (netsuHighY2 > NetsuSkyFrom && netsuLowY > NetsuSkyKeepFrom);
		if (CurrentFocus == CameraFocus.CENTER && (netsuBothUp || sky > 0f))
		{
			// Netsu: up in the sky (both of them in the air, one above NetsuSkyFrom) the camera doesn't lag them out of
			// the picture: the higher one's head and the lower one's feet stay in view (if they can't both fit, it keeps
			// the middle). On the way back down (still pulled back) only the feet: it comes down with them.
			float half = Mathf.Tan(Mathf.DegToRad(base.Fov * 0.5f)) * Mathf.Max(0.5f, 0f - FinalZOffset);
			float lo = netsuBothUp ? netsuHighY2 + NetsuSkyHead - half : float.NegativeInfinity;
			float hi = netsuLowY - NetsuSkyFeet + half;
			netsuY = lo <= hi ? Mathf.Clamp(netsuY, lo, hi) : (lo + hi) * 0.5f;
		}
		base.Position = new Vector3(Mathf.Clamp(Mathf.Lerp(base.Position.X, newCamPosition.X, netsuFollow), 0f - _wallLimit + BoundsAdd, _wallLimit - BoundsAdd), Mathf.Clamp(netsuY, netsuBottom, netsuTop), 0f - FinalZOffset);
		_lastShake = Vector3.Zero;
		if (_shakeFrames > 0)
		{
			float k = _shakeAmp * ((float)_shakeFrames / _shakeTotal);
			float sx = ((_shakeFrames / 2) % 2 == 0) ? k : -k;
			float sy = ((_shakeFrames % 3) == 0) ? k * 0.6f : -k * 0.3f;
			_lastShake = new Vector3(sx, sy, 0f);
			_shakeFrames--;
		}
		base.Position += _lastShake;
		charCam.GlobalTransform = base.GlobalTransform;
		float dist = base.GlobalPosition.DistanceTo(clampedCamPosition);
		if (base.Projection == ProjectionType.Perspective)
		{
			if (charCam.Projection == ProjectionType.Perspective)
			{
				charCam.Fov = base.Fov;
			}
			else
			{
				charCam.Size = dist * Mathf.Tan(Mathf.DegToRad(base.Fov * 2f) / 2f) - FlatOffset;
			}
		}
		else
		{
			charCam.Projection = base.Projection;
			base.Size = base.Position.Z;
			charCam.Size = base.Size;
		}
		if (Listener != null)
		{
			Listener.GlobalPosition = new Vector3(base.Position.X, base.Position.Y, 0f);
		}
	}
}
