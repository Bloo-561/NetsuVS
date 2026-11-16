# What Netsu VS still needs (opinion, Oct 24 2026)

Asked for on Oct 24: "look at everything and tell me what I am missing or what I need to change to make it a
fighting game people will enjoy playing" (suggestions only, nothing here is built). Ordered by how much I think
each one matters.

## Must-have before strangers play it
1. **Throws (and throw tech).** Nobody can throw yet, so blocking beats everything and offense has no answer
   to a player who just holds back. Every fighter needs a fast A+B throw (5–7 frame startup, short range), a tech
   window (about 10 frames: press throw too to break it), and no throws on someone who just left blockstun or
   woke up for a few frames. Air throws can come later.
2. **Sound.** Flan, Leticia and the assists have no attack or voice sounds, and hits use the engine's stock set.
   Sound is half of how heavy a hit feels: whoosh per strength, hit / block sounds per strength (light, heavy,
   counter hit), voice lines (attacks, special names, supers, hurt, KO, intros, win quotes), assist call voices.
   Even placeholder voices are better than none.
3. **One frame-data rulebook for everyone.** Pick shared rules and fit every move to them: lights 5–6 frames,
   mediums 7–9, heavies 10–13; lights + on block, mediums slightly −, heavies punishable; every fighter gets a
   reliable anti-air and some meterless or 2-bar reversal; specials that are "safe" or "unsafe" on purpose. Right
   now each fighter's numbers came from her own art timings, so the cast doesn't feel like one game yet.
4. **Combo limits.** With assists that can be called mid-combo, loops and infinites will be found fast. A clear
   limiter (hitstun gets shorter the longer a combo runs, gravity on juggles, a cap on wall bounces / ground
   bounces per combo) and damage scaling that everyone can predict. Also make sure an assist from behind plus an
   overhead from the front can't make a true unblockable (common in assist games: make the second hit
   blockable either way if both come within a few frames).
5. **Input leniency.** Motion buffers of ~10–12 frames, a 2–3 frame window for two-button presses (A+B, B+C),
   a clear rule for 236 vs 623 (the engine checks 623 first, so walking forward and then doing 236 can come out as
   the 623 move), SOCD cleaning for leverless controllers (left + right = neutral), buffering a special during
   hitstop / blockstun. Players blame the game, not themselves, when a move doesn't come out.
6. **Answers to Leticia's beams.** Full-screen beams need counterplay or she'll be the least fun opponent:
   long recovery so a read gets punished, moves that go through projectiles for each fighter, a universal way to
   close distance (projectile-invincible dash or super jump), small chip damage, maybe a cooldown.
7. **A flash / shake option.** The EX and super cut-ins and the super flash are bright and fast: add "reduce
   flashing" and "screen shake" toggles in Options (photosensitivity), and keep them on by default.

## What makes people stay
8. **A tutorial and combo trials.** Movement, blocking high / low, throws, meter, Burst, Overdrive, Pushblock and
   assists are a lot of systems: a short tutorial per system, then 8–10 combo trials per fighter (easy to hard).
   Training mode already has the tools for this.
9. **A frame meter in training** (like Street Fighter 6 / Guilty Gear Strive): a bar showing startup, active,
   recovery and frame advantage of every move as it happens. The hitbox viewer exists; this is the other half of
   learning a character.
10. **Arcade / story built on the campaign.** Netsu No Kiseki's lore is the thing no other fighting game has:
    an arcade route per character with a rival fight, short story scenes before / after fights, and endings.
    Matchup-specific intros and win quotes (some exist) go a long way.
11. **A signature mechanic.** Burst, Overdrive, Pushblock, EX and assists are all borrowed (which is fine), but
    the games people remember have one thing that is theirs (Guilty Gear's Roman Cancel, Under Night's GRD,
    Melty Blood's Shield). "Netsu" (heat) is a perfect name for one: e.g. Overdrive becomes a branded "Netsu"
    state with its own visual, its own super or special-to-special cancels, tied to the story.
12. **More fighters with clear, different game plans.** For a release, 8–12 is the usual minimum, and every
    archetype should exist: rushdown (Cecilia), zoner (Leticia), brawler (Flan), plus a grappler with command
    throws, a footsies / mid-range fighter, a set-play / puppet fighter, a stance fighter. Give each one a unique
    mechanic (Flan's planned "charge punches + Heat" is a good example) instead of the same 236 / 623 / 214
    template for everyone.
13. **Online that always connects.** Lobby codes are a good start, but a direct connection fails behind some
    routers and mobile hotspots. A small relay / matchmaking server, or Steam's networking if it goes on Steam
    (lobbies, friend invites, relay built in), plus: replays, rematch counter, casual / ranked queues, spectators.
    The engine is deterministic now, so **replays** are cheap (save the inputs).
14. **A better CPU.** The CPU is most players' first opponent: difficulty levels, blocking that reacts to
    high / low, anti-airs, punishing unsafe moves, no random super spam.

## Polish
15. **Hit feel table.** Hitstop per strength (light 8, medium 10, heavy 12, counter hit +4 and a unique sound),
    screen shake on heavies only, a short slow-down and zoom on the final KO, distinct counter-hit sparks.
16. **Missing animations.** Flan has no block drawings, Meteor Drop has no recovery pose, nobody has throws,
    taunts or intros; crumple / wall-bounce / ground-bounce reactions should look different from a normal hit.
17. **Real move names** (many are placeholders) and command lists that explain what each move is for.
18. **Small fairness details.** Hurtboxes that match the drawings (players hate hits that look like they
    missed), the same health for everyone unless it's a character trait on purpose (Flan has 11000), same walk /
    dash speeds within an archetype.
19. **Accessibility.** An optional simple-input mode (auto-combo on A, specials on one button, like Under Night's
    Smart Steer or Granblue's assisted controls), bigger HUD text option, colour-blind-safe P1 / P2 colours.
20. **Playtest early with fighting game players.** A local scene night or an online beta with a feedback form;
    write down frame data and change it on a schedule (balance patches) instead of after every comment.
