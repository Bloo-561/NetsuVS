# Handoff: Oct 24 2026, late (throws, sounds, input leniency, CPU)

**Build first:** C# changed (engine). Open the project in Godot, press **Build** (top right), then play. Godot also
imports the 63 new sounds when it opens.

| # | Asked | Done | Where |
| --- | --- | --- | --- |
| 1 | Throws and throw breaks on B+C (unless something is on it) | B+C alone was free (supers are B+C *with a motion*, 2+B+C stays 2C). **B+C** close = throw, **4+B+C** = back throw (puts them behind you, into the corner), **B+C while grabbed** (12-frame window) = throw break, both pushed apart. Can't throw someone in block / hit stun or 5 frames after. Kara throws (5B then B+C) work. Damage 1100 (Flan 350 + 750), knockdown. No throw drawings yet: the poses are borrowed from each fighter's other animations | `docs/game_systems.md` → Throws; made by `tools/sprite_port/throws.py` |
| 2 | Add sounds (you'll add your own later) | 63 placeholder sounds (synthesized, nothing downloaded) on every normal, special, super, throw, throw break and assist move. Save your own .wav over one with the same name and it's used at once. Also: fight sounds now follow the SFX volume (they were on Master), and an online rollback no longer plays them twice | `docs/sounds.md`; cues `tools/sprite_port/sounds.py`; placeholders `tools/fx/make_fight_sfx.py` |
| 3 | Input leniency | Two buttons up to 2 frames apart count as together; motions forgive extra / held / late directions (2369+B = 236B, crouch then 36+B = 236B, the button up to 6 frames late); kara cancels into throws / supers; a move pressed in the last 4 frames of block / hit stun comes out on the first free frame; up+down = up | `docs/game_systems.md` → Input leniency |
| 4 | Better CPUs | New brain: guards what it sees coming (assists, beams, jump-ins, rushing supers) after a reaction time per level, the right height and direction; anti-airs timed from your jump (each anti-air with its own timing); punishes recoveries; breaks throws and throws you; drops a dash-in or a throw when it sees you jump; holds guard sometimes; presses cancels / rekka follow-ups on time; wake-up reversals; assist use per level. Its own dice (its combos used to drop at the same link every time). Every fighter's plans checked to connect, combos fixed (Flan's ended in a move too slow to combo, Leticia's follow-ups whiffed) | `docs/cpu_ai.md`; `tools/ai/` |

Also fixed on the way: the VS screen's background loading sometimes failed ("Parse Error" in a random fighter
file) and the fight then never started; it now loads one file at a time (`game/autoloads/match_setup.gd`).

## Testing checklist
1. **Build.** Training: B+C next to the dummy (throw), 4+B+C (back throw), whiff one (it's slow). Dummy → CPU, then
   throw it: it breaks some (B+C) depending on its level. Record the dummy doing B+C to practise breaks.
2. Leniency: 236 + B with a sloppy motion (2369, or crouch first), B and C a frame apart for a throw / super.
3. Sounds: every move; Options → Sound → SFX changes their volume. Replace one placeholder with your own .wav.
4. CPU: Versus vs CPU at Normal, then Hard / Pro: jump in (it anti-airs or guards high), Leticia's beam from far
   (Hard+ guards it), throw it (it breaks some), whiff a big move near it (it punishes).

## Tests run here (a copy of the project, scripted player vs CPU)
Each test repeats one thing against the CPU (16 or 12 times), from the training start positions. "Old" = the CPU
before this batch.

| Test | Level | Old CPU | New CPU |
| --- | --- | --- | --- |
| Cecilia jumps in at Cecilia (late j.B, 16×) | Normal | hit 6, anti-air 1, hit you on landing 6 | hit 5, guarded 5, anti-air 5, hit you on landing 1 |
| | Hard | hit 0, anti-air 8, hit you on landing 4 | hit 2, guarded 3, anti-air 7 |
| | Pro | hit 1, anti-air 12 | hit 2, guarded 2, anti-air 9 |
| Flan jumps in at Leticia (16×) | Normal | hit 0, anti-air 6, hit you on landing 7 | hit 2, guarded 5, anti-air 5 |
| | Hard | hit 1, anti-air 10, hit you on landing 3 | hit 0, anti-air 6, hit you on landing 6 |
| | Pro | hit 0, anti-air 16 | hit 0, guarded 2, anti-air 11 |
| Leticia jumps in at Flan (16×) | Normal | | hit 0, guarded 2, anti-air 7, hit you on landing 4 |
| | Hard | | hit 0, guarded 8, anti-air 4 |
| | Pro | | hit 0, guarded 3, anti-air 11 |
| Leticia's Photon Line beam from full screen at Cecilia (12×) | Normal | hit 8, guarded 0 | hit 9, guarded 0 |
| | Hard | hit 8, guarded 1 | hit 6, guarded 5 |
| | Pro | hit 4, guarded 2 | hit 0, guarded 5 (and hit you first 3 times) |
| Cecilia walks up and throws Flan (12×) | Normal | thrown 11 | thrown 2, broke 1, hit you first 6 |
| | Hard | thrown 1, hit you first 11 | thrown 3, broke 1, hit you first 3 |
| | Pro | thrown 4, hit you first 6 | thrown 0, broke 8, hit you first 2 |
| Cecilia whiffs 5C near Cecilia (14×) | Normal / Hard / Pro | | punished 1 / 2 / 6 |

- The old CPU's "anti-airs" at Hard and Pro were mostly its own jumps meeting yours (it jumped all the time) and
  EX moves; it never guarded a jump-in or the beam, and never broke a throw (it had no throw).
- The new CPU's hits at Hard / Pro in the Cecilia test: it went for a dash throw just as you jumped (a throw loses
  to a jump, for a player too); if it sees the jump first it drops the throw.
- Normal can't react to the beam (12 frames of start-up, Normal reacts in 15): only Hard and up guard it on sight.
- CPU vs CPU (2 rounds of 60 s): Cecilia Hard beat Cecilia Normal 4 rounds to 0, Flan Normal beat Leticia Normal
  4-1, Cecilia Pro beat Flan Normal 2-0, Leticia Hard beat Cecilia Normal 2-1. Every plan of every fighter was also
  run against a standing opponent: all combos connect.

## Backups
Everything this batch replaced on the PC: `_backup_stage_select/pre_oct24_late/` (same folders as in the project,
files as `.bak`; `push_manifest.tsv` lists every file with its checksum before and after).

## Notes / next
- Throws on wake-up: the get-up animation is a free state, so a fighter can be thrown in its last frames (5 frames of
  throw protection after the knockdown). Most games give a few frames more: easy to change
  (`SakugaActor.NetsuThrowProtectFrames`) if it feels cheap.
- Placeholders are placeholders: no voices yet (`docs/sounds.md` → Voice lines). Mary's moves got sounds too (cues
  only, nothing else of hers changed): `python tools/sprite_port/sounds.py --remove mary` takes them out.
- The CPU's plans are per fighter in `tools/ai/build_*_ai.py`; the six levels for everyone in `tools/ai/ai_common.py`.

## Afterwards (Oct 24, 21:00): 5-digit lobby codes
Online lobby codes are now 5 digits (`48213`) instead of 12 letters. A number can't hold an internet address, so the
host posts its address under the number on ntfy.sh (a free public message board, no account) and the joiner looks it
up; the joiner posts its own address back, so both computers call each other by themselves (the old "reply code"
step is gone unless the board can't be reached). The long code is still there as a backup (S on the host's screen),
and the host's screen shows it straight away if the board is down. **Needs a Build** (`NetsuOnline.cs`). Details,
privacy note and tests: `docs/online.md`. Files replaced: `_backup_stage_select/pre_lobby_codes/`.
