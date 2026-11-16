# Stage quality audit (2026-11-04)

Every stage was rendered in Godot 4.7.2 (Compatibility) from the mid, near, far and jump_far fight cameras, with stand-in fighters wrapped like the real ones (viewer node plus the engine's `Shadow` Sprite3D). Each stage was judged against the new bar set by North Ambria and Celdic: detailed materials, layered depth, contrast lighting, and fighters lit and grounded by the stage. The renders are in the session scratchpad only; nothing was changed on the PC.

## Ranking

| # | Stage | Verdict | Main problems |
|---|---|---|---|
| 1 | Old Schoolhouse -Entrance- | Full overhaul | Only 15k triangles, and unlike Thors Hall (13k) its textures and lighting don't make up for it. Flat box walls with punched windows, a plain block stair, no furniture or props. Everything is one dark blue, there is no focal point, and the ceiling is a black void from jump_far. |
| 2 | Crimson Abyss | Overhaul the crater (keep the sky) | The spires are faceted low-poly cones repeated in a wall, and the rim rocks are flat-shaded slabs. One violet value everywhere, so there is no depth. |
| 3 | Roer | Partial: near buildings and gateway | The near facades are flat boxes with one repeated window texture. The gateway is a heavy dark slab across the middle of the screen. |
| 4 | Depths of the Old Schoolhouse | Partial: islands and gazebo | The floating islands are crude jagged rocks on a 1024 px atlas. The gazebo is a cage of thin poles that reads as unfinished. |
| 5 | The GeoFront (vault) | Partial: walls and lighting | Large areas of blank navy wall and flat lighting. The vault door holds up. |
| 6 | Septian Chapel | Targeted fix | Icosphere and stacked-cone trees. The cobbles are large and uniform, and the square is empty. The chapel itself is good. |
| 7 | Ordis Manor - Ruined | Targeted fix | The smoke columns render as hard-edged grey panels, and the rubble piles are pale blobs. |
| - | Ordis Manor - Day, Thors Hall (Morning and Dusk) | Fine | Polish only, for example a few training props in Thors Hall. |
| - | North Ambria, Celdic (Day and Evening) | Reference standard | - |

## What each job would involve
- **Entrance:** rebuild the hall with:
  - wood wainscot, mouldings and pilasters;
  - a carved grand stair with turned balusters;
  - props: notice boards, benches, a clock, hanging lamps and a rug;
  - warm lantern pools against cool moonlight, so the colour stops being one blue;
  - a visible beamed ceiling, and dust in the moonbeams.
- **Crimson:**
  - sculpted obsidian and crystal spire clusters with glowing veins and bevelled edges that catch the rim light;
  - layered rim rock with haze between the layers;
  - keep the painted sky, tendrils, fissure floor and particles.
- **Roer:**
  - relief on the near facades: cornices, balconies, shopfronts with awnings and signs, deep window frames and rooftop clutter;
  - an open steel truss arch with lit signage in place of the slab gateway;
  - plaza props.
- **Depths:** sculpted islands with strata, grass and ruins; a proper arched pavilion in place of the pole cage.
- **GeoFront:** panel seams, vents, pipes, cables, signage and consoles on the walls; stronger light contrast; steam and sparks.
- **Chapel:** Celdic's leaf-clump trees and its finer cobble shader; props at the edges of the square.
- **Ordis Ruined:** a soft, billowing smoke shader and a rubble material.

## Quick win for all stages (no rebake)
- **Hidden fighter shadow.** The fighter's `Shadow` Sprite3D has `sorting_offset = -10`. On the mirror-floor stages, the floor is a transparent plane over the reflection copy and draws after the shadow, so it covers it:
  - fully hidden on Crimson, both Schoolhouses and GeoFront;
  - faint on Ordis;
  - Thors Hall, Roer, Chapel, North Ambria and Celdic are fine.
- **Verified fix:** setting the shadow's `render_priority` to 1 makes it draw after the floor. The fix was verified in the test harness on Crimson and Entrance.
- **Fighter tint.** Only North Ambria and Celdic tint the fighters to the stage light.
- **Plan:** a stage-side script (Celdic's `ce_fighter_light.gd`, extended with a shadow priority) added to every stage fixes both. It is stage-only, with no engine change.

## Size reference (triangles / atlases)

| Stage | Triangles | Atlases |
|---|---|---|
| Entrance | 15k | 4096 / 4096 / 2048 |
| Thors Hall | 13k | 4096 ×4, 2048 |
| Depths | 28k | 3072 ×2, islands 1024 |
| Roer | 29k | 4096 ×4, 2048 |
| Crimson | 34k | 4096 ×2, 2048, 1024 |
| GeoFront vault | 35k | 4096 / 3072 |
| Chapel | 36k | 4096 ×3 |
| Ordis | 50–56k | 4096 ×2, 2048 |
| Celdic | 84–110k | 3072 ×2, 2048 (reduced for RAM) |
| North Ambria | 199k | 4096 ×2, 2048 |
