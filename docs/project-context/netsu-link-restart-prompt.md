I'm making NetsuVS, a 2D anime fighting game (Godot 4.7, C#/GDScript, rollback netcode), based on my D&D campaign "Netsu no Kiseki" (inspired by Trails of Cold Steel). Project folder on my PC: E:\Netsu Projects\Netsu Fighter\Godot\netsu-vs. The project docs (claude/assists.md, claude/handoff-*.md) describe the systems in detail. Read them only when you need specifics.

## What I want
A signature mechanic, working name **Netsu Link**, that makes NetsuVS feel like no other fighting game. The fighter and their partners should feel like a **party fighting together**, the way a Cold Steel party or a D&D table does, not a fighter with a backup button. I want a new **structure or dynamic** to the match, not just "assists, but stronger".

## Hard constraints
- **1v1 control.** I always play one fighter. I never switch characters. It must not feel like a normal tag game.
- **I want 2 partners per fighter.** That means more campaign characters, and trio moments (e.g. Juel, Doris and Rumi get a literature club intro).
- **Some partners don't fight.** Doris is a bookworm: all she can do is point out a weakness for others to hit. Mary plays the violin (a buff). The system has to make non-fighters just as valuable as fighters.
- **Keep it simple.** I've said several times that ideas got overcomplicated. Aim for 3 rules or fewer, readable on screen, and buildable by a small team.
- It has to stay balanced and fit rollback.

## The game today (short)
- 4 fighters: Cecilia (sword), Flan (fists), Leticia (guns), Noah (void magic).
- 4 partners, one per player, called with S (5S / 6S), with cooldowns:
  - Mary: violin buff, plus a note projectile;
  - Adin: shield counter, plus a rush;
  - Eren: sword slashes;
  - Harie: a puddle trap, plus a wave.
- Assist Cancel costs 1 bar.
- Craft Gauge: 4 bars (3 outside Overdrive). EX 1 bar, S-Craft 3 bars.
- Automatic Overdrive at ≤30% HP, once per round.
- Burst (A+C), Pushblock, 6C universal launcher.

## Already tried, and why it didn't land
- **Link Gauge** (levels 1–3 filled by "teamwork hits"; Level 2 = shorter cooldown; Level 3 = team super). It felt like bookkeeping: the rewards were invisible and far away. It's built in code (Nov 7) but not compiled. Handoff: claude/handoff-2026-11-07-link-gauge.md.
- **Link Chase** (6C hits, then S: the partner sets the opponent up, then you dash after them; from Marvel Tōkon's Assemble Rush). It's built for Eren only and not compiled. Handoff: claude/handoff-2026-11-07-link-chase.md. Keep it if it fits.
- Every version so far still felt like "a normal tag/assist game at the end of the day".

## Ideas still on the table (not decided)
- **Two partner buttons** (Nitroplus Blasterz style): S1 and S2, one move each, no 6S.
- **Partners as effects, not just hits.** Strikers attack, supports buff, analysts mark weaknesses (Doris), trappers make zones. A hit landing while two partner effects are active is a LINK, which Unbalances the opponent and opens a Rush.
- **Cold Steel's loop:** Unbalance, then Link Attack, then Brave Points / Orders.
- **A partner who joins mid-round** (Marvel Tōkon's progressive team).
- **A partner who adds moves to any fighter** (Arcana Heart 3).

## Games already studied for reference
E's Laf++, Idol Showdown, AQUAPAZZA, Nitroplus Blasterz, Million Arthur: Arcana Blood, Dengeki Bunko: Fighting Climax Ignition, Vanguard Princess, Umineko: Golden Fantasia, Marvel Tōkon. Still to look at: Persona 4 Arena Ultimax, Dragon Ball FighterZ, 2XKO (Fuses), Arcana Heart 3, Skullgirls, MvC2.

## How I want you to work
1. First, ask me what you need about the campaign's partners: who they are and what each one *does* (fights, supports, points, heals...). Don't guess.
2. Then pitch **at most 3 genuinely different structures** in plain words. For each: the rules (3 or fewer), one example round, and why it's unique to Netsu.
3. Recommend one. No code and no long docs until I pick.
