# ComfyUI for Netsu VS sprites (`tools/comfyui/`)

New poses and fixes for a fighter, in that fighter's own style, ready for the sprite port tools
(`tools/sprite_port/`). Made Nov 14 2026. The workflows pass ComfyUI's own validation (checked against
ComfyUI + comfyui_controlnet_aux node definitions), and the scripts were tested on Cecilia's 193 game frames.
The full chain has **not** been run on a GPU yet: the first real test is the "First test" section below.

| File | What it's for |
| --- | --- |
| `workflows/netsu_style_test.json` | **Style test.** One pose you describe → Cecilia in BlazBlue style and in Dengeki Bunko style, same seed, side by side (her look from `actors/cecilia/Artwork/Cecilia_MainRender.png` via IP-Adapter). For picking the style. |
| `workflows/netsu_new_pose.json` | **New pose.** A pose reference (photo of you, 3D render, sketch, an existing frame) → skeleton (DWPose) → 4 candidates of the fighter in that pose (LoRA + ControlNet). |
| `workflows/netsu_fix_frame.json` | **Fix part of a frame.** Paint a mask over a hand / face / ribbon; only that area is redrawn and pasted back. |
| `workflows/*_api.json` | The same two in API format (for scripts / the ComfyUI MCP). |
| `make_lora_dataset.py` | A fighter's finished drawings → LoRA training set (grey background, 832×1216, captions). |
| `cutout.py` | A ComfyUI picture → transparent PNG for the art folder. `--restore` after a fix gives the exact original frame back except the fixed patch. |
| `prep_frame.py` | A game frame → the grey, upscaled picture the fix workflow takes (+ a `.json` so cutout.py can undo it). |

Why it's built this way (lessons from Oct 17–23, `docs/project-context/sprites-start-here.md`): frames made one by
one drift (proportions, socks, sword, eyes). Here the **look** comes from a LoRA trained on the fighter's finished
drawings, the **pose** comes from a skeleton, and fixes only touch the masked pixels. Still keep one style per
fighter and judge results by looking (GIF preview), not by numbers.

## 1. One-time setup
**This PC: AMD Radeon RX 9070 XT (RDNA 4, 16 GB)**, the best-supported AMD card for ComfyUI on Windows (ComfyUI
Desktop has official ROCm support since v0.7.0). ComfyUI installed Nov 15 2026.
- Check it uses the card: the startup log should say `Device: cuda:0 AMD Radeon RX 9070 XT` (ROCm reports as "cuda").
  `cpu` there = AMD backend not picked in the installer or an old driver (update AMD Adrenalin).
- The first run is slow (ROCm compiles kernels); later runs are faster.
- A node that fails only on AMD: usually a CUDA-only extension; the pose node uses the torchscript models (no ONNX).
- **LoRA training: use Civitai's on-site trainer** (base: Illustrious) or a rented NVIDIA GPU; OneTrainer / kohya
  are unreliable on Windows + Radeon. The trained LoRA then runs locally.

1. **ComfyUI**: the ComfyUI Desktop app (comfy.org) or the Windows portable build. Open **Manager → Install
   Custom Nodes** → install **ComfyUI's ControlNet Auxiliary Preprocessors** (`comfyui_controlnet_aux`, for the
   DWPose node) → restart. Its pose models download by themselves on the first run.
2. **Base model** → `ComfyUI/models/checkpoints/`: an **Illustrious-XL** model (anime SDXL). The workflows expect
   `Illustrious-XL-v2.0.safetensors` (Hugging Face: OnomaAIResearch/Illustrious-XL-v2.0); any Illustrious / NoobAI
   *eps* fine-tune also works: just pick it in the node. Avoid v-pred models (they need other sampler settings).
3. **ControlNet** → `ComfyUI/models/controlnet/`: `diffusion_pytorch_model_promax.safetensors` from Hugging Face
   **xinsir/controlnet-union-sdxl-1.0**, renamed to `controlnet-union-sdxl-1.0-promax.safetensors`. If poses are
   ignored with your base model, try an Illustrious-specific OpenPose ControlNet instead and remove the
   "SetUnionControlNetType" node.
4. **For the style test only:** Manager → install **ComfyUI_IPAdapter_plus** (cubiq); put
   `CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors` in `ComfyUI/models/clip_vision/` and
   `ip-adapter-plus_sdxl_vit-h.safetensors` in `ComfyUI/models/ipadapter/` (both from Hugging Face h94/IP-Adapter;
   the pack's README lists them). The two style models from Civitai go in `ComfyUI/models/loras/` as
   `arcsys_blazblue_sprite_style_illustrious.safetensors` (civitai.com/models/2251256) and
   `dengeki_bunko_sprite_style_illustrious.safetensors` (civitai.com/models/996658). Both are Illustrious LyCORIS,
   triggers `full body, pixel art, simple background`, clip skip 2 (already set in the workflow).
5. Drag a workflow `.json` from `workflows/` onto ComfyUI. Red nodes = something missing (step 1–3).

## 2. Pick the style (`netsu_style_test.json`)
Write the neutral pose in **Pose (write this)**, load the render in **Character reference**, queue. Two pictures per
style land in `ComfyUI/output/netsu/style_test/`. Both samplers use the same seed, so the only difference is the
style. Then train the fighter's LoRA in the chosen style (below): first redraw her existing frames in that style,
so the LoRA learns her *and* the style. The move itself (the second prompt) comes after that.

## 3. Train a LoRA per fighter (once per fighter, ~1 h)
```
python tools/comfyui/make_lora_dataset.py "C:/Users/elvis/Downloads/Fighting_Game_All_Sprites/Cecilia_Original_Idle_Style" "C:/Users/elvis/Downloads/Fighting_Game_All_Sprites/Cecilia" --name netsu_cecilia --tags "black hair, purple hair tips, red headband, yellow-brown eyes, katana"
```
(or `actors/cecilia/Sprites/v2`: works, but those are ~500 px and get upscaled 2×; the artist's full-size drawings
are better. Don't feed it `Archive/`.) Effects on their own, tiny pictures and near-duplicate idle frames are
skipped; frames with big slash trails get the tags `lightning, yellow slash trail` so trails stay optional in
prompts. Check `datasets/netsu_cecilia/contact_sheet.png` and delete anything off-model.
Tested on Cecilia's game frames: 130 of 193 kept, all of them her.

Train with **OneTrainer** (Windows GUI) or **kohya_ss**: SDXL LoRA, base = the same Illustrious checkpoint, dataset =
the `<repeats>_netsu_cecilia` folder (captions are the `.txt` files), resolution 1024 with bucketing, rank 16 /
alpha 8, AdamW8bit lr 1e-4 (or Prodigy lr 1), batch 2, ~10 epochs, gradient checkpointing on, save every 2 epochs.
Put the `.safetensors` in `ComfyUI/models/loras/` as `netsu_cecilia.safetensors`. Try the saved epochs in the
pose workflow and keep the one that looks most like her without copying her existing poses.

Trigger words: `netsu_cecilia`, `netsu_flan`, `netsu_leticia`, ... (the `--name`). Other fighters: change
`--subject` (e.g. `1boy`) and `--tags`.

## 4. Daily use
**New pose** (`netsu_new_pose.json`)
1. Load a portrait pose reference (whole body visible). Check the *Pose map* preview: a wrong skeleton gives a
   wrong picture.
2. LoRA + trigger word, danbooru tags for the pose; keep `facing right` and `grey background, simple background`.
   Generate the character **without** big effects; effects are separate pictures in the set.
3. Queue → 4 candidates in `ComfyUI/output/netsu/`. Then:
   `python tools/comfyui/cutout.py <candidate>.png --out <art folder> --name <frame name> --preview`
   (`--flip` if it faces left). Look at `<name>_check.png`: nothing of her should be missing.
4. Into the game like any drawing: manifest `frames` → `python build.py <fighter> <anim> --preview` →
   `python hitfit.py <fighter> <anim> --write`.

**Fix a frame** (`netsu_fix_frame.json`)
1. `python tools/comfyui/prep_frame.py actors/cecilia/Sprites/v2/5b_2.png --out <somewhere>` → `5b_2_flat.png` + `.json`.
2. Load `5b_2_flat.png`, right-click → **Open in MaskEditor**, paint the part to redraw, describe it in the prompt.
3. Queue, pick one, then
   `python tools/comfyui/cutout.py <result>.png --restore <somewhere>/5b_2_flat.json --out <art folder> --name 5b_2`
   → same size as the original; every pixel outside the fixed patch is the original's (tested: an untouched round
   trip changes 0 pixels).

Knobs: ControlNet strength 0.6–1.0 (stiff ↔ ignores pose), LoRA 0.8–1.0 (off-model ↔ overcooked), fix denoise
0.4–0.7, cfg 5–7.

## 5. Optional: let Claude drive ComfyUI (MCP)
Comfy's official MCP server lets a Claude chat linked to this PC run these workflows, upload pose references and
collect the outputs itself. Install: `pip install comfy-mcp "comfy-cli>=1.14.0"`, then in the Claude desktop app
Settings → Developer → Edit Config add
```json
{ "mcpServers": { "comfy-mcp": { "command": "comfy-mcp", "env": { "COMFYUI_URL": "http://127.0.0.1:8188" } } } }
```
(add `"COMFY_BIN": "<path to comfy.exe>"` if `comfy` isn't on PATH), restart the app, start ComfyUI. It accepts
the workflow files here (UI or API format). Source: github.com/Comfy-Org/comfy-mcp.

## First test (not done yet)
Cecilia LoRA → one throw pose (nobody has a throw yet) → cutout → `build.py --preview` next to her 5A frames.
If her face, socks or sword drift from the real frames, more/better training images or a lower LoRA strength
come before anything else.
