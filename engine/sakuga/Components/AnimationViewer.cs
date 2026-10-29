using Godot;
using SakugaEngine.Resources;

namespace SakugaEngine;

[GlobalClass]
[Tool]
public partial class AnimationViewer : Node
{
	[Export(PropertyHint.None, "")]
	private Sprite3D[] Sprites;

	[Export(PropertyHint.None, "")]
	private Node3D Shadow;

	private Vector3 baseScale;

	// Netsu: afterimages (fading ghost copies of the body sprite) for dashes and slides.
	// Turned on per animation with AnimationData.Afterimages; drawn only in game, not in the editor.
	[Export(PropertyHint.None, "")]
	public Color AfterimageTint = new Color(1f, 0.85f, 0.3f, 1f);

	[Export(PropertyHint.None, "")]
	public int AfterimageCount = 3;

	[Export(PropertyHint.None, "")]
	public int AfterimageSpacing = 3;

	private struct GhostFrame
	{
		public Texture2D Texture;
		public Vector2 Offset;
		public bool FlipH;
		public Transform3D Xform;
	}

	private Sprite3D[] _ghosts;
	private GhostFrame[] _history;
	private int _historyHead;
	private int _historyCount;
	private bool _ghostsOn;

	public override void _Ready()
	{
		base._Ready();
		baseScale = ((Shadow == null) ? Vector3.Zero : Shadow.Scale);
		NetsuCreateGhosts();
		NetsuCreateAura();
		// Netsu: extra layers (slash trails) get their own copy of the palette material,
		// because ViewAnimations writes each layer's texture into its material.
		if (Sprites != null)
		{
			for (int i = 1; i < Sprites.Length; i++)
			{
				if (Sprites[i] != null && Sprites[i].MaterialOverride != null)
				{
					Sprites[i].MaterialOverride = (Material)Sprites[i].MaterialOverride.Duplicate();
				}
			}
		}
	}

	private void NetsuCreateGhosts()
	{
		if (Engine.IsEditorHint() || Sprites == null || Sprites.Length == 0 || Sprites[0] == null || AfterimageCount <= 0)
		{
			return;
		}
		Node parent = Sprites[0].GetParent();
		_ghosts = new Sprite3D[AfterimageCount];
		_history = new GhostFrame[AfterimageCount * AfterimageSpacing + 1];
		for (int i = 0; i < AfterimageCount; i++)
		{
			Sprite3D g = new Sprite3D();
			g.TopLevel = true;
			g.Visible = false;
			g.Centered = Sprites[0].Centered;
			g.PixelSize = Sprites[0].PixelSize;
			g.TextureFilter = Sprites[0].TextureFilter;
			g.Layers = Sprites[0].Layers;
			g.Shaded = false;
			parent.CallDeferred(Node.MethodName.AddChild, g);
			_ghosts[i] = g;
		}
	}

	/// <summary>Netsu: show or hide afterimages; call after ViewAnimations each render.</summary>
	public void SetAfterimages(bool on)
	{
		if (_ghosts == null)
		{
			return;
		}
		if (!on)
		{
			if (_ghostsOn)
			{
				for (int i = 0; i < _ghosts.Length; i++) _ghosts[i].Visible = false;
				_historyCount = 0;
			}
			_ghostsOn = false;
			return;
		}
		_ghostsOn = true;
		for (int i = 0; i < _ghosts.Length; i++)
		{
			int back = (i + 1) * AfterimageSpacing;
			Sprite3D g = _ghosts[i];
			if (back >= _historyCount || !g.IsInsideTree())
			{
				g.Visible = false;
				continue;
			}
			int idx = (_historyHead - 1 - back + _history.Length * 2) % _history.Length;
			GhostFrame f = _history[idx];
			g.Texture = f.Texture;
			g.Offset = f.Offset;
			g.FlipH = f.FlipH;
			g.GlobalTransform = f.Xform;
			float a = 0.5f * (1f - (float)i / _ghosts.Length);
			g.Modulate = new Color(AfterimageTint.R, AfterimageTint.G, AfterimageTint.B, a);
			g.SortingOffset = Sprites[0].SortingOffset - 1f - i;
			g.Visible = true;
		}
	}

	private void NetsuRecordFrame()
	{
		if (_history == null || Sprites[0].Texture == null || !Sprites[0].IsInsideTree())
		{
			return;
		}
		_history[_historyHead] = new GhostFrame { Texture = Sprites[0].Texture, Offset = Sprites[0].Offset, FlipH = Sprites[0].FlipH, Xform = Sprites[0].GlobalTransform };
		_historyHead = (_historyHead + 1) % _history.Length;
		if (_historyCount < _history.Length) _historyCount++;
	}

	// --- Netsu: aura (Oct 24) -------------------------------------------------------------------
	// A coloured outline around the body sprite while the fighter's EX move or super flashes (Under
	// Night In-Birth style). Eight flat-colour copies of the body sprite (assets/shaders/netsu_aura.gdshader),
	// nudged a few sprite pixels in every direction and drawn just behind it, so only the rim shows.
	// SakugaActor.NetsuSuperFlashLook turns it on and off every render. Drawn only in game, not in the editor.
	private static readonly Vector2[] AuraDirs =
	{
		new Vector2(1f, 0f), new Vector2(-1f, 0f), new Vector2(0f, 1f), new Vector2(0f, -1f),
		new Vector2(0.7071f, 0.7071f), new Vector2(-0.7071f, 0.7071f), new Vector2(0.7071f, -0.7071f), new Vector2(-0.7071f, -0.7071f),
	};

	private Sprite3D[] _aura;
	private ShaderMaterial _auraMaterial;
	private bool _auraOn;
	private Color _auraColor = new Color(0f, 0f, 0f, 0f);

	// Oct 25: shader parameter names made once (a StringName from a string every frame was garbage for the
	// collector, whose pauses were hitches), and the aura drawn invisibly for its first frames so its shader is
	// compiled during the fight's fade-in instead of at the first EX move (the first one stalled).
	private static readonly StringName NetsuAuraParam = new StringName("aura");
	private static readonly StringName NetsuTexParam = new StringName("tex");
	private static readonly StringName NetsuAlbedoParam = new StringName("albedo_texture");
	private int _auraWarm = 4;
	private Texture2D[] _netsuAlbedo;
	private Texture2D _netsuAuraTex;

	private void NetsuCreateAura()
	{
		if (Engine.IsEditorHint() || Sprites == null || Sprites.Length == 0 || Sprites[0] == null)
		{
			return;
		}
		Shader shader = ResourceLoader.Exists("res://assets/shaders/netsu_aura.gdshader") ? GD.Load<Shader>("res://assets/shaders/netsu_aura.gdshader") : null;
		if (shader == null)
		{
			return;
		}
		_auraMaterial = new ShaderMaterial();
		_auraMaterial.Shader = shader;
		// Netsu (Oct 26 late): one more flat copy, drawn ON the body: the solid white flash (tech)
		_whiteMaterial = new ShaderMaterial();
		_whiteMaterial.Shader = shader;
		_whiteMaterial.SetShaderParameter(NetsuAuraParam, new Color(1f, 1f, 1f, 1f));
		_white = new Sprite3D();
		_white.Visible = false;
		_white.Centered = Sprites[0].Centered;
		_white.PixelSize = Sprites[0].PixelSize;
		_white.TextureFilter = Sprites[0].TextureFilter;
		_white.Layers = Sprites[0].Layers;
		_white.Shaded = false;
		_white.MaterialOverride = _whiteMaterial;
		Sprites[0].GetParent().CallDeferred(Node.MethodName.AddChild, _white);
		Node parent = Sprites[0].GetParent();
		_aura = new Sprite3D[AuraDirs.Length];
		for (int i = 0; i < _aura.Length; i++)
		{
			Sprite3D s = new Sprite3D();
			s.Visible = false;
			s.Centered = Sprites[0].Centered;
			s.PixelSize = Sprites[0].PixelSize;
			s.TextureFilter = Sprites[0].TextureFilter;
			s.Layers = Sprites[0].Layers;
			s.Shaded = false;
			s.MaterialOverride = _auraMaterial;
			parent.CallDeferred(Node.MethodName.AddChild, s);
			_aura[i] = s;
		}
	}

	private Sprite3D _white;
	private ShaderMaterial _whiteMaterial;
	private float _whiteAmount = -1f;
	private Color _whiteColor = Colors.White;
	private Texture2D _whiteTex;

	/// <summary>Netsu (Oct 26 late, TamaDeez): the whole body sprite drawn solid white, `amount` 0..1 (0 = off).
	/// A flat white copy of the body sprite on top of it (same picture, place, scale and flip). Used by the tech
	/// flash (SakugaActor.NetsuTechFlash). Call after ViewAnimations each render.</summary>
	public void SetWhite(float amount)
	{
		SetWhite(amount, Colors.White);
	}

	/// <summary>Netsu (Oct 26 c15, restored Oct 27 c26): the same flat copy in `color` instead of white (counter hit
	/// red, air counter purple: SakugaActor.NetsuCounterLook). Only the colour's RGB is used; `amount` is the alpha.</summary>
	public void SetWhite(float amount, Color color)
	{
		if (_white == null || !_white.IsInsideTree())
		{
			return;
		}
		Sprite3D body = Sprites[0];
		if (amount <= 0.01f || body.Texture == null || !body.Visible)
		{
			if (_white.Visible)
			{
				_white.Visible = false;
			}
			return;
		}
		if (amount != _whiteAmount || color.R != _whiteColor.R || color.G != _whiteColor.G || color.B != _whiteColor.B)
		{
			_whiteAmount = amount;
			_whiteColor = color;
			_whiteMaterial.SetShaderParameter(NetsuAuraParam, new Color(color.R, color.G, color.B, amount));
		}
		if (body.Texture != _whiteTex)
		{
			_whiteTex = body.Texture;
			_whiteMaterial.SetShaderParameter(NetsuTexParam, _whiteTex);
		}
		_white.Texture = body.Texture;
		_white.Transform = body.Transform;
		_white.Offset = body.Offset;
		_white.FlipH = body.FlipH;
		_white.FlipV = body.FlipV;
		_white.SortingOffset = body.SortingOffset + 0.25f;
		_white.Visible = true;
	}

	/// <summary>Netsu: show the aura in `color` (alpha 0 = off), `width` sprite pixels wide. Call after
	/// ViewAnimations each render.</summary>
	public void SetAura(Color color, float width)
	{
		if (_aura == null)
		{
			return;
		}
		if (_auraWarm > 0 && color.A <= 0.01f && _aura[0].IsInsideTree() && Sprites[0].Texture != null)
		{
			// warm-up: drawn fully transparent (the shader's colour has alpha 0), only to compile it
			_auraWarm--;
			color = new Color(1f, 1f, 1f, 0f);
			width = 1f;
		}
		else if (color.A <= 0.01f)
		{
			if (_auraOn)
			{
				for (int i = 0; i < _aura.Length; i++) _aura[i].Visible = false;
			}
			_auraOn = false;
			return;
		}
		else
		{
			_auraWarm = 0;
		}
		Sprite3D body = Sprites[0];
		if (color != _auraColor)
		{
			_auraMaterial.SetShaderParameter(NetsuAuraParam, color);
			_auraColor = color;
		}
		if (body.Texture != _netsuAuraTex)
		{
			_netsuAuraTex = body.Texture;
			_auraMaterial.SetShaderParameter(NetsuTexParam, _netsuAuraTex);
		}
		for (int i = 0; i < _aura.Length; i++)
		{
			Sprite3D s = _aura[i];
			if (!s.IsInsideTree())
			{
				continue;
			}
			s.Texture = body.Texture;
			s.Transform = body.Transform;
			s.Offset = body.Offset + AuraDirs[i] * width;
			s.FlipH = body.FlipH;
			s.FlipV = body.FlipV;
			s.SortingOffset = body.SortingOffset - 0.25f;
			s.Visible = body.Visible && body.Texture != null;
		}
		_auraOn = true;
	}

	private Color _tint = Colors.White;
	private Color[] _baseModulate;

	/// <summary>Netsu: colour multiplied into the sprite layers (the super flash darkens the frozen
	/// side and pulses the other bright; SakugaActor.NetsuSuperFlashLook). The palette shaders
	/// multiply it in too. Each layer's own modulate (set in its scene) is kept and multiplied.
	/// Afterimages keep their own tint.</summary>
	public void SetTint(Color tint)
	{
		if (Sprites == null || tint == _tint)
		{
			return;
		}
		if (_baseModulate == null)
		{
			_baseModulate = new Color[Sprites.Length];
			for (int i = 0; i < Sprites.Length; i++)
			{
				_baseModulate[i] = Sprites[i] != null ? Sprites[i].Modulate : Colors.White;
			}
		}
		_tint = tint;
		for (int i = 0; i < Sprites.Length; i++)
		{
			if (Sprites[i] != null)
			{
				Sprites[i].Modulate = _baseModulate[i] * tint;
			}
		}
	}

	public void SetDepth(int depth)
	{
		for (int i = 0; i < Sprites.Length; i++)
		{
			// Netsu: extra layers draw just in front of the body
			Sprites[i].SortingOffset = depth + i * 0.5f;
		}
	}

	public void ViewAnimations(AnimationSettings anim)
	{
		ViewAnimations(anim, contact: true);
	}

	/// <param name="contact">true when the current move has hit or been blocked; layers marked
	/// OnlyOnContact are hidden until then.</param>
	public void ViewAnimations(AnimationSettings anim, bool contact)
	{
		if (anim == null || anim.Modifiers == null || anim.Modifiers.Length == 0)
		{
			return;
		}
		for (int i = 0; i < Sprites.Length; i++)
		{
			// Netsu: bounds check first (a frame may fill fewer layers than the fighter has)
			SpriteModifier mod = (i < anim.Modifiers.Length) ? anim.Modifiers[i] : null;
			if (mod == null)
			{
				if (i > 0)
				{
					Sprites[i].Visible = false;
				}
				continue;
			}
			Sprites[i].Visible = !(mod.OnlyOnContact && !contact);
			Sprites[i].Texture = mod.Sprite;
			Sprites[i].Offset = mod.Offset;
			Sprites[i].RotationDegrees = new Vector3(0f, 0f, mod.Rotation);
			Sprites[i].Scale = new Vector3(mod.Scale.X, mod.Scale.Y, 1f);   // Netsu: stretched layers (beams)
			Sprites[i].FlipH = mod.FlipX;
			Sprites[i].FlipV = mod.FlipY;
			if (Sprites[i].MaterialOverride != null && (_netsuAlbedo == null || _netsuAlbedo.Length != Sprites.Length || _netsuAlbedo[i] != mod.Sprite))
			{
				// (Oct 25: only when the picture changes: a texture in a Variant every frame was garbage for the collector)
				_netsuAlbedo ??= new Texture2D[Sprites.Length];
				_netsuAlbedo[i] = mod.Sprite;
				((ShaderMaterial)Sprites[i].MaterialOverride).SetShaderParameter(NetsuAlbedoParam, mod.Sprite);
			}
		}
		NetsuRecordFrame();
		if (Shadow != null)
		{
			Shadow.GlobalPosition = new Vector3(Shadow.GlobalPosition.X, 0.001f, 0f);
			float scaleFactor = Shadow.GlobalPosition.DistanceTo(Sprites[0].GlobalPosition) * 0.25f;
			Shadow.Scale = baseScale * Mathf.Clamp(1f - scaleFactor, 0.1f, 1f);
		}
	}
}
