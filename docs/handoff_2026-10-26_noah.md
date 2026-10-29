# Handoff — Oct 26 2026, late afternoon (TamaDeez: Noah fixes)

**Build first:** one C# file changed (`SakugaActor.cs`, the STOCK badge). Press **Build** in Godot before playing.

First batch of Tamaki's second list (Noah). The rest of that list comes in later batches: systems (OTG / hard
knockdown time, no super OTG, tech flash, assist cancel only on hit, throw cancels, BBCF Overdrive, Mary's 6S), Flan,
menus & art, and the hurtbox / hitbox pass for everyone.

## Noah
1. **236C Umbral Wall** is bigger (1.6×) and races across the screen (7 m/s). It only disappears off the screen
   (16 m past Noah) or when it touches the opponent; there it bursts for its other two hits (the last launches, as
   before) and disappears. On block it bursts the same way.
2. **5A** is a standing low: hits low, and its box is taller (floor to about 0.6 m, same reach).
3. **5B** whiffed because its kick drawing was placed 90 px behind him (the foot never reached past his own body).
   The kick is drawn further forward, its box sits on the shin and foot, and he steps forward a little more.
4. **5C**'s attack box is on the devil arm now (it was down at his front foot).
5. **STOCK READY** badge under his Burst gauge while the energy from Void Grasp / Void Devour (214A / 214C) is stocked
   for Overflow Ray. Colour: `stock_color` on the HUD (Inspector).

Details and files: `docs/characters/noah.md` (end of the file).

## Not checked here
No Godot here: Build, then the checklist.

## Testing checklist
1. Training as Noah, dummy at mid-screen: 236C. The wall crosses the screen; it bursts on the dummy (3 hits, launch).
   Dummy far away and jumping over it: the wall keeps going off the screen.
2. 5A on a crouching blocking dummy: blocked low (standing block gets hit).
3. 5B point blank and at 5A range: it connects. He steps forward a little.
4. 5C at its tip: connects at arm height.
5. 214A on hit: the STOCK READY badge appears under his Burst gauge; 214 + A (Overflow Ray): it goes away.

## Backups
`_backup_stage_select/pre_push_oct26_noah/` (every file this replaced, `.bak`).
