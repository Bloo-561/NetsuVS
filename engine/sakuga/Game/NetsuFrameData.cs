#nullable disable
using System;
using System.Collections.Generic;
using System.Globalization;
using System.Reflection;
using System.Text;
using System.Text.Json;
using Godot;
using SakugaEngine.Global;
using SakugaEngine.Resources;

namespace SakugaEngine.Game;

/// <summary>
/// Netsu (Oct 25 2026): the frame data spreadsheets. Each fighter has an Excel workbook in data/frame_data
/// (Cecilia.xlsx, Flan.xlsx, Leticia.xlsx, Noah.xlsx) and the assists share Assists.xlsx: one row per move (state) with its
/// start-up, active and recovery frames, damage, hitstun, blockstun, guard, knockdown, pushback, launch, meter... Change
/// a number, save the file, and the game uses it: at the start of every match, and in Training right away (the moment
/// the file is saved).
///
/// Only the cells you CHANGED are used. data/frame_data/frame_data.json remembers what every cell said when the sheets
/// were made (tools/frame_data/make_sheets.py writes both); a cell that still says that leaves the game's own data alone,
/// so moves updated in the game since then keep their new numbers unless you changed that cell yourself.
///
/// Frames: changing start-up / active / recovery re-times the WHOLE move to fit - its pictures, hitboxes, sounds,
/// effects, movement starts, cancel windows and follow-up timings all slide with the part of the move they belong to.
/// Hit values: a move with several hits shows its first hit; a change is passed on to every hit (damage, chip, pushback,
/// launch and meter by the same percentage; hitstun, blockstun, hitstop and scaling by the same number of frames).
///
/// Everything is applied the same way on every copy of the game, before the fight starts; online, both players need the
/// same spreadsheets (OnlineSignature goes into the connection check). A cell that can't be read is skipped and
/// reported (LastReport, and the Godot output).
/// </summary>
public static class NetsuFrameData
{
	public const string Folder = "res://data/frame_data/";
	public const string ManifestPath = Folder + "frame_data.json";
	/// <summary>Meter per bar (the HUD's 100%).</summary>
	public const int MeterPerBar = 2000;

	/// <summary>What the last apply did: "Cecilia: 5A startup 6 -> 8; ..." plus anything that couldn't be read.</summary>
	public static string LastReport = "";
	private static readonly List<string> _pending = new List<string>();

	/// <summary>Everything applied since the last call, one line per fighter / assist ("" = nothing changed).</summary>
	public static string TakeReport()
	{
		string text = string.Join("\n", _pending);
		_pending.Clear();
		return text;
	}

	private sealed class Entry
	{
		public string File = "";
		public string Kind = "";   // "fighter" | "assists"
		public string Data = "";   // fighter: res:// path of its 0_XXX_Data.tres
		public string Name = "";   // fighter: "Cecilia"
		public readonly Dictionary<string, string> Assists = new Dictionary<string, string>();   // assist name -> data path
		/// <summary>sheet -> row ID -> column -> what the cell said when the sheet was made</summary>
		public readonly Dictionary<string, Dictionary<string, Dictionary<string, JsonElement>>> Baseline =
			new Dictionary<string, Dictionary<string, Dictionary<string, JsonElement>>>();
	}

	private struct Edit
	{
		public string Sheet;
		public string Row;
		public string Column;
		public bool IsNumber;
		public double Number;
		public string Text;
		public string Was;
	}

	private static List<Entry> _manifest;
	private static ulong _manifestTime;
	/// <summary>Undo list per scope (a fighter's data path, "assist:Mary"): puts every changed value back as it was.</summary>
	private static readonly Dictionary<string, List<Action>> _restore = new Dictionary<string, List<Action>>();
	/// <summary>Spreadsheets read so far -> their modified time then (Training reloads when one changes).</summary>
	private static readonly Dictionary<string, ulong> _watched = new Dictionary<string, ulong>();
	private static readonly Dictionary<string, (ulong time, List<Edit> edits, List<string> problems)> _editCache =
		new Dictionary<string, (ulong, List<Edit>, List<string>)>();

	// --- Applying -------------------------------------------------------------------------------------------------

	/// <summary>Puts this fighter's spreadsheet into its data (call before the fighter is initialised). Safe to call
	/// again: everything goes back to the game's own values first.</summary>
	public static void ApplyFighter(DataContainer data)
	{
		if (data == null || string.IsNullOrEmpty(data.ResourcePath))
		{
			return;
		}
		string scope = data.ResourcePath;
		Restore(scope);
		Entry entry = null;
		foreach (Entry e in Manifest())
		{
			if (e.Kind == "fighter" && string.Equals(e.Data, data.ResourcePath, StringComparison.OrdinalIgnoreCase))
			{
				entry = e;
				break;
			}
		}
		if (entry == null)
		{
			return;
		}
		List<Edit> edits = ReadEdits(entry, out List<string> problems);
		var report = new List<string>(problems);
		var states = new Dictionary<int, List<Edit>>();
		foreach (Edit ed in edits)
		{
			if (ed.Sheet == "Fighter")
			{
				ApplyFighterValue(scope, data, ed, report);
				continue;
			}
			if (!int.TryParse(ed.Row, NumberStyles.Integer, CultureInfo.InvariantCulture, out int index))
			{
				continue;
			}
			if (!states.TryGetValue(index, out List<Edit> list))
			{
				states[index] = list = new List<Edit>();
			}
			list.Add(ed);
		}
		ApplyStates(scope, data, states, entry.Name, report);
		Report(entry.Name, report);
	}

	/// <summary>Puts the Assists spreadsheet's rows for this assist into its data and its moves' cooldowns, and the
	/// rows of what it sends out ("Mary (note)": its own data, loaded from the path the manifest gives).</summary>
	public static void ApplyAssist(NetsuAssistElement element, DataContainer data)
	{
		if (element == null || data == null)
		{
			return;
		}
		string name = element.AssistName ?? "";
		Entry entry = null;
		foreach (Entry e in Manifest())
		{
			if (e.Kind == "assists")
			{
				entry = e;
				break;
			}
		}
		if (entry == null)
		{
			Restore("assist:" + name);
			return;
		}
		List<Edit> edits = ReadEdits(entry, out List<string> problems);
		foreach (KeyValuePair<string, string> part in entry.Assists)
		{
			bool main = part.Key == name;
			if (!main && !part.Key.StartsWith(name + " (", StringComparison.Ordinal))
			{
				continue;
			}
			string scope = "assist:" + part.Key;
			Restore(scope);
			DataContainer partData = main ? data : (ResourceLoader.Exists(part.Value) ? GD.Load<DataContainer>(part.Value) : null);
			if (partData == null)
			{
				continue;
			}
			var report = new List<string>();
			var states = new Dictionary<int, List<Edit>>();
			string prefix = part.Key + ":";
			foreach (Edit ed in edits)
			{
				if (!ed.Row.StartsWith(prefix, StringComparison.Ordinal)
					|| !int.TryParse(ed.Row.Substring(prefix.Length), NumberStyles.Integer, CultureInfo.InvariantCulture, out int index))
				{
					continue;
				}
				if (ed.Column == "Cooldown")
				{
					if (!main)
					{
						continue;
					}
					if (!ed.IsNumber || ed.Number < 0)
					{
						report.Add(ed.Row + " cooldown: \"" + ed.Text + "\" isn't a number of frames");
						continue;
					}
					foreach (NetsuAssistMove m in element.Moves ?? Array.Empty<NetsuAssistMove>())
					{
						if (m != null && m.StateIndex == index)
						{
							int old = m.Cooldown;
							NetsuAssistMove mm = m;
							Record(scope, () => mm.Cooldown = old);
							m.Cooldown = Round(ed.Number);
							report.Add(m.MoveName + " cooldown " + ed.Was + " -> " + m.Cooldown);
						}
					}
					continue;
				}
				if (!states.TryGetValue(index, out List<Edit> list))
				{
					states[index] = list = new List<Edit>();
				}
				list.Add(ed);
			}
			ApplyStates(scope, partData, states, part.Key, report);
			foreach (string p in problems)
			{
				if (p.Contains(prefix))
				{
					report.Add(p);
				}
			}
			Report(part.Key, report);
		}
	}

	/// <summary>Training: has a spreadsheet the fighters use been saved since it was read? (Checked twice a second.)</summary>
	public static bool Changed()
	{
		foreach (KeyValuePair<string, ulong> w in _watched)
		{
			if (FileAccess.FileExists(w.Key) && FileAccess.GetModifiedTime(w.Key) != w.Value)
			{
				return true;
			}
		}
		return FileAccess.FileExists(ManifestPath) && _manifest != null && FileAccess.GetModifiedTime(ManifestPath) != _manifestTime;
	}

	/// <summary>A short code for "which changes the spreadsheets make" (all of them, every fighter and assist): two
	/// copies of the game can only play online when theirs match. "fd0" = no changes.</summary>
	public static string OnlineSignature()
	{
		var lines = new List<string>();
		foreach (Entry e in Manifest())
		{
			foreach (Edit ed in ReadEdits(e, out _))
			{
				lines.Add(e.File + "|" + ed.Sheet + "|" + ed.Row + "|" + ed.Column + "|"
					+ (ed.IsNumber ? ed.Number.ToString("R", CultureInfo.InvariantCulture) : ed.Text.Trim().ToLowerInvariant()));
			}
		}
		if (lines.Count == 0)
		{
			return "fd0";
		}
		lines.Sort(StringComparer.Ordinal);
		uint hash = 2166136261;
		foreach (byte b in Encoding.UTF8.GetBytes(string.Join("\n", lines)))
		{
			hash = (hash ^ b) * 16777619;
		}
		return "fd" + lines.Count + "-" + hash.ToString("x8");
	}

	// --- The manifest and the sheets ------------------------------------------------------------------------------

	private static List<Entry> Manifest()
	{
		if (!FileAccess.FileExists(ManifestPath))
		{
			_manifest = new List<Entry>();
			return _manifest;
		}
		ulong time = FileAccess.GetModifiedTime(ManifestPath);
		if (_manifest != null && time == _manifestTime)
		{
			return _manifest;
		}
		_manifestTime = time;
		_manifest = new List<Entry>();
		_editCache.Clear();
		try
		{
			using JsonDocument doc = JsonDocument.Parse(FileAccess.GetFileAsString(ManifestPath));
			foreach (JsonElement f in doc.RootElement.GetProperty("files").EnumerateArray())
			{
				var e = new Entry
				{
					File = Str(f, "file"),
					Kind = Str(f, "kind"),
					Data = Str(f, "data"),
					Name = Str(f, "name"),
				};
				if (f.TryGetProperty("assists", out JsonElement a) && a.ValueKind == JsonValueKind.Object)
				{
					foreach (JsonProperty p in a.EnumerateObject())
					{
						e.Assists[p.Name] = p.Value.GetString();
					}
				}
				if (f.TryGetProperty("baseline", out JsonElement b) && b.ValueKind == JsonValueKind.Object)
				{
					foreach (JsonProperty sheet in b.EnumerateObject())
					{
						var rows = new Dictionary<string, Dictionary<string, JsonElement>>();
						foreach (JsonProperty row in sheet.Value.EnumerateObject())
						{
							var cols = new Dictionary<string, JsonElement>();
							foreach (JsonProperty c in row.Value.EnumerateObject())
							{
								cols[c.Name] = c.Value.Clone();
							}
							rows[row.Name] = cols;
						}
						e.Baseline[sheet.Name] = rows;
					}
				}
				_manifest.Add(e);
			}
		}
		catch (Exception ex)
		{
			GD.PushWarning("Frame data: can't read " + ManifestPath + ": " + ex.Message);
		}
		return _manifest;
	}

	private static string Str(JsonElement e, string key)
	{
		return e.TryGetProperty(key, out JsonElement v) && v.ValueKind == JsonValueKind.String ? v.GetString() : "";
	}

	/// <summary>The cells that no longer say what they said when the sheet was made.</summary>
	private static List<Edit> ReadEdits(Entry entry, out List<string> problems)
	{
		string path = Folder + entry.File;
		problems = new List<string>();
		if (!FileAccess.FileExists(path))
		{
			return new List<Edit>();
		}
		ulong time = FileAccess.GetModifiedTime(path);
		_watched[path] = 0;   // until it has been read: Training keeps trying
		if (_editCache.TryGetValue(path, out var cached) && cached.time == time)
		{
			_watched[path] = time;
			problems = new List<string>(cached.problems);
			return cached.edits;
		}
		var edits = new List<Edit>();
		Dictionary<string, List<List<string>>> sheets;
		try
		{
			byte[] bytes = FileAccess.GetFileAsBytes(path);
			if (bytes == null || bytes.Length == 0)
			{
				problems.Add(entry.File + " couldn't be opened (is it still being saved?)");
				return edits;   // not cached: tried again next time
			}
			sheets = NetsuXlsx.Read(bytes);
		}
		catch (Exception ex)
		{
			problems.Add(entry.File + " couldn't be read: " + ex.Message);
			return edits;
		}
		foreach (KeyValuePair<string, Dictionary<string, Dictionary<string, JsonElement>>> baseSheet in entry.Baseline)
		{
			if (!sheets.TryGetValue(baseSheet.Key, out List<List<string>> rows))
			{
				problems.Add(entry.File + ": the \"" + baseSheet.Key + "\" sheet is missing (renamed?)");
				continue;
			}
			// the header row: the first row with an "ID" cell
			int headerRow = -1;
			int idCol = -1;
			for (int r = 0; r < Math.Min(rows.Count, 20) && headerRow < 0; r++)
			{
				for (int c = 0; c < rows[r].Count; c++)
				{
					if (rows[r][c].Trim() == "ID")
					{
						headerRow = r;
						idCol = c;
						break;
					}
				}
			}
			if (headerRow < 0)
			{
				problems.Add(entry.File + ": no \"ID\" column on the \"" + baseSheet.Key + "\" sheet");
				continue;
			}
			var columns = new Dictionary<string, int>();
			for (int c = 0; c < rows[headerRow].Count; c++)
			{
				string h = rows[headerRow][c].Trim();
				if (h != "" && !columns.ContainsKey(h))
				{
					columns[h] = c;
				}
			}
			for (int r = headerRow + 1; r < rows.Count; r++)
			{
				List<string> row = rows[r];
				if (idCol >= row.Count)
				{
					continue;
				}
				string id = NormalizeId(row[idCol]);
				if (id == "" || !baseSheet.Value.TryGetValue(id, out Dictionary<string, JsonElement> baseRow))
				{
					continue;
				}
				foreach (KeyValuePair<string, JsonElement> cell in baseRow)
				{
					if (!columns.TryGetValue(cell.Key, out int c) || c >= row.Count)
					{
						continue;
					}
					string text = row[c].Trim();
					if (text == "")
					{
						continue;   // an emptied cell: leave the game's value
					}
					if (cell.Value.ValueKind == JsonValueKind.Number)
					{
						double was = cell.Value.GetDouble();
						if (!TryNumber(text, out double v))
						{
							problems.Add(entry.File + " " + id + " " + cell.Key + ": \"" + text + "\" isn't a number");
							continue;
						}
						if (Math.Abs(v - was) < 1e-6)
						{
							continue;
						}
						edits.Add(new Edit { Sheet = baseSheet.Key, Row = id, Column = cell.Key, IsNumber = true, Number = v, Text = text,
							Was = was.ToString(CultureInfo.InvariantCulture) });
					}
					else if (cell.Value.ValueKind == JsonValueKind.String)
					{
						string was = cell.Value.GetString() ?? "";
						if (string.Equals(text, was.Trim(), StringComparison.OrdinalIgnoreCase))
						{
							continue;
						}
						bool number = TryNumber(text, out double v);
						edits.Add(new Edit { Sheet = baseSheet.Key, Row = id, Column = cell.Key, IsNumber = number, Number = v, Text = text, Was = was });
					}
				}
			}
		}
		_editCache[path] = (time, edits, new List<string>(problems));
		_watched[path] = time;
		return edits;
	}

	private static string NormalizeId(string text)
	{
		text = text.Trim();
		if (double.TryParse(text, NumberStyles.Float, CultureInfo.InvariantCulture, out double d) && d == Math.Floor(d) && Math.Abs(d) < 1e9)
		{
			return ((long)d).ToString(CultureInfo.InvariantCulture);
		}
		return text;
	}

	private static bool TryNumber(string text, out double value)
	{
		text = text.Trim().TrimEnd('%');
		if (double.TryParse(text, NumberStyles.Float, CultureInfo.InvariantCulture, out value))
		{
			return true;
		}
		// "1,5" from a sheet typed with a decimal comma
		return text.Contains(',') && !text.Contains('.')
			&& double.TryParse(text.Replace(',', '.'), NumberStyles.Float, CultureInfo.InvariantCulture, out value);
	}

	private static int Round(double v)
	{
		return (int)Math.Round(v, MidpointRounding.AwayFromZero);
	}

	// --- Undo -----------------------------------------------------------------------------------------------------

	private static void Record(string scope, Action undo)
	{
		if (!_restore.TryGetValue(scope, out List<Action> list))
		{
			_restore[scope] = list = new List<Action>();
		}
		list.Add(undo);
	}

	private static void Restore(string scope)
	{
		if (!_restore.TryGetValue(scope, out List<Action> list))
		{
			return;
		}
		for (int i = list.Count - 1; i >= 0; i--)
		{
			list[i]();
		}
		list.Clear();
	}

	private static void Report(string who, List<string> lines)
	{
		if (lines.Count == 0)
		{
			return;
		}
		LastReport = who + ": " + string.Join("; ", lines);
		_pending.Add(LastReport);
		GD.Print("Frame data - " + LastReport);
	}

	// --- Fighter-wide values (the "Fighter" sheet) ----------------------------------------------------------------

	private static void ApplyFighterValue(string scope, DataContainer data, Edit ed, List<string> report)
	{
		if (!ed.IsNumber || ed.Number < 0)
		{
			report.Add(ed.Row + ": \"" + ed.Text + "\" isn't a number");
			return;
		}
		int v = Round(ed.Number);
		switch (ed.Row)
		{
		case "Health":
			{
				int old = data.MaxHealth;
				Record(scope, () => data.MaxHealth = old);
				data.MaxHealth = Math.Max(1, v);
				break;
			}
		case "Attack":
			{
				ushort old = data.BaseAttack;
				Record(scope, () => data.BaseAttack = old);
				data.BaseAttack = (ushort)Math.Clamp(v, 1, 1000);
				break;
			}
		case "Defense":
			{
				ushort old = data.BaseDefense;
				Record(scope, () => data.BaseDefense = old);
				data.BaseDefense = (ushort)Math.Clamp(v, 1, 1000);
				break;
			}
		default:
			return;
		}
		report.Add(ed.Row + " " + ed.Was + " -> " + v);
	}

	// --- Moves ----------------------------------------------------------------------------------------------------

	/// <summary>Where a move's parts are, in frames of its state (0 = its first frame).</summary>
	public struct Timing
	{
		public bool HasAttack;
		public int First;      // first frame with an attack box (0-based)
		public int Last;       // last frame with an attack box
		public int Duration;   // the state's length
		public int Startup => First + 1;
		public int Active => Last - First + 1;
		public int Recovery => Duration - Last - 1;
	}

	/// <summary>The frames of a state's animation data that have an attack (hit, projectile, throw or counter box).</summary>
	public static Timing TimingOf(AnimationData ad)
	{
		var t = new Timing { Duration = ad != null ? ad.Duration : 0, First = -1, Last = -1 };
		if (ad?.Hitboxes == null)
		{
			return t;
		}
		for (int i = 0; i < ad.Hitboxes.Length; i++)
		{
			HitboxState key = ad.Hitboxes[i];
			if (key == null || !HasAttack(key.HitboxData))
			{
				continue;
			}
			int start = key.AtFrame;
			int end = t.Duration - 1;
			for (int j = i + 1; j < ad.Hitboxes.Length; j++)
			{
				if (ad.Hitboxes[j] != null)
				{
					end = Math.Min(end, ad.Hitboxes[j].AtFrame - 1);
					break;
				}
			}
			if (end < start || start >= t.Duration)
			{
				continue;
			}
			if (!t.HasAttack || start < t.First)
			{
				t.First = start;
			}
			if (!t.HasAttack || end > t.Last)
			{
				t.Last = end;
			}
			t.HasAttack = true;
		}
		return t;
	}

	private static bool IsAttack(HitboxElement el)
	{
		return el != null && (el.HitboxType == HitboxType.HITBOX || el.HitboxType == HitboxType.PROJECTILE
			|| el.HitboxType == HitboxType.THROW || el.HitboxType == HitboxType.COUNTER);
	}

	private static bool HasAttack(HitboxSettings hs)
	{
		if (hs?.Hitboxes == null)
		{
			return false;
		}
		foreach (HitboxElement el in hs.Hitboxes)
		{
			if (IsAttack(el))
			{
				return true;
			}
		}
		return false;
	}

	/// <summary>The boxes a hit value change goes to: every hit / projectile box of the state (or its throw or counter
	/// boxes when it has neither), each once. The first one is the move's first hit: what the sheet shows.</summary>
	public static List<HitboxElement> AttackBoxes(AnimationData ad)
	{
		var hits = new List<HitboxElement>();
		var others = new List<HitboxElement>();
		var seen = new HashSet<HitboxElement>();
		if (ad?.Hitboxes == null)
		{
			return hits;
		}
		foreach (HitboxState key in ad.Hitboxes)
		{
			if (key?.HitboxData?.Hitboxes == null)
			{
				continue;
			}
			foreach (HitboxElement el in key.HitboxData.Hitboxes)
			{
				if (!IsAttack(el) || !seen.Add(el))
				{
					continue;
				}
				if (el.HitboxType == HitboxType.HITBOX || el.HitboxType == HitboxType.PROJECTILE)
				{
					hits.Add(el);
				}
				else
				{
					others.Add(el);
				}
			}
		}
		return hits.Count > 0 ? hits : others;
	}

	/// <summary>Frame f of the old timing -> where it goes in the new one. f is a boundary ("from frame f on"): the
	/// start of active lands on the new start, the frame after active on the start of the new recovery, the end on the
	/// new end. Each part is stretched evenly; frames past the end keep their distance from it.</summary>
	private sealed class Mapper
	{
		private readonly int _s0, _a0, _d0, _s1, _a1, _d1;   // start of active, end of active (exclusive), end
		private readonly bool _even;

		public Mapper(Timing old, int startup, int active, int recovery)
		{
			_s0 = old.First;
			_a0 = old.Last + 1;
			_d0 = old.Duration;
			_s1 = startup - 1;
			_a1 = _s1 + active;
			_d1 = _a1 + recovery;
		}

		/// <summary>A move with no attack: the whole state stretched to `duration`.</summary>
		public Mapper(int oldDuration, int duration)
		{
			_even = true;
			_d0 = Math.Max(1, oldDuration);
			_d1 = duration;
		}

		public int NewDuration => _d1;

		public int Map(int f)
		{
			if (f < 0)
			{
				return f;
			}
			if (_even)
			{
				return f >= _d0 ? _d1 + (f - _d0) : Scale(f, _d1, _d0);
			}
			if (f <= _s0)
			{
				return _s0 == 0 ? 0 : Scale(f, _s1, _s0);
			}
			if (f <= _a0)
			{
				return _s1 + Scale(f - _s0, _a1 - _s1, _a0 - _s0);
			}
			if (f <= _d0)
			{
				return _d0 == _a0 ? _a1 : _a1 + Scale(f - _a0, _d1 - _a1, _d0 - _a0);
			}
			return _d1 + (f - _d0);
		}

		/// <summary>The last frame of a range that ends on old frame `last` (inclusive).</summary>
		public int MapLast(int first, int last)
		{
			return Math.Max(Map(first), Map(last + 1) - 1);
		}

		private static int Scale(int x, int num, int den)
		{
			// x * num / den, rounded half up (whole numbers: the same on every computer)
			return (int)((2L * x * num + den) / (2L * den));
		}
	}

	private static readonly string[] TimingColumns = { "Startup", "Active", "Recovery", "Total" };

	private static void ApplyStates(string scope, DataContainer data, Dictionary<int, List<Edit>> states, string who,
		List<string> report)
	{
		if (states.Count == 0 || data.States == null)
		{
			return;
		}
		// 1. new timings
		var maps = new Dictionary<int, Mapper>();
		var byAnimation = new Dictionary<AnimationData, List<int>>();
		for (int i = 0; i < data.States.Length; i++)
		{
			AnimationData ad = data.States[i]?.AnimationData;
			if (ad == null)
			{
				continue;
			}
			if (!byAnimation.TryGetValue(ad, out List<int> users))
			{
				byAnimation[ad] = users = new List<int>();
			}
			users.Add(i);
		}
		foreach (KeyValuePair<int, List<Edit>> st in states)
		{
			if (st.Key < 0 || st.Key >= data.States.Length || data.States[st.Key]?.AnimationData == null)
			{
				report.Add("row " + st.Key + ": there's no such state");
				continue;
			}
			FighterState state = data.States[st.Key];
			Timing t = TimingOf(state.AnimationData);
			int startup = t.Startup, active = t.Active, recovery = t.Recovery, total = t.Duration;
			bool timing = false;
			foreach (Edit ed in st.Value)
			{
				if (Array.IndexOf(TimingColumns, ed.Column) < 0)
				{
					continue;
				}
				string label = state.StateName + " " + ed.Column.ToLowerInvariant();
				if (!ed.IsNumber)
				{
					report.Add(label + ": \"" + ed.Text + "\" isn't a number of frames");
					continue;
				}
				int v = Round(ed.Number);
				bool ok = true;
				switch (ed.Column)
				{
				case "Startup":
					ok = t.HasAttack && t.First > 0 && v >= 1 && v <= 600;
					startup = v;
					break;
				case "Active":
					ok = t.HasAttack && v >= 1 && v <= 600;
					active = v;
					break;
				case "Recovery":
					ok = t.HasAttack && t.Recovery > 0 && v >= 0 && v <= 600;
					recovery = v;
					break;
				case "Total":
					ok = !t.HasAttack && v >= 1 && v <= 1200;
					total = v;
					break;
				}
				if (!ok)
				{
					report.Add(label + ": " + v + " can't be used here");
					continue;
				}
				timing = true;
				report.Add(label + " " + ed.Was + " -> " + v);
			}
			if (timing)
			{
				Mapper map = t.HasAttack ? new Mapper(t, startup, active, recovery) : new Mapper(t.Duration, total);
				foreach (int user in byAnimation[state.AnimationData])
				{
					maps[user] = map;   // states sharing the same animation data move together
				}
			}
		}
		// 2. re-time the animation data, the states' own events and the moves' cancel windows
		var doneAnimations = new HashSet<AnimationData>();
		foreach (KeyValuePair<int, Mapper> m in maps)
		{
			FighterState state = data.States[m.Key];
			AnimationData ad = state.AnimationData;
			if (doneAnimations.Add(ad))
			{
				RetimeAnimation(scope, ad, m.Value);
			}
			RetimeConditions(scope, state, m.Value);
		}
		if (maps.Count > 0)
		{
			RetimeGoToFrames(scope, data, maps);
			RetimeMoves(scope, data, maps);
		}
		// 3. hit values and move costs
		foreach (KeyValuePair<int, List<Edit>> st in states)
		{
			if (st.Key < 0 || st.Key >= data.States.Length || data.States[st.Key]?.AnimationData == null)
			{
				continue;
			}
			FighterState state = data.States[st.Key];
			List<HitboxElement> boxes = AttackBoxes(state.AnimationData);
			foreach (Edit ed in st.Value)
			{
				if (Array.IndexOf(TimingColumns, ed.Column) >= 0)
				{
					continue;
				}
				string label = state.StateName + " " + ed.Column.ToLowerInvariant();
				if (ed.Column == "Cost" || ed.Column == "Pause")
				{
					ApplyMoveValue(scope, data, st.Key, ed, label, report);
					continue;
				}
				if (boxes.Count == 0)
				{
					report.Add(label + ": this move has no hit to change");
					continue;
				}
				string done = ApplyHitValue(scope, boxes, ed);
				report.Add(done == null ? label + " " + ed.Was + " -> " + ed.Text : label + ": " + done);
			}
		}
	}

	private static void RetimeAnimation(string scope, AnimationData ad, Mapper map)
	{
		int duration = ad.Duration;
		Record(scope, () => ad.Duration = duration);
		ad.Duration = map.NewDuration;
		int hold = ad.HitstunHold;
		if (hold >= 0)
		{
			Record(scope, () => ad.HitstunHold = hold);
			ad.HitstunHold = map.Map(hold);
		}
		foreach (AnimationSettings a in ad.Animations ?? Array.Empty<AnimationSettings>())
		{
			if (a == null)
			{
				continue;
			}
			int at = a.AtFrame;
			AnimationSettings aa = a;
			Record(scope, () => aa.AtFrame = at);
			a.AtFrame = map.Map(at);
		}
		foreach (HitboxState h in ad.Hitboxes ?? Array.Empty<HitboxState>())
		{
			if (h == null)
			{
				continue;
			}
			int at = h.AtFrame;
			HitboxState hh = h;
			Record(scope, () => hh.AtFrame = at);
			h.AtFrame = map.Map(at);
		}
	}

	private static IEnumerable<FrameDataEvent[]> EventLists(FighterState s)
	{
		yield return s.TransitionEvents;
		yield return s.OnEnterEvents;
		yield return s.OnTickEvents;
		yield return s.OnExitEvents;
		yield return s.OnHitConfirmEvents;
		yield return s.OnHitReactionEvents;
	}

	/// <summary>"At frame N" / "between frames A and B" / "at a random frame" checks of the state.</summary>
	private static void RetimeConditions(string scope, FighterState state, Mapper map)
	{
		foreach (FrameDataEvent[] list in EventLists(state))
		{
			foreach (FrameDataEvent ev in list ?? Array.Empty<FrameDataEvent>())
			{
				foreach (FrameDataCondition c in ev?.Conditions ?? Array.Empty<FrameDataCondition>())
				{
					switch (c)
					{
					case AtFrameCondition:
						if (GetInt(c, "Modulo") <= 0)   // "every N frames" checks keep their rhythm
						{
							SetInt(scope, c, "Frame", map.Map(GetInt(c, "Frame")));
						}
						break;
					case AtFrameRangeCondition:
						{
							int min = GetInt(c, "MinFrame");
							int max = GetInt(c, "MaxFrame");
							SetInt(scope, c, "MinFrame", map.Map(min));
							SetInt(scope, c, "MaxFrame", map.MapLast(min, max));
							break;
						}
					case AtRandomFrameCondition:
						{
							Vector2I r = GetVector(c, "Range");
							int x = map.Map(r.X);
							SetVector(scope, c, "Range", new Vector2I(x, Math.Max(x + 1, map.Map(r.Y))));
							break;
						}
					}
				}
			}
		}
	}

	/// <summary>"Go to frame N" actions: N is a frame of the state just played by the same event (or of the state the
	/// event belongs to), re-timed with that state.</summary>
	private static void RetimeGoToFrames(string scope, DataContainer data, Dictionary<int, Mapper> maps)
	{
		for (int i = 0; i < data.States.Length; i++)
		{
			FighterState state = data.States[i];
			if (state == null)
			{
				continue;
			}
			foreach (FrameDataEvent[] list in EventLists(state))
			{
				foreach (FrameDataEvent ev in list ?? Array.Empty<FrameDataEvent>())
				{
					int target = i;
					foreach (FrameDataAction a in ev?.Actions ?? Array.Empty<FrameDataAction>())
					{
						if (a is PlayStateAction)
						{
							target = PlayTarget(data, a);
						}
						else if (a is GoToFrameActions && target >= 0 && maps.TryGetValue(target, out Mapper map))
						{
							SetInt(scope, a, "Frame", map.Map(GetInt(a, "Frame")));
						}
					}
				}
			}
		}
	}

	private static int PlayTarget(DataContainer data, FrameDataAction play)
	{
		int index = GetInt(play, "StateIndex");
		if (index >= 0)
		{
			return index;
		}
		string name = GetString(play, "StateName");
		for (int i = 0; i < data.States.Length && !string.IsNullOrEmpty(name); i++)
		{
			if (data.States[i]?.StateName == name)
			{
				return i;
			}
		}
		return -1;
	}

	/// <summary>Cancel windows (from the move's own state) and "only within N frames" follow-up limits.</summary>
	private static void RetimeMoves(string scope, DataContainer data, Dictionary<int, Mapper> maps)
	{
		var seen = new HashSet<MoveSettings>();
		var seenCancels = new HashSet<MoveCancelSettings>();
		foreach (FighterStance stance in data.Stances ?? Array.Empty<FighterStance>())
		{
			foreach (MoveSettings move in stance?.Moves ?? Array.Empty<MoveSettings>())
			{
				if (move == null || !seen.Add(move))   // a move in two stances is still one move
				{
					continue;
				}
				if (maps.TryGetValue(move.MoveState, out Mapper map))
				{
					foreach (MoveCancelSettings c in move.CanCancelTo ?? Array.Empty<MoveCancelSettings>())
					{
						if (c == null || !seenCancels.Add(c))
						{
							continue;
						}
						Vector2I w = c.FrameThreshold;
						MoveCancelSettings cc = c;
						Record(scope, () => cc.FrameThreshold = w);
						int x = map.Map(w.X);
						c.FrameThreshold = new Vector2I(x, Math.Max(x, map.MapLast(w.X, w.Y)));
					}
				}
				if (move.FrameLimit > 0 && move.IsSequenceFromStates != null && move.IsSequenceFromStates.Length > 0
					&& maps.TryGetValue(move.IsSequenceFromStates[0], out Mapper from))
				{
					int limit = move.FrameLimit;
					MoveSettings mm = move;
					Record(scope, () => mm.FrameLimit = limit);
					move.FrameLimit = Math.Max(1, from.Map(limit));
				}
			}
		}
	}

	private static void ApplyMoveValue(string scope, DataContainer data, int state, Edit ed, string label, List<string> report)
	{
		if (!ed.IsNumber || ed.Number < 0)
		{
			report.Add(label + ": \"" + ed.Text + "\" isn't a number");
			return;
		}
		int count = 0;
		var seen = new HashSet<MoveSettings>();
		foreach (FighterStance stance in data.Stances ?? Array.Empty<FighterStance>())
		{
			foreach (MoveSettings move in stance?.Moves ?? Array.Empty<MoveSettings>())
			{
				if (move == null || move.MoveState != state || !seen.Add(move))
				{
					continue;
				}
				MoveSettings mm = move;
				if (ed.Column == "Cost")
				{
					int old = move.SuperGaugeRequired;
					Record(scope, () => mm.SuperGaugeRequired = old);
					move.SuperGaugeRequired = Round(ed.Number * MeterPerBar);
				}
				else
				{
					int old = move.NetsuPauseFrames;
					Record(scope, () => mm.NetsuPauseFrames = old);
					move.NetsuPauseFrames = Round(ed.Number);
				}
				count++;
			}
		}
		report.Add(count > 0 ? label + " " + ed.Was + " -> " + ed.Text : label + ": no move starts this state");
	}

	private static readonly string[] Guards = { "High", "Mid", "Low", "Unblockable" };

	/// <summary>The names the sheet uses for HitstunType (Knockdown / Air knockdown columns).</summary>
	public static string KnockdownName(HitstunType t)
	{
		switch (t)
		{
		case HitstunType.NONE: return "No stun";
		case HitstunType.BASIC: return "None";
		case HitstunType.KNOCKDOWN: return "Soft";
		case HitstunType.HARD_KNOCKDOWN: return "Hard";
		case HitstunType.DIZZINESS: return "Dizzy";
		case HitstunType.STAGGERED: return "Stagger";
		default: return "Grab";
		}
	}

	private static bool ParseKnockdown(string text, out HitstunType type)
	{
		string s = text.Trim();
		foreach (HitstunType k in Enum.GetValues(typeof(HitstunType)))
		{
			if (string.Equals(KnockdownName(k), s, StringComparison.OrdinalIgnoreCase))
			{
				type = k;
				return true;
			}
		}
		s = s.ToLowerInvariant();
		if (s.StartsWith("hard") || s == "hkd")
		{
			type = HitstunType.HARD_KNOCKDOWN;
			return true;
		}
		if (s.StartsWith("soft") || s == "knockdown" || s == "kd" || s == "skd")
		{
			type = HitstunType.KNOCKDOWN;
			return true;
		}
		if (s == "no" || s == "-" || s == "no knockdown")
		{
			type = HitstunType.BASIC;
			return true;
		}
		type = HitstunType.BASIC;
		return false;
	}

	/// <summary>Passes a hit value change to every box. Returns null when done, else why it couldn't be.</summary>
	private static string ApplyHitValue(string scope, List<HitboxElement> boxes, Edit ed)
	{
		HitboxElement first = boxes[0];
		switch (ed.Column)
		{
		case "Guard":
			{
				int g = Array.FindIndex(Guards, x => string.Equals(x, ed.Text.Trim(), StringComparison.OrdinalIgnoreCase));
				if (g < 0 && ed.Text.Trim().ToLowerInvariant().StartsWith("over"))
				{
					g = 0;
				}
				if (g < 0)
				{
					return "\"" + ed.Text + "\" isn't High, Mid, Low or Unblockable";
				}
				foreach (HitboxElement b in boxes)
				{
					HitType old = b.HitType;
					HitboxElement bb = b;
					Record(scope, () => bb.HitType = old);
					b.HitType = (HitType)g;
				}
				return null;
			}
		case "Knockdown":
		case "Air knockdown":
			{
				if (!ParseKnockdown(ed.Text, out HitstunType type))
				{
					return "\"" + ed.Text + "\" isn't None, Soft or Hard";
				}
				bool air = ed.Column == "Air knockdown";
				foreach (HitboxElement b in boxes)
				{
					HitboxElement bb = b;
					if (air)
					{
						HitstunType old = b.AirHitstunType;
						Record(scope, () => bb.AirHitstunType = old);
						b.AirHitstunType = type;
					}
					else
					{
						HitstunType old = b.GroundHitstunType;
						Record(scope, () => bb.GroundHitstunType = old);
						b.GroundHitstunType = type;
					}
				}
				return null;
			}
		}
		if (!ed.IsNumber)
		{
			return "\"" + ed.Text + "\" isn't a number";
		}
		double v = ed.Number;
		switch (ed.Column)
		{
		case "Damage":
			Scale(scope, boxes, b => b.BaseDamage, (b, x) => b.BaseDamage = x, first.BaseDamage, v, 0);
			return null;
		case "Chip":
			Scale(scope, boxes, b => b.ChipDamage, (b, x) => b.ChipDamage = x, first.ChipDamage, v, 0);
			return null;
		case "Meter":
			Scale(scope, boxes, b => b.SelfSuperGaugeGain, (b, x) => b.SelfSuperGaugeGain = x, first.SelfSuperGaugeGain, v, 0);
			return null;
		case "Push (hit)":   // the sheet shows how far AWAY: the engine's X is negative for that
			Scale(scope, boxes, b => -b.GroundHitKnockback.X, (b, x) => b.GroundHitKnockback = new Vector2I(-x, b.GroundHitKnockback.Y),
				-first.GroundHitKnockback.X, v, int.MinValue);
			return null;
		case "Push (block)":
			Scale(scope, boxes, b => -b.GroundBlockKnockback.X, (b, x) => b.GroundBlockKnockback = new Vector2I(-x, b.GroundBlockKnockback.Y),
				-first.GroundBlockKnockback.X, v, int.MinValue);
			return null;
		case "Launch":
			Scale(scope, boxes, b => b.GroundHitKnockback.Y, (b, x) => b.GroundHitKnockback = new Vector2I(b.GroundHitKnockback.X, x),
				first.GroundHitKnockback.Y, v, int.MinValue);
			return null;
		case "Air launch":
			Scale(scope, boxes, b => b.AirHitKnockback.Y, (b, x) => b.AirHitKnockback = new Vector2I(b.AirHitKnockback.X, x),
				first.AirHitKnockback.Y, v, int.MinValue);
			return null;
		case "Hitstun":
			Shift(scope, boxes, b => b.GroundHitstun, (b, x) => b.GroundHitstun = x, first.GroundHitstun, v, 0);
			return null;
		case "Air hitstun":
			Shift(scope, boxes, b => b.AirHitstun, (b, x) => b.AirHitstun = x, first.AirHitstun, v, 0);
			return null;
		case "Blockstun":
			{
				int delta = Round(v) - first.GroundBlockstun;
				Shift(scope, boxes, b => b.GroundBlockstun, (b, x) => b.GroundBlockstun = x, first.GroundBlockstun, v, 0);
				Shift(scope, boxes, b => b.AirBlockstun, (b, x) => b.AirBlockstun = x, first.AirBlockstun, first.AirBlockstun + delta, 0);
				return null;
			}
		case "Hitstop":
			{
				int delta = Round(v) - first.SelfHitStopDuration;
				Shift(scope, boxes, b => b.SelfHitStopDuration, (b, x) => b.SelfHitStopDuration = x, first.SelfHitStopDuration, v, 0);
				Shift(scope, boxes, b => b.OpponentHitStopDuration, (b, x) => b.OpponentHitStopDuration = x, first.OpponentHitStopDuration,
					first.OpponentHitStopDuration + delta, 0);
				Shift(scope, boxes, b => b.BlockStopDuration, (b, x) => b.BlockStopDuration = x, first.BlockStopDuration,
					first.BlockStopDuration + delta, 0);
				return null;
			}
		case "Scaling":
			Shift(scope, boxes, b => b.DamageScalingSubtract, (b, x) => b.DamageScalingSubtract = x, first.DamageScalingSubtract, v, 0);
			return null;
		}
		return "this column can't be changed";
	}

	/// <summary>Every box by the same percentage as the first one goes from `shown` to `wanted` (all set to it when the
	/// first one is 0).</summary>
	private static void Scale(string scope, List<HitboxElement> boxes, Func<HitboxElement, int> get, Action<HitboxElement, int> set,
		int shown, double wanted, int min)
	{
		foreach (HitboxElement b in boxes)
		{
			int old = get(b);
			HitboxElement bb = b;
			Record(scope, () => set(bb, old));
			int x = shown == 0 ? Round(wanted) : Round(old * wanted / shown);
			set(b, Math.Max(min, x));
		}
	}

	/// <summary>Every box by the same number as the first one goes from `shown` to `wanted`.</summary>
	private static void Shift(string scope, List<HitboxElement> boxes, Func<HitboxElement, int> get, Action<HitboxElement, int> set,
		int shown, double wanted, int min)
	{
		int delta = Round(wanted) - shown;
		foreach (HitboxElement b in boxes)
		{
			int old = get(b);
			HitboxElement bb = b;
			Record(scope, () => set(bb, old));
			set(b, Math.Max(min, old + delta));
		}
	}

	// --- What the sheets show (tools/frame_data/make_sheets.py) ---------------------------------------------------

	/// <summary>Everything the frame data sheet shows for this fighter's (or assist's) data, as JSON: the values the
	/// game really uses, worked out the same way the sheet's changes are applied. tools/frame_data/make_sheets.py builds
	/// the spreadsheets from it (through the container's test runner, _rt/RtFrameDump.cs).</summary>
	public static string Describe(DataContainer data, int pauseEx = 30, int pauseSuper = 60)
	{
		var root = new Dictionary<string, object>
		{
			["path"] = data.ResourcePath,
			["health"] = data.MaxHealth,
			["attack"] = (int)data.BaseAttack,
			["defense"] = (int)data.BaseDefense,
		};
		var moves = new Dictionary<int, List<Dictionary<string, object>>>();
		var seen = new HashSet<MoveSettings>();
		foreach (FighterStance stance in data.Stances ?? Array.Empty<FighterStance>())
		{
			foreach (MoveSettings m in stance?.Moves ?? Array.Empty<MoveSettings>())
			{
				if (m == null || !seen.Add(m))
				{
					continue;
				}
				if (!moves.TryGetValue(m.MoveState, out List<Dictionary<string, object>> list))
				{
					moves[m.MoveState] = list = new List<Dictionary<string, object>>();
				}
				int pause = m.NetsuPauseFrames >= 0 ? m.NetsuPauseFrames
					: (m.SuperGaugeRequired >= 6000 ? pauseSuper : (m.SuperGaugeRequired >= 4000 ? pauseEx : 0));
				list.Add(new Dictionary<string, object>
				{
					["name"] = m.MoveName ?? "",
					["path"] = m.ResourcePath ?? "",
					["cost"] = m.SuperGaugeRequired,
					["pause"] = pause,
					["ground"] = m.UseOnGround,
					["air"] = m.UseOnAir,
					["from"] = m.IsSequenceFromStates ?? Array.Empty<int>(),
				});
			}
		}
		var states = new List<object>();
		for (int i = 0; i < (data.States?.Length ?? 0); i++)
		{
			FighterState s = data.States[i];
			if (s == null)
			{
				continue;
			}
			AnimationData ad = s.AnimationData;
			Timing t = TimingOf(ad);
			var row = new Dictionary<string, object>
			{
				["index"] = i,
				["name"] = s.StateName ?? "",
				["type"] = (int)s.Type,
				["path"] = s.ResourcePath ?? "",
				["animation"] = ad?.ResourcePath ?? "",
				["attack"] = t.HasAttack,
				["first"] = t.First,
				["last"] = t.Last,
				["duration"] = t.Duration,
			};
			bool landing = false;
			int resets = 0;
			var targets = new List<int>();
			foreach (FrameDataEvent[] list in EventLists(s))
			{
				foreach (FrameDataEvent ev in list ?? Array.Empty<FrameDataEvent>())
				{
					if (list == s.TransitionEvents)
					{
						foreach (FrameDataCondition c in ev?.Conditions ?? Array.Empty<FrameDataCondition>())
						{
							if (c is OnGroundCondition && !GetBool(c, "Not"))
							{
								landing = true;
							}
						}
					}
					foreach (FrameDataAction a in ev?.Actions ?? Array.Empty<FrameDataAction>())
					{
						if (a is ResetHitAction)
						{
							resets++;
						}
						else if (a is PlayStateAction)
						{
							int target = PlayTarget(data, a);
							if (target >= 0 && !targets.Contains(target))
							{
								targets.Add(target);
							}
						}
					}
				}
			}
			row["landing"] = landing;
			row["targets"] = targets;
			int windows = 0;
			bool inWindow = false;
			foreach (HitboxState key in ad?.Hitboxes ?? Array.Empty<HitboxState>())
			{
				bool attack = key != null && key.AtFrame < t.Duration && HasAttack(key.HitboxData);
				if (attack && !inWindow)
				{
					windows++;
				}
				inWindow = attack;
			}
			row["hits"] = Math.Max(windows, t.HasAttack ? Math.Min(resets + 1, 99) : 0);
			List<HitboxElement> boxes = AttackBoxes(ad);
			if (boxes.Count > 0)
			{
				HitboxElement b = boxes[0];
				row["box"] = b.HitboxType.ToString();
				row["damage"] = b.BaseDamage;
				row["chip"] = b.ChipDamage;
				row["guard"] = Guards[Math.Clamp((int)b.HitType, 0, Guards.Length - 1)];
				row["hitstun"] = b.GroundHitstun;
				row["air_hitstun"] = b.AirHitstun;
				row["blockstun"] = b.GroundBlockstun;
				row["hitstop"] = b.SelfHitStopDuration;
				row["knockdown"] = KnockdownName(b.GroundHitstunType);
				row["air_knockdown"] = KnockdownName(b.AirHitstunType);
				row["push_hit"] = -b.GroundHitKnockback.X;
				row["push_block"] = -b.GroundBlockKnockback.X;
				row["launch"] = b.GroundHitKnockback.Y;
				row["air_launch"] = b.AirHitKnockback.Y;
				row["meter"] = b.SelfSuperGaugeGain;
				row["scaling"] = b.DamageScalingSubtract;
				row["boxes"] = boxes.Count;
			}
			if (moves.TryGetValue(i, out List<Dictionary<string, object>> ms))
			{
				row["moves"] = ms;
			}
			states.Add(row);
		}
		root["states"] = states;
		return JsonSerializer.Serialize(root, new JsonSerializerOptions { WriteIndented = true });
	}

	private static bool GetBool(object o, string name)
	{
		FieldInfo f = Field(o, name);
		return f != null && f.FieldType == typeof(bool) && (bool)f.GetValue(o);
	}

	// --- Private fields of the engine's conditions / actions (Frame, MinFrame...) ---------------------------------------

	private static readonly Dictionary<(Type, string), FieldInfo> _fields = new Dictionary<(Type, string), FieldInfo>();

	private static FieldInfo Field(object o, string name)
	{
		Type t = o.GetType();
		if (!_fields.TryGetValue((t, name), out FieldInfo f))
		{
			for (Type k = t; k != null && f == null; k = k.BaseType)
			{
				f = k.GetField(name, BindingFlags.Instance | BindingFlags.NonPublic | BindingFlags.Public);
			}
			_fields[(t, name)] = f;
		}
		return f;
	}

	private static int GetInt(object o, string name)
	{
		FieldInfo f = Field(o, name);
		return f != null && f.FieldType == typeof(int) ? (int)f.GetValue(o) : 0;
	}

	private static string GetString(object o, string name)
	{
		FieldInfo f = Field(o, name);
		return f != null && f.FieldType == typeof(string) ? (string)f.GetValue(o) : "";
	}

	private static void SetInt(string scope, object o, string name, int value)
	{
		FieldInfo f = Field(o, name);
		if (f == null || f.FieldType != typeof(int))
		{
			return;
		}
		int old = (int)f.GetValue(o);
		if (old == value)
		{
			return;
		}
		Record(scope, () => f.SetValue(o, old));
		f.SetValue(o, value);
	}

	private static Vector2I GetVector(object o, string name)
	{
		FieldInfo f = Field(o, name);
		return f != null && f.FieldType == typeof(Vector2I) ? (Vector2I)f.GetValue(o) : Vector2I.Zero;
	}

	private static void SetVector(string scope, object o, string name, Vector2I value)
	{
		FieldInfo f = Field(o, name);
		if (f == null || f.FieldType != typeof(Vector2I))
		{
			return;
		}
		Vector2I old = (Vector2I)f.GetValue(o);
		if (old == value)
		{
			return;
		}
		Record(scope, () => f.SetValue(o, old));
		f.SetValue(o, value);
	}
}
