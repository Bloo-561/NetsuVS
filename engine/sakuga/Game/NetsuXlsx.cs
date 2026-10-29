#nullable disable
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.IO.Compression;
using System.Xml.Linq;

namespace SakugaEngine.Game;

/// <summary>
/// Netsu (Oct 25 2026): reads the cells of an Excel workbook (.xlsx) - enough for the frame data spreadsheets in
/// data/frame_data (NetsuFrameData). An .xlsx file is a zip of XML files: the workbook lists the sheets, each sheet
/// lists its cells, and text cells point into one shared list of strings. Works with files saved by Excel, Google
/// Sheets ("Download as .xlsx") and LibreOffice. Formulas are not worked out: a formula cell reads as the value the
/// program saved with it (or empty).
/// </summary>
public static class NetsuXlsx
{
	private static readonly XNamespace Main = "http://schemas.openxmlformats.org/spreadsheetml/2006/main";
	private static readonly XNamespace Rel = "http://schemas.openxmlformats.org/officeDocument/2006/relationships";
	private static readonly XNamespace PackageRel = "http://schemas.openxmlformats.org/package/2006/relationships";

	/// <summary>Sheet name -> its rows (from the top, empty rows kept), each row its cells as text (from column A,
	/// "" where empty). Throws if the bytes aren't an .xlsx workbook.</summary>
	public static Dictionary<string, List<List<string>>> Read(byte[] bytes)
	{
		var sheets = new Dictionary<string, List<List<string>>>();
		using var stream = new MemoryStream(bytes);
		using var zip = new ZipArchive(stream, ZipArchiveMode.Read);
		List<string> shared = ReadSharedStrings(zip);
		XDocument workbook = Load(zip, "xl/workbook.xml");
		XDocument rels = Load(zip, "xl/_rels/workbook.xml.rels");
		if (workbook == null)
		{
			throw new InvalidDataException("not an .xlsx workbook (no xl/workbook.xml)");
		}
		var targets = new Dictionary<string, string>();
		if (rels != null)
		{
			foreach (XElement r in rels.Root.Elements(PackageRel + "Relationship"))
			{
				string id = (string)r.Attribute("Id");
				string target = (string)r.Attribute("Target");
				if (id != null && target != null)
				{
					targets[id] = target;
				}
			}
		}
		XElement sheetList = workbook.Root.Element(Main + "sheets");
		if (sheetList == null)
		{
			return sheets;
		}
		int n = 0;
		foreach (XElement s in sheetList.Elements(Main + "sheet"))
		{
			n++;
			string name = (string)s.Attribute("name") ?? ("Sheet" + n);
			string rid = (string)s.Attribute(Rel + "id");
			string path = rid != null && targets.TryGetValue(rid, out string t) ? t : "worksheets/sheet" + n + ".xml";
			path = path.StartsWith("/") ? path.Substring(1) : "xl/" + path;
			XDocument sheet = Load(zip, path);
			if (sheet != null)
			{
				sheets[name] = ReadSheet(sheet, shared);
			}
		}
		return sheets;
	}

	private static XDocument Load(ZipArchive zip, string path)
	{
		ZipArchiveEntry entry = zip.GetEntry(path);
		if (entry == null)
		{
			// some programs write paths with other cases or backslashes
			foreach (ZipArchiveEntry e in zip.Entries)
			{
				if (string.Equals(e.FullName.Replace('\\', '/'), path, StringComparison.OrdinalIgnoreCase))
				{
					entry = e;
					break;
				}
			}
		}
		if (entry == null)
		{
			return null;
		}
		using Stream s = entry.Open();
		return XDocument.Load(s);
	}

	private static List<string> ReadSharedStrings(ZipArchive zip)
	{
		var list = new List<string>();
		XDocument doc = Load(zip, "xl/sharedStrings.xml");
		if (doc == null)
		{
			return list;
		}
		foreach (XElement si in doc.Root.Elements(Main + "si"))
		{
			list.Add(TextOf(si));
		}
		return list;
	}

	/// <summary>The text of a string item: a plain &lt;t&gt;, or rich text runs (&lt;r&gt;&lt;t&gt;) joined.</summary>
	private static string TextOf(XElement item)
	{
		XElement t = item.Element(Main + "t");
		if (t != null)
		{
			return t.Value;
		}
		var sb = new System.Text.StringBuilder();
		foreach (XElement r in item.Elements(Main + "r"))
		{
			XElement rt = r.Element(Main + "t");
			if (rt != null)
			{
				sb.Append(rt.Value);
			}
		}
		return sb.ToString();
	}

	private static List<List<string>> ReadSheet(XDocument sheet, List<string> shared)
	{
		var rows = new List<List<string>>();
		XElement data = sheet.Root.Element(Main + "sheetData");
		if (data == null)
		{
			return rows;
		}
		int nextRow = 1;
		foreach (XElement row in data.Elements(Main + "row"))
		{
			int r = int.TryParse((string)row.Attribute("r"), out int rr) ? rr : nextRow;
			while (rows.Count < r - 1)
			{
				rows.Add(new List<string>());
			}
			var cells = new List<string>();
			int nextCol = 0;
			foreach (XElement c in row.Elements(Main + "c"))
			{
				string reference = (string)c.Attribute("r");
				int col = reference != null ? ColumnIndex(reference) : nextCol;
				while (cells.Count < col)
				{
					cells.Add("");
				}
				cells.Add(CellText(c, shared));
				nextCol = col + 1;
			}
			rows.Add(cells);
			nextRow = r + 1;
		}
		return rows;
	}

	private static string CellText(XElement c, List<string> shared)
	{
		string type = (string)c.Attribute("t") ?? "n";
		XElement v = c.Element(Main + "v");
		switch (type)
		{
		case "s":
			return v != null && int.TryParse(v.Value, NumberStyles.Integer, CultureInfo.InvariantCulture, out int i) && i >= 0 && i < shared.Count ? shared[i] : "";
		case "inlineStr":
			XElement inline = c.Element(Main + "is");
			return inline != null ? TextOf(inline) : "";
		case "b":
			return v != null && v.Value == "1" ? "TRUE" : "FALSE";
		default:   // "n" numbers, "str" formula text, "e" errors, "d" dates
			return v != null ? v.Value : "";
		}
	}

	/// <summary>"A1" -> 0, "B7" -> 1, "AA3" -> 26.</summary>
	public static int ColumnIndex(string reference)
	{
		int col = 0;
		foreach (char ch in reference)
		{
			char u = char.ToUpperInvariant(ch);
			if (u < 'A' || u > 'Z')
			{
				break;
			}
			col = col * 26 + (u - 'A' + 1);
		}
		return Math.Max(0, col - 1);
	}
}
