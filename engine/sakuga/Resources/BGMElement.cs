using Godot;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class BGMElement : Resource
{
	[Export(PropertyHint.None, "")]
	public string SongName;

	[Export(PropertyHint.None, "")]
	public AudioStream clip;

	/// <summary>Composer / artist, shown on the stage select and in the credits.</summary>
	[Export(PropertyHint.None, "")]
	public string Artist = "";

	/// <summary>Where the song comes from (site, album, URL), shown in the credits.</summary>
	[Export(PropertyHint.None, "")]
	public string Source = "";

	/// <summary>Fighter this song is a theme for (their ShortName, e.g. "Cecilia"). Empty = not a character theme.</summary>
	[Export(PropertyHint.None, "")]
	public string Character = "";

	/// <summary>Seconds to jump back to when the song loops (OGG / MP3 only; WAV loops come from the import settings).</summary>
	[Export(PropertyHint.None, "")]
	public float LoopStart = 0f;
}
