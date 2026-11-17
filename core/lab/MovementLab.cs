// Netsu VS new core: MOVEMENT LAB (Nov 16 2026).
// Runs on its own (F6 on res://core/lab/movement_lab.tscn): it needs no other scene, autoload or match setup.
// P1 = the p1_* controls (keyboard or pad, from the Controls autoload; arrow keys + Z/X/C if those are missing).
// P2 = a dummy Cecilia, moved by the p2_* controls if a second player wants to.
// Keys: Tab or F1 = panel, F2 = pause, F3 = step one frame, F4 = slow motion, F5 = reset positions.
using System;
using System.Collections.Generic;
using System.Text.Json;
using Godot;
using Netsu.Core;

namespace Netsu.Lab;

public partial class MovementLab : Node2D
{
	const string SavePath = "res://data/core/movement_cecilia.json";
	const int Ring = 16;

	CoreParams _p = CoreParams.Baseline();
	CoreParams _ghostP = CoreParams.OldNetsu();
	World _w, _ghost;
	readonly LabLook _look1 = new(), _look2 = new(), _lookG = new();
	double _acc;
	bool _paused, _step, _ghostOn, _rollbackOn, _trailOn = true, _boxesOn;
	int _slow = 1;

	// rollback check: the last frames and their inputs
	readonly World[] _ring = new World[Ring];
	readonly ushort[] _ringIn1 = new ushort[Ring], _ringIn2 = new ushort[Ring];
	long _rbChecked, _rbMismatch; double _rbMs;

	// measurements
	int _jumpPeak, _jumpStartX, _jumpAir, _lastJumpPeak, _lastJumpAir, _lastJumpDist, _runTop, _lastRunTop, _skidStartX, _lastSkid;
	bool _inAir, _inSkid;
	readonly List<Vector2> _trail = new();
	readonly List<string> _inputLog = new();
	ushort _lastIn1;

	// UI
	CanvasLayer _ui;
	PanelContainer _panel;
	Label _live, _defs, _status;
	VBoxContainer _sliders;
	readonly List<(HSlider s, Label v, System.Reflection.FieldInfo f, TuneAttribute t)> _rows = new();
	OptionButton _preset;
	bool _syncing;

	public override void _Ready()
	{
		TextureFilter = TextureFilterEnum.Linear;
		LoadAttackFrames(_p); LoadAttackFrames(_ghostP);
		TryLoadSaved();
		ResetWorld();
		BuildUi();
		RefreshSliders();
	}

	void LoadAttackFrames(CoreParams p)
	{
		for (int i = 0; i < _look1.AttackAnims.Length; i++)
		{
			var a = _look1.Get(_look1.AttackAnims[i]);
			if (a != null && a.Duration > 0) p.AttackFrames[i] = a.Duration;
		}
	}

	void ResetWorld()
	{
		_w = Sim.NewWorld(_p);
		_ghost = Sim.NewWorld(_ghostP);
		for (int i = 0; i < Ring; i++) _ring[i] = _w;
		_trail.Clear();
	}

	// ------------------------------------------------------------------ input
	static readonly string[] Suffix = { "_up", "_down", "_left", "_right", "_a", "_b", "_c", "_d" };
	static readonly Btn[] Bits = { Btn.Up, Btn.Down, Btn.Left, Btn.Right, Btn.A, Btn.B, Btn.C, Btn.D };

	static ushort ReadPad(string prefix)
	{
		ushort v = 0;
		for (int i = 0; i < Suffix.Length; i++)
		{
			string act = prefix + Suffix[i];
			if (InputMap.HasAction(act) && Input.IsActionPressed(act)) v |= (ushort)Bits[i];
		}
		return v;
	}

	static ushort ReadKeysFallback()
	{
		ushort v = 0;
		if (Input.IsKeyPressed(Key.Up)) v |= (ushort)Btn.Up;
		if (Input.IsKeyPressed(Key.Down)) v |= (ushort)Btn.Down;
		if (Input.IsKeyPressed(Key.Left)) v |= (ushort)Btn.Left;
		if (Input.IsKeyPressed(Key.Right)) v |= (ushort)Btn.Right;
		if (Input.IsKeyPressed(Key.Z)) v |= (ushort)Btn.A;
		if (Input.IsKeyPressed(Key.X)) v |= (ushort)Btn.B;
		if (Input.IsKeyPressed(Key.C)) v |= (ushort)Btn.C;
		return v;
	}

	public override void _Input(InputEvent e)
	{
		if (e is InputEventKey k && k.Pressed && !k.Echo)
		{
			switch (k.Keycode)
			{
				case Key.Tab: case Key.F1: _panel.Visible = !_panel.Visible; GetViewport().SetInputAsHandled(); break;
				case Key.F2: _paused = !_paused; break;
				case Key.F3: _paused = true; _step = true; break;
				case Key.F4: _slow = _slow == 1 ? 2 : _slow == 2 ? 4 : 1; break;
				case Key.F5: ResetWorld(); break;
			}
		}
	}

	// ------------------------------------------------------------------ frame loop (fixed 60 per second)
	public override void _Process(double delta)
	{
		_acc += delta / _slow;
		int steps = 0;
		while (_acc >= 1.0 / 60.0 && steps < 4)
		{
			_acc -= 1.0 / 60.0; steps++;
			if (_paused && !_step) continue;
			_step = false;
			Tick();
		}
		if (steps >= 4) _acc = 0;
		UpdateLive();
		QueueRedraw();
	}

	void Tick()
	{
		ushort in1 = (ushort)(ReadPad("p1") | (InputMap.HasAction("p1_up") ? 0 : ReadKeysFallback()));
		ushort in2 = ReadPad("p2");
		int slot = _w.Frame % Ring;
		_ring[slot] = _w; _ringIn1[slot] = in1; _ringIn2[slot] = in2;
		Sim.Step(ref _w, in1, in2, _p);
		if (_ghostOn) Sim.Step(ref _ghost, in1, in2, _ghostP);
		if (_rollbackOn) RollbackCheck();
		Measure();
		LogInput(in1);
		if (_trailOn && (_w.P1.State is St.Run or St.AirDash or St.AirBackDash || (_w.P1.State == St.Air && _w.P1.JumpKind == 2)))
			_trail.Add(new Vector2(_w.P1.X, _w.P1.Y));
		else if (_trail.Count > 0) _trail.RemoveAt(0);
		while (_trail.Count > 10) _trail.RemoveAt(0);
	}

	/// <summary>Every frame: go back 8 frames, re-simulate them from the saved copy with the same inputs,
	/// and check the result is identical (what online rollback does all the time).</summary>
	void RollbackCheck()
	{
		const int back = 8;
		if (_w.Frame < back + 1) return;
		var t0 = Time.GetTicksUsec();
		int from = _w.Frame - back;
		var r = _ring[from % Ring];
		for (int f = from; f < _w.Frame; f++) Sim.Step(ref r, _ringIn1[f % Ring], _ringIn2[f % Ring], _p);
		_rbMs = (Time.GetTicksUsec() - t0) / 1000.0;
		_rbChecked++;
		if (Sim.Checksum(r) != Sim.Checksum(_w)) _rbMismatch++;
	}

	void Measure()
	{
		ref Fighter f = ref _w.P1;
		if (f.Y > 0 || f.State == St.Air)
		{
			if (!_inAir) { _inAir = true; _jumpPeak = 0; _jumpAir = 0; _jumpStartX = f.X; }
			_jumpAir++; _jumpPeak = Math.Max(_jumpPeak, f.Y);
		}
		else if (_inAir)
		{
			_inAir = false; _lastJumpPeak = _jumpPeak; _lastJumpAir = _jumpAir; _lastJumpDist = Math.Abs(f.X - _jumpStartX);
		}
		if (f.State == St.Run) _runTop = Math.Max(_runTop, Math.Abs(f.Vx));
		else if (_runTop > 0) { _lastRunTop = _runTop; _runTop = 0; }
		if (f.State == St.Skid && !_inSkid) { _inSkid = true; _skidStartX = f.X; }
		if (f.State != St.Skid && _inSkid) { _inSkid = false; _lastSkid = Math.Abs(f.X - _skidStartX); }
	}

	void LogInput(ushort i)
	{
		if (i == _lastIn1) return;
		_lastIn1 = i;
		int face = _w.P1.Facing;
		bool up = (i & (ushort)Btn.Up) != 0, dn = (i & (ushort)Btn.Down) != 0;
		bool fw = Sim.Fwd(i, face), bk = Sim.Back(i, face);
		int num = up ? (bk ? 7 : fw ? 9 : 8) : dn ? (bk ? 1 : fw ? 3 : 2) : (bk ? 4 : fw ? 6 : 5);
		string s = num.ToString();
		if ((i & (ushort)Btn.A) != 0) s += "A";
		if ((i & (ushort)Btn.B) != 0) s += "B";
		if ((i & (ushort)Btn.C) != 0) s += "C";
		if ((i & (ushort)Btn.D) != 0) s += "D";
		_inputLog.Insert(0, s);
		if (_inputLog.Count > 14) _inputLog.RemoveAt(_inputLog.Count - 1);
	}

	// ------------------------------------------------------------------ drawing
	float Zoom => GetViewportRect().Size.X / (_p.ViewWidth / 100f);
	float GroundY => GetViewportRect().Size.Y * 0.86f;

	Vector2 ToScreen(int x, int y)
	{
		var size = GetViewportRect().Size;
		return new Vector2((x - _w.CamX) / 100f * Zoom + size.X / 2f, GroundY - (y - _w.CamY) / 100f * Zoom);
	}

	public override void _Draw()
	{
		var size = GetViewportRect().Size;
		DrawRect(new Rect2(Vector2.Zero, size), new Color(0.09f, 0.085f, 0.12f));
		var font = ThemeDB.FallbackFont;
		// grid: thin line every 100 px, strong line + label every 1 H (500 px), heights every 0.5 H
		int stageHalf = _p.ViewWidth * _p.StageScreens / 2;
		for (int x = -stageHalf; x <= stageHalf; x += 10000)
		{
			var a = ToScreen(x, 0); var b = ToScreen(x, CoreParams.H * 5);
			bool major = x % CoreParams.H == 0;
			DrawLine(a, b, major ? new Color(1, 1, 1, 0.14f) : new Color(1, 1, 1, 0.05f), 1);
			if (major) DrawString(font, a + new Vector2(4, 18), $"{x / CoreParams.H}H", HorizontalAlignment.Left, -1, 13, new Color(1, 1, 1, 0.4f));
		}
		for (int y = 0; y <= CoreParams.H * 5; y += CoreParams.H / 2)
		{
			var a = ToScreen(-stageHalf, y); var b = ToScreen(stageHalf, y);
			DrawLine(a, b, y == 0 ? new Color(0.91f, 0.77f, 0.36f, 0.9f) : new Color(1, 1, 1, y % CoreParams.H == 0 ? 0.12f : 0.05f), y == 0 ? 2 : 1);
			if (y > 0 && y % CoreParams.H == 0) DrawString(font, ToScreen(_w.CamX - _p.ViewWidth / 2, y) + new Vector2(470, -4), $"{y / CoreParams.H}H high", HorizontalAlignment.Left, -1, 13, new Color(1, 1, 1, 0.35f));
		}
		// stage walls
		foreach (int wx in new[] { -stageHalf, stageHalf })
			DrawLine(ToScreen(wx, 0), ToScreen(wx, CoreParams.H * 6), new Color(0.85f, 0.3f, 0.35f, 0.8f), 3);
		DrawRect(new Rect2(0, GroundY, size.X, size.Y - GroundY), new Color(0.06f, 0.055f, 0.08f));

		// trail (lightning streak behind her run / dashes)
		if (_trailOn && _trail.Count > 1)
			for (int i = 1; i < _trail.Count; i++)
			{
				var a = ToScreen((int)_trail[i - 1].X, (int)_trail[i - 1].Y + CoreParams.H / 3);
				var b = ToScreen((int)_trail[i].X, (int)_trail[i].Y + CoreParams.H / 3);
				DrawLine(a, b, new Color(1f, 0.85f, 0.35f, 0.15f + 0.6f * i / _trail.Count), 3 + 6f * i / _trail.Count);
			}

		if (_ghostOn) DrawFighter(_ghost.P1, _lookG, new Color(0.45f, 0.7f, 1f, 0.38f), "old");
		DrawFighter(_w.P2, _look2, new Color(0.62f, 0.58f, 0.72f, 1f), "P2");
		DrawFighter(_w.P1, _look1, Colors.White, null);
	}

	void DrawFighter(in Fighter f, LabLook look, Color tint, string tag)
	{
		var (anim, frame) = look.Pick(f);
		var origin = ToScreen(f.X, f.Y);
		float z = Zoom;
		var fr = anim?.At(frame);
		if (fr == null)
		{
			DrawRect(new Rect2(origin + new Vector2(-30, -250) * z, new Vector2(60, 250) * z), tint);
		}
		else
		{
			foreach (var (tex, off, rot, flipX) in fr.Layers)
			{
				var ts = tex.GetSize();
				bool flip = flipX ^ (f.Facing < 0);
				// offset = left edge and bottom edge (y up) in px from her origin, facing right
				float left = f.Facing > 0 ? off.X : -(off.X + ts.X);
				var topLeft = new Vector2(left, -(off.Y + ts.Y)) * z;
				if (rot != 0) DrawSetTransform(origin, Mathf.DegToRad(f.Facing > 0 ? -rot : rot), Vector2.One);
				else DrawSetTransform(origin, 0, Vector2.One);
				var rect = new Rect2(topLeft, ts * z);
				if (flip) rect = new Rect2(topLeft + new Vector2(ts.X * z, 0), new Vector2(-ts.X * z, ts.Y * z));
				DrawTextureRect(tex, rect, false, tint);
			}
			DrawSetTransform(Vector2.Zero, 0, Vector2.One);
		}
		if (_boxesOn)
		{
			float hw = _p.PushHalfWidth / 100f * z;
			DrawRect(new Rect2(origin + new Vector2(-hw, -CoreParams.H * 0.6f / 100f * z), new Vector2(hw * 2, CoreParams.H * 0.6f / 100f * z)), new Color(1, 1, 0.3f, 0.6f), false, 2);
			DrawCircle(origin, 4, Colors.Yellow);
		}
		if (tag != null) DrawString(ThemeDB.FallbackFont, origin + new Vector2(-14, 22), tag, HorizontalAlignment.Left, -1, 14, tint);
	}

	// ------------------------------------------------------------------ panel
	void BuildUi()
	{
		_ui = new CanvasLayer();
		AddChild(_ui);
		_panel = new PanelContainer();
		_panel.Position = new Vector2(16, 16);
		_panel.CustomMinimumSize = new Vector2(470, 0);
		_panel.Size = new Vector2(470, 1048);
		var sb = new StyleBoxFlat { BgColor = new Color(0.06f, 0.055f, 0.09f, 0.88f), CornerRadiusTopLeft = 10, CornerRadiusTopRight = 10, CornerRadiusBottomLeft = 10, CornerRadiusBottomRight = 10 };
		sb.SetContentMarginAll(12);
		_panel.AddThemeStyleboxOverride("panel", sb);
		_ui.AddChild(_panel);

		var scroll = new ScrollContainer { HorizontalScrollMode = ScrollContainer.ScrollMode.Disabled };
		scroll.CustomMinimumSize = new Vector2(446, 1020);
		_panel.AddChild(scroll);
		var col = new VBoxContainer { SizeFlagsHorizontal = Control.SizeFlags.ExpandFill };
		col.AddThemeConstantOverride("separation", 6);
		scroll.AddChild(col);

		var title = new Label { Text = "MOVEMENT LAB · Cecilia" };
		title.AddThemeColorOverride("font_color", new Color(0.91f, 0.77f, 0.36f));
		title.AddThemeFontSizeOverride("font_size", 20);
		col.AddChild(title);
		col.AddChild(Small("Tab / F1 panel · F2 pause · F3 step · F4 slow · F5 reset", 0.55f));

		_live = new Label(); _live.AddThemeFontSizeOverride("font_size", 14);
		col.AddChild(_live);

		var toggles = new HFlowContainer();
		toggles.AddChild(Toggle("Ghost: old Netsu", v => { _ghostOn = v; _ghost = _w; }));
		toggles.AddChild(Toggle("Rollback check", v => { _rollbackOn = v; _rbChecked = _rbMismatch = 0; }));
		toggles.AddChild(Toggle("Lightning trail", v => _trailOn = v, true));
		toggles.AddChild(Toggle("Body boxes", v => _boxesOn = v));
		col.AddChild(toggles);

		var presetRow = new HBoxContainer();
		_preset = new OptionButton();
		_preset.AddItem("Baseline (BlazBlue-inspired)"); _preset.AddItem("Old Netsu (Sakuga, Nov 13)");
		_preset.ItemSelected += i => { _p = i == 0 ? CoreParams.Baseline() : CoreParams.OldNetsu(); LoadAttackFrames(_p); RefreshSliders(); SetStatus("Preset: " + _preset.GetItemText((int)i)); };
		presetRow.AddChild(_preset);
		var save = new Button { Text = "Save" }; save.Pressed += Save; presetRow.AddChild(save);
		var load = new Button { Text = "Load saved" }; load.Pressed += () => { if (TryLoadSaved()) { RefreshSliders(); SetStatus("Loaded " + SavePath); } else SetStatus("Nothing saved yet"); };
		presetRow.AddChild(load);
		col.AddChild(presetRow);
		_status = Small("", 0.7f); col.AddChild(_status);

		_defs = Small("Hover a slider to see what it means.", 0.85f);
		_defs.AutowrapMode = TextServer.AutowrapMode.WordSmart;
		_defs.CustomMinimumSize = new Vector2(430, 56);
		col.AddChild(_defs);

		_sliders = new VBoxContainer();
		col.AddChild(_sliders);
		string group = null;
		foreach (var (f, t) in CoreParams.Tunables())
		{
			if (t.Group != group)
			{
				group = t.Group;
				var g = new Label { Text = group.ToUpper() };
				g.AddThemeColorOverride("font_color", new Color(0.95f, 0.65f, 0.76f));
				g.AddThemeFontSizeOverride("font_size", 13);
				_sliders.AddChild(g);
			}
			var row = new HBoxContainer();
			var name = new Label { Text = t.Label, CustomMinimumSize = new Vector2(170, 0), TooltipText = t.Definition, MouseFilter = Control.MouseFilterEnum.Pass };
			name.AddThemeFontSizeOverride("font_size", 13);
			bool scaled = t.Unit.StartsWith("px");
			var s = new HSlider { MinValue = t.Min, MaxValue = t.Max, Step = 1, CustomMinimumSize = new Vector2(170, 0), SizeFlagsHorizontal = Control.SizeFlags.ExpandFill, TooltipText = t.Definition };
			var v = new Label { CustomMinimumSize = new Vector2(84, 0), HorizontalAlignment = HorizontalAlignment.Right };
			v.AddThemeFontSizeOverride("font_size", 13);
			var field = f; var tune = t;
			s.ValueChanged += val => { if (_syncing) return; field.SetValue(_p, (int)val); ShowValue(v, (int)val, tune); };
			s.MouseEntered += () => _defs.Text = $"{tune.Label} ({tune.Unit}): {tune.Definition}";
			name.MouseEntered += () => _defs.Text = $"{tune.Label} ({tune.Unit}): {tune.Definition}";
			row.AddChild(name); row.AddChild(s); row.AddChild(v);
			_sliders.AddChild(row);
			_rows.Add((s, v, f, t));
		}

		col.AddChild(Small(Glossary, 0.6f, true));
	}

	const string Glossary =
		"WORDS\n" +
		"H: Cecilia's height on screen, 500 px. Distances and heights are given in px and H.\n" +
		"f: one frame, 1/60 of a second. px/f: pixels moved per frame (×60 = per second).\n" +
		"px/f²: how much a speed changes every frame (gravity, braking, acceleration).\n" +
		"Momentum: speed that carries over from one action into the next (run into a jump, an attack or a landing).\n" +
		"Buffer: an input pressed a little early that still comes out as soon as she can act.\n" +
		"Air actions: double jumps and air dashes; each jump gives this many.\n" +
		"Prejump: the frames on the ground before a jump leaves the floor.\n" +
		"Landing lag: frames after touching the floor before she can act.\n" +
		"Rollback check: every frame the lab rewinds 8 frames and replays them; any difference is a desync bug.";

	static Label Small(string text, float alpha, bool wrap = false)
	{
		var l = new Label { Text = text };
		l.AddThemeFontSizeOverride("font_size", 12);
		l.AddThemeColorOverride("font_color", new Color(1, 1, 1, alpha));
		if (wrap) { l.AutowrapMode = TextServer.AutowrapMode.WordSmart; l.CustomMinimumSize = new Vector2(430, 0); }
		return l;
	}

	static CheckBox Toggle(string text, Action<bool> on, bool start = false)
	{
		var c = new CheckBox { Text = text, ButtonPressed = start };
		c.AddThemeFontSizeOverride("font_size", 13);
		c.Toggled += v => on(v);
		return c;
	}

	static void ShowValue(Label v, int val, TuneAttribute t)
	{
		v.Text = t.Unit.StartsWith("px") ? $"{val / 100.0:0.##} {t.Unit}" : (t.Unit.Length > 0 ? $"{val} {t.Unit}" : $"{val}");
	}

	void RefreshSliders()
	{
		_syncing = true;
		foreach (var (s, v, f, t) in _rows)
		{
			int val = (int)f.GetValue(_p);
			s.Value = val;
			ShowValue(v, val, t);
		}
		_syncing = false;
	}

	void SetStatus(string s) { if (_status != null) _status.Text = s; }

	void UpdateLive()
	{
		if (_live == null) return;
		ref Fighter f = ref _w.P1;
		string H(int u) => $"{u / 100.0:0} px ({u / (double)CoreParams.H:0.00} H)";
		string V(int u) => $"{u / 100.0:0.0} px/f";
		var rb = _rollbackOn ? $"\nRollback check: {_rbChecked} frames re-played, {_rbMismatch} mismatches ({_rbMs:0.00} ms for 8 frames)" : "";
		_live.Text =
			$"State  {f.State}  (frame {f.StateFrame}){(_paused ? "   PAUSED" : "")}{(_slow > 1 ? $"   1/{_slow} speed" : "")}\n" +
			$"Speed  x {V(f.Vx)}   y {V(f.Vy)}\n" +
			$"Height {H(f.Y)}\n" +
			$"Air actions left {f.AirActionsLeft}  (jumps {f.AirJumpsLeft}, dashes {f.AirDashesLeft})   buffered: {f.Buffered}\n" +
			$"Last jump: peak {H(_lastJumpPeak)}, {_lastJumpAir} f in the air, {H(_lastJumpDist)} across\n" +
			$"Last run: top {V(_lastRunTop)}   last skid {H(_lastSkid)}\n" +
			$"Inputs  {string.Join(" ", _inputLog)}" + rb;
	}

	// ------------------------------------------------------------------ save / load
	void Save()
	{
		var d = new Dictionary<string, int>();
		foreach (var (f, _) in CoreParams.Tunables()) d[f.Name] = (int)f.GetValue(_p);
		DirAccess.MakeDirRecursiveAbsolute(ProjectSettings.GlobalizePath("res://data/core"));
		using var file = FileAccess.Open(SavePath, FileAccess.ModeFlags.Write);
		if (file == null) { SetStatus("Couldn't write " + SavePath); return; }
		file.StoreString(JsonSerializer.Serialize(d, new JsonSerializerOptions { WriteIndented = true }));
		SetStatus("Saved to " + SavePath);
	}

	bool TryLoadSaved()
	{
		if (!FileAccess.FileExists(SavePath)) return false;
		using var file = FileAccess.Open(SavePath, FileAccess.ModeFlags.Read);
		var d = JsonSerializer.Deserialize<Dictionary<string, int>>(file.GetAsText());
		if (d == null) return false;
		foreach (var (f, _) in CoreParams.Tunables())
			if (d.TryGetValue(f.Name, out int v)) f.SetValue(_p, v);
		return true;
	}
}
