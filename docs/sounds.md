# Fight sounds (Oct 24 2026, night)

Every attack, special, super, throw, throw break and assist move now makes a sound. They are **placeholders**,
synthesized by script (nothing recorded or downloaded): swap in your own whenever you like.

## Using your own sound
1. Find the placeholder (list below). Save your sound over it **as a .wav with the same name**.
2. Go back to Godot: it re-imports the file and the game uses it at once. Nothing else to change.

Your file in another format (.ogg, .mp3) or with another name: change that sound's path in the `SOUNDS` table at
the top of `tools/sprite_port/sounds.py` and run `python tools/sprite_port/sounds.py` (it adds the new file to the
sound list and points the moves at it).

| Folder | Sounds |
| --- | --- |
| `assets/audio/sfx/fight/` | `throw_reach` (the throw's grab), `throw_grab` (it connects), `throw_break` (both hands slap apart) |
| `actors/cecilia/Sounds/` | `slash_light / medium / heavy` (A / B / C normals), `lightning_dash` (214), `lightning_slash` (its slashes, EX slashes), `dash_rush` (236 rush), `teleport` (623, S1), `counter_stance` (S1 stance), `thunderclap` (S1 finish, EX rush finish), `thunder_barrage` (S2), `plunge_dive`, `thunder_impact` (S2 landing) |
| `actors/flan/Sounds/` | `punch_light / medium / heavy`, `star_fist` (236A/B), `supernova` (236C), `armor_glint` (236B armour), `rising_star` (623, S2 jump), `star_burst` (623C finish), `meteor_rise` / `meteor_fall` / `meteor_impact` / `meteor_impact_big` (214), `radiant_rush` / `radiant_burst` (S1), `explosion_big` (S2) |
| `actors/leticia/Sounds/` | `swing_light / medium / heavy`, `gunshot`, `gunshot_double` (5C, j.B, 2B, 2C, Crossfire), `comet_kick` (623), `photon_beam` (214A), `ricochet` (214B), `prism_beam` (214C), `board_flip` / `board_spin` (Flux Dive / Storm), `stardrive_charge` / `stardrive_beam` (S1), `crimson_rush`, `flame_trap`, `flame_shot`, `flame_explosion` (S2) |
| `actors/assists/mary/Sounds/` | `encore` (5S violin, peaks with her buff), `fermata` (6S), `note_chime` (the note appears), `note_burst` (it explodes) |
| `actors/assists/adin/Sounds/` | `shield_raise`, `shield_block` (an attack hits the shield), `shield_bash`, `rush_run` (6S) |
| `actors/assists/eren/Sounds/` | `slash`, `dash`, `jump`, `spin` |
| `actors/assists/harie/Sounds/` | `dive`, `burst` (the uppercut out of the puddle), `wave` (6S), `wave_launch` |

Hit, block and clash sounds were already there (the hit effects play them: `actors/_shared/sakuga/SFX/*HitFINAL.wav`),
as were the movement sounds (footsteps, jumps, dashes, landing) and the EX / super flash sounds.

## Which move plays which sound, when
`tools/sprite_port/sounds.py` → `CUES`: for each state file, `(frame, sound)` pairs. A swing starts 2 frames before
its first active frame (it peaks as the hit comes out), a shot 1 frame before. Change a frame or a sound there and run
`python tools/sprite_port/sounds.py` (`--check` lists what would change, `--remove` takes every cue out again,
`cecilia` / `flan` / ... does one actor).

Each cue is a normal frame event in the state (`OnTickEvents`: AtFrame → PlaySoundAction; frame 0 goes into
`OnEnterEvents`, so it also plays when a hit or a throw puts the fighter into that state), so you can see and edit them
in Godot like any other event. The script's events have sub-resource ids starting with `sfx_`: running it again
replaces them, never doubles them, and leaves other sound events (the engine's, yours) alone. The moves scripts
(`moves_*.py`, `assists.py`, `throws.py`) put the cues back in whenever they rewrite a state (`fdk.write`).

**Index** = the sound's place in `actors/_shared/sakuga/Shared_SFXList.tres`, the list every fighter and assist uses.
New sounds go at its end, so the numbers already in use never move.

**Players**: a fighter has five (`SFX_0`..`SFX_4` in its scene). 0 and 1 are the engine's movement sounds; the cues use
2 for swings and shots, 3 for effects (lightning, sparkles, beams, teleports) and 4 for the big ones (thunder,
explosions, throws). A new sound on a player stops the one it was playing, which is why things that must overlap go on
different players. Assists have one player.

## Making the placeholders again
`python tools/fx/make_fight_sfx.py` (needs `pip install numpy scipy`; `--list` shows them, `cecilia` / `mary` / ...
does one group). It **skips any file it didn't make** (it remembers what it wrote in `tools/fx/fight_sfx_written.json`),
so your own sounds are safe unless you add `--force`. The recipes (noise, filters, oscillators) are in the same file.

## Engine changes (need a Build)
- **The SFX volume works on fight sounds**: fighter, assist and hit-effect sounds went to the Master bus, so only the
  master volume changed them. `SoundQueue._Ready` puts them on the SFX bus (Options → Sound → SFX).
- **Online**: a rollback replays the last few frames, and every sound started in them used to start again (heard
  twice or cut and restarted). `SoundQueue` remembers the last sounds it started with their game frame and doesn't
  start the same one again for the same frame. Offline nothing changes.

## Voice lines (not made)
The engine plays voices the same way (`PlaySoundAction` with **Sound Type = Voice**, the list
`actors/_shared/sakuga/Shared_VoiceLines.tres`). Add your lines to that list, then add a PlaySoundAction event to the
move's state in Godot (pick a player that isn't busy at that moment, e.g. 4, or ask for a sixth player).
