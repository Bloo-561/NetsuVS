You're building a 3D model of Cecilia Richter, a fighter in Netsu VS, my 2D anime fighting game (Godot 4.7.2 mono, built on the Mahou SakugaEngine). A first attempt failed: it was built from generic scripted shapes and guessed proportions and didn't look like her. This is the second and last honest attempt. The ONLY goal is ACCURACY to her turnaround sheet. Speed and elegance don't matter; matching the sheet does.

WHAT IT'S FOR
A cel-shaded 3D model, Guilty Gear Xrd style, that we can pose and render into 2D sprite frames that always stay on-model. It must match the sheet, be rigged, and render as clean anime-style art.

FILES (on my PC, through the linked computer)
- Project: E:\Netsu Projects\Netsu Fighter\Godot\netsu-vs
- Work ONLY in actors/cecilia/3d_v2/ (it has a .gdignore so Godot skips it). The old attempt in actors/cecilia/3d/ stays untouched; you may look at it for what NOT to do.
- References, already cut from the sheet at its original resolution:
  - actors/cecilia/3d_v2/refs/cecilia_ref_front.png, cecilia_ref_back.png, cecilia_ref_side.png: T-pose orthographic views. All three crops share the same top and bottom, so the head top and the soles line up across them. The figure is about 682 px tall in each.
  - cecilia_ref_detail_eyes.png, _headband.png, _socks.png, _katana.png: close-up panels.
  - The full sheet: actors/cecilia/Artwork/Cecilia_Turnaround.png
- You can't delete files; move anything replaced into a backup folder inside 3d_v2.

THE METHOD (do it this way; this is what makes it accurate)
1. Reference rig in Blender: load front, back and side as reference images on the orthographic front / back / side axes, scaled so the figure is 1.58 m tall (head top incl. ahoge to sole) with the soles on z = 0 and the centre line on x = 0. Check that the head top, chin, shoulders, waist, skirt hem, knees and ankles land at the same height in all three; report any mismatch.
2. Trace, don't guess: model every part by matching its outline to the reference in the orthographic views (front + side for depth, back for the rear). No proportions from memory or generic anime templates.
3. Measure the match: after every milestone, render a flat silhouette (pure white model on black, ortho camera framed exactly like each ref crop, same resolution). Compare it with a silhouette mask cut from the matching reference (everything not near-white background). Report the overlap (IoU) per view and show a difference image: red = reference only, blue = model only. Targets: front and back IoU at least 0.95, side at least 0.92. Keep fixing until you hit them or explain exactly what's blocking you.
4. Colour by projection: UV unwrap, then project the front and back reference images onto the model from their orthographic cameras (side view for the sides), blending by surface angle, and bake into textures. That way the ribbons, belts, skirt stripes, frills, face, eyes and hair gradient come straight from the sheet instead of being redrawn. Then clean the seams, fill hidden areas (under the arms, inside the skirt, soles) and remove the sheet's soft shading from the bake (flatten to base colours) so the toon shader does the shading.
5. Compare the beauty renders too: render front / back / side with the toon shader at the reference framing and show them side by side with the reference AND as a 50% overlay.

HER DESIGN (from the sheet; if this list and the sheet disagree, the sheet wins)
- Slim, about 7 heads tall, calm small smile.
- Hair: black bob to jaw length, the lower half fading to magenta-purple (strongest at the ends, all the way around). One ahoge. Side bangs framing the face and one lock between the eyes. A small teal hair clip on her right side next to the headband.
- Headband: red with a yellow-gold "V" mark (see the headband panel).
- Eyes: large anime eyes, dark red-brown at the top fading to yellow-gold at the bottom, with a yellow highlight (see the eyes panel).
- Jacket: cropped, ending just under the chest, open at the front, turned-down collar, no hood. Black body, dark-grey sleeves with a red band around each upper arm near the elbow, and rolled white cuffs just below the elbow. Back: plain black with a short centre vent. Side view: a round badge on the upper sleeve.
- White shirt with a frilled collar, short black tie, grey sailor collar, white flower brooch holding a yellow-gold neckerchief that hangs in two tails.
- Red sleeveless pinafore dress; the pleated skirt flares to mid-thigh and has two thin white stripes near the hem and a white scalloped lace petticoat under it.
- Two thin maroon belts with silver buckles crossing at the waist and hips (they cross in an X at the back).
- Black fingerless gloves.
- Legs (ASYMMETRICAL; see the socks panel): RIGHT leg = dark brown-black thigh-high stocking with red ribbons crossing in X's all the way down. LEFT leg = plain dark knee-high sock. Brown loafers with red bows at the ankles.
- No sash, no scarf.
- Weapon: tachi worn on her LEFT hip, hilt forward, sheath angled down and back. Red hilt wrap with a gold diamond pattern, gold end cap, ornate gold guard. WHITE sheath with gold-and-red fittings at the mouth and a red-and-gold tip. The blade is a separate object (glowing yellow lightning is an effect, not the model). The sword must attach to the hip, the right hand or both hands.
- Known sheet inconsistency: the SIDE view shows the criss-cross stocking on the near leg while the sheath sits on the left hip, so it can't be exact about left and right. Use FRONT and BACK for which leg and hip; use SIDE only for profile and depth. Ask me if anything else conflicts.

HONESTY RULES
- At every milestone, show the numbers (IoU), the difference images and the side-by-sides, and say plainly what looks wrong. No "looks great" unless the overlay proves it.
- The face and hair decide whether this works. If by Milestone 3 the head can't get close to the sheet with modelling plus projection, stop and say so. Then recommend the best fallback, and say what you'd need from me:
  (a) An AI image-to-3D tool that takes multi-view images (front / back / side). I'd upload the refs from 3d_v2/refs/ myself and give you the result; you'd clean it, retopologise it, re-project the textures from the sheet, rig it and shade it.
  (b) A VRoid Studio base I build from the sheet; you'd import the VRM and do the rest.

MILESTONES (stop after each one for my OK)
1. Reference rig set up, the height check across the three views, and the plan (what you'll model, how, the risks).
2. Body and clothing silhouettes (blockout) at IoU targets in all three views.
3. Head and hair modelled and projected; front, side and 3/4 face close-ups next to the sheet. Go / no-go decision here.
4. All clothing parts and the tachi detailed to the sheet; IoU re-checked.
5. Textures: projected, cleaned and flattened; beauty renders and overlays.
6. Toon shading: 2-3 tone ramp, colours sampled from the sheet, inverted-hull outlines at a weight that matches the sheet's line art, one fixed key light.
7. Rig: armature with IK arms and legs, fingers, head, eyes, hair, neckerchief and skirt bones, and sword sockets (hip, right hand, both hands). Test poses: her idle stance (actors/cecilia/Sprites/idle1.png, which is a 3/4 view facing right) and a two-handed draw-slash, checked for deformation (shoulders, hips, skirt).
8. Sprite test: transparent 1024x1024 render facing right, about 250 px tall incl. the ahoge, feet on row 620, rear foot near x 403, camera angle matching idle1.png. Show it next to idle1.png. Save as actors/cecilia/3d_v2/renders/idle_test.png.

Save the .blend after every milestone (actors/cecilia/3d_v2/cecilia_v2.blend) and keep every script in actors/cecilia/3d_v2/scripts/ so each step can be re-run. At the end, write actors/cecilia/3d_v2/README.md: what's in the file, how to pose her and render a frame, the final IoU numbers, and what still needs an artist.
