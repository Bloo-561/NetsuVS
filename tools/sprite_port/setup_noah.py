"""NOAH'S PROFILE, COLOURS AND ROSTER SLOT (Oct 25). Run after moves_noah.py:

    python setup_noah.py

  * Artwork/ pictures (make_artwork.py, "artwork" block of manifests/noah.json; the select portrait is the pack's
    Artwork/Noah_Character_Select_Portrait.png with its black background made transparent: derived_noah_art.py)
  * 0_NOA_Profile.tres: names, bio, select-screen / win-screen pictures
  * his 4 colours: Umbra (as drawn), Crimson, Azure, Pale (sprite_color_swap shader: the purple devil-arm energy +
    the black coat)
  * win quotes (0_NOA_Data.tres -> Outros), command_list.json (pause-menu move list), data/roster.tres (after Leticia)
Everything replaced is backed up once in _backup_stage_select/pre_noah_setup/.
"""
import os, sys, re, json, shutil
HERE = os.path.dirname(os.path.abspath(__file__)); PROJ = os.path.abspath(os.path.join(HERE, '..', '..')); sys.path.insert(0, HERE)
from fdk import res_uid, new_uid
from tres import Tres
import make_artwork

CH, TAG, NAME = 'noah', 'NOA', 'Noah'
BK = os.path.join(PROJ, '_backup_stage_select', 'pre_noah_setup')
ART = 'res://actors/noah/Artwork/'
PROFILE = dict(FighterName='Noah Swallowtail', ShortName='Noah',
               Bio='A hooded youth whose cursed devil arm devours light: shadow waves, black holes and stolen energy.',
               AuraColor='Color(0.68, 0.32, 1, 1)')   # EX / super aura and super smoke (his arm's purple)
# the purple of his arm / effects = the "trim" band; the coat = "dark"
ARM = dict(hue_offset=0.0, trim_hue_min=0.68, trim_hue_max=0.92, trim_min_sat=0.3)
COLORS = [
    ('Umbra', None, None),
    ('Crimson', 'Palettes/Color2/NOA_Palette_Crimson_MAT.tres', dict(ARM, target_hue=0.985, target_sat=0.95, target_val=1.0,
                                                                    dark_max_sat=0.3, dark_max_val=0.45, dark_hue=0.99, dark_sat=0.35, dark_lift=1.25)),
    ('Azure', 'Palettes/Color3/NOA_Palette_Azure_MAT.tres', dict(ARM, target_hue=0.54, target_sat=0.9, target_val=1.05,
                                                                dark_max_sat=0.3, dark_max_val=0.45, dark_hue=0.61, dark_sat=0.35, dark_lift=1.3)),
    ('Pale', 'Palettes/Color4/NOA_Palette_Pale_MAT.tres', dict(ARM, target_hue=0.12, target_sat=0.85, target_val=1.1,
                                                              dark_max_sat=0.3, dark_max_val=0.45, dark_hue=0.6, dark_sat=0.05, dark_lift=2.3)),
]
OLD_MATS = ['Palettes/Color2/NOA_Palette_Polaris_MAT.tres', 'Palettes/Color3/NOA_Palette_Stigmata_MAT.tres', 'Palettes/Color4/NOA_Palette_RoseGold_MAT.tres']
QUOTES = [
    (None, "...Stay down. I can't hold it\nback much longer."),
    ('Noah', "So that's what I look like\nwhen it takes over. Hm."),
    ('Cecilia', "Your lightning's bright, Cecilia.\nThe dark still swallowed it."),
    ('Flan', "Starlight, huh. It tasted\nwarm. Sorry."),
    ('Leticia', "Light bends near a black hole.\nYour shots never had a chance."),
]
COMMANDS = {
    "fighter": "Noah",
    "note": "Numpad notation, facing right: 6 = forward, 4 = back, 2 = down, 8 = up, 236 = quarter circle forward. Craft Gauge: 6 bars, kept between rounds. Overdrive: more damage and Craft Gauge until the Burst gauge runs out.",
    "sections": [
        {"title": "Normals", "moves": [
            ["5A / 5B / 5C", "A / B / C", "chains A > B > C; 5C is a long devil-arm punch"],
            ["2A / 2B / 2C", "2 + A / B / C", "2A is low; 2C sweeps"],
            ["6C", "6 + C", "devil-arm uppercut"],
            ["Air A / B / C", "in air: A / B / C", "air C punches down"]]},
        {"title": "Specials", "moves": [
            ["Shade Wave", "236 + A", "a wave of shadow rolls along the floor"],
            ["Twin Shade", "236 + B", "two waves, one after the other"],
            ["Umbral Wall (EX)", "236 + C (2 bars)", "invincible start: a wall of energy pushes slowly forward, three hits, launches"],
            ["Event Horizon", "623 + A / B", "a black hole opens close in front of him (A) or far away (B); it waits about 5 seconds"],
            ["Twin Horizon (EX)", "623 + C (2 bars)", "both black holes at once, invincible start"],
            ["Collapse", "623 + A / B / C (a hole is open)", "finger snap: the holes suck the opponent in and burst; the near one throws them away, the far one toward him"],
            ["Void Grasp", "214 + A", "low grab lunge; on hit he drains them and stocks the energy"],
            ["Abyss Hammer", "214 + B (also in air)", "jumping overhead smash with the devil arm"],
            ["Void Devour (EX)", "214 + C (2 bars)", "invincible lunge: grabs the face, drains, explosion; stocks the energy"],
            ["Overflow Ray", "214 + A / B (energy stocked)", "a long purple beam, three hits; uses the stock"],
            ["Fallen Grasp", "in air: 214 + A", "air grab: drags them down into a ground explosion"]]},
        {"title": "Supers", "moves": [
            ["Raging Storm", "236236 + A/B/C or 236 + B + C (3 bars)", "charge, ground slam, a storm of purple fire around him, then the last burst throws them away"],
            ["God Press", "214214 + A/B/C or 214 + B + C (3 bars)", "sliding grab: carries them to the wall, three slams, then a blast that knocks him back onto one knee"]]},
        {"title": "System", "moves": [
            ["Dash / Back dash", "66 / 44", ""], ["Super jump", "2 then 8", ""], ["Air dash", "in air: 66 / 44", ""],
            ["Throw", "B + C (close)", "4 + B+C throws behind you"], ["Throw break", "B + C as you're grabbed", "12-frame window"],
            ["Burst", "A + C", "full Burst gauge, works in hitstun"], ["Overdrive", "A + B + C", "full Burst gauge"],
            ["Pushblock", "A + B", "while blocking, 1 bar"], ["Recover", "any button", "when knocked down"]]},
    ],
}

def path(rel): return os.path.join(PROJ, 'actors', CH, rel)
def backup(p):
    os.makedirs(BK, exist_ok=True); b = os.path.join(BK, os.path.basename(p) + '.bak')
    if os.path.exists(p) and not os.path.exists(b): shutil.copyfile(p, b)
def write(p, text):
    backup(p); open(p, 'w', encoding='utf-8', newline='\n').write(text); print('wrote', os.path.relpath(p, PROJ))

def profile():
    p = path('0_%s_Profile.tres' % TAG); uid = Tres(open(p, encoding='utf-8').read()).uid()
    pics = [('sel_render', NAME + '_Select_FullBody.png'), ('sel_portrait', NAME + '_Select_Portrait.png'),
            ('win', NAME + '_WinRender.png'), ('icon', NAME + '_Icon_Small.png')]
    out = ['[gd_resource type="Resource" script_class="FighterProfile" format=3 uid="%s"]' % uid, '',
           '[ext_resource type="Script" uid="uid://c5w04j5my3h8p" path="res://engine/sakuga/Resources/FighterProfile.cs" id="5"]']
    for i, f in pics: out.append('[ext_resource type="Texture2D" path="%s%s" id="%s"]' % (ART, f, i))
    out += ['', '[resource]', 'script = ExtResource("5")', 'FighterName = "%s"' % PROFILE['FighterName'], 'ShortName = "%s"' % PROFILE['ShortName'],
            'Render = ExtResource("sel_render")', 'Portrait = ExtResource("sel_portrait")', 'Bio = "%s"' % PROFILE['Bio'],
            'VictoryRender = ExtResource("win")', 'OnlineIcon = ExtResource("icon")', 'NetsuAuraColor = %s' % PROFILE['AuraColor'],
            'metadata/_custom_type_script = "uid://c5w04j5my3h8p"', '']
    write(p, '\n'.join(out))

def colors():
    """material files + skins; returns [(name, skin res)]"""
    old_uids = [res_uid('res://actors/%s/%s' % (CH, m)) for m in OLD_MATS]
    out = [(COLORS[0][0], 'res://actors/%s/Instances/%s_Fighter_Skin00.tscn' % (CH, TAG))]
    for n, (cname, mat, prm) in enumerate(COLORS[1:]):
        mp = path(mat); old = path(OLD_MATS[n])
        uid = res_uid('res://actors/%s/%s' % (CH, mat)) or old_uids[n] or new_uid()
        lines = ['[gd_resource type="ShaderMaterial" format=3 uid="%s"]' % uid, '',
                 '[ext_resource type="Shader" path="res://assets/shaders/sprite_color_swap.gdshader" id="1"]', '',
                 '[resource]', 'render_priority = 0', 'shader = ExtResource("1")']
        lines += ['shader_parameter/%s = %s' % (k, v) for k, v in prm.items()] + ['shader_parameter/strength = 1.0', '']
        os.makedirs(os.path.dirname(mp), exist_ok=True)
        write(mp, '\n'.join(lines))
        if os.path.exists(old) and os.path.abspath(old) != os.path.abspath(mp):      # the copied Cecilia colour: out of the project
            os.makedirs(BK, exist_ok=True); shutil.move(old, os.path.join(BK, os.path.basename(old) + '.moved.bak'))
            print('moved', os.path.relpath(old, PROJ), 'to the backup folder')
        skin = path('Instances/%s_Fighter_Skin%02d.tscn' % (TAG, n + 1))
        t = open(skin, encoding='utf-8').read()
        t2 = re.sub(r'\[ext_resource type="Material"[^\]]*path="res://actors/%s/Palettes/[^"]+"' % CH,
                    '[ext_resource type="Material" uid="%s" path="res://actors/%s/%s"' % (uid, CH, mat), t)
        if t2 != t: write(skin, t2)
        out.append((cname, 'res://actors/%s/Instances/%s_Fighter_Skin%02d.tscn' % (CH, TAG, n + 1)))
    for n in range(4):   # editor preview picture: her own idle
        skin = path('Instances/%s_Fighter_Skin%02d.tscn' % (TAG, n))
        t = open(skin, encoding='utf-8').read(); t2 = re.sub(r'path="res://actors/flan/Sprites/v2/[^"]+"', 'path="res://actors/noah/Sprites/v2/idle_0_1.png"', t)
        if t2 != t: write(skin, t2)
    return out

def quotes():
    p = path('0_%s_Data.tres' % TAG); t = Tres(open(p, encoding='utf-8').read())
    fo = t.ext_id_for_path('res://engine/sakuga/Resources/FighterOutro.cs')
    t.sub = [s for s in t.sub if not s[0].startswith('outro_') and s[0] not in re.findall(r'SubResource\("([^"]+)"\)', t.res_get('Outros') or '')]
    ids = []
    for n, (opp, q) in enumerate(QUOTES):
        body = ['script = ExtResource("%s")' % fo, 'StateIndex = -1']
        if opp: body.append('ForOpponent = "%s"' % opp)
        body += ['FinalMessage = "%s"' % q.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\n'), 'metadata/_custom_type_script = "uid://bne635raru5sj"']
        t.sub.append(['outro_%d' % n, 'Resource', body]); ids.append('outro_%d' % n)
    t.res_set('Outros', '[%s]' % ', '.join('SubResource("%s")' % i for i in ids)); t.prune()
    write(p, t.text())

def command_list():
    # Oct 25 night: the json is edited directly now (6C, the EX moves' texts): COMMANDS only makes a missing file
    if not os.path.exists(path('command_list.json')):
        write(path('command_list.json'), json.dumps(COMMANDS, indent='\t', ensure_ascii=False))

def roster(skins):
    p = os.path.join(PROJ, 'data', 'roster.tres'); t = Tres(open(p, encoding='utf-8').read())
    for e in t.ext:   # stale uids (the files were re-made): point at what the files say now
        if e.get('path', '').endswith('.tscn') or e.get('path', '').endswith('.tres'):
            u = res_uid(e['path'])
            if u and e.get('uid') and e['uid'] != u: print('roster: uid fixed for', e['path']); e['uid'] = u
    fe = t.ext_id_for_path('res://engine/sakuga/Resources/FighterElement.cs'); cp = t.ext_id_for_path('res://engine/sakuga/Resources/ColorPaletteElement.cs')
    prof = 'res://actors/%s/0_%s_Profile.tres' % (CH, TAG)
    pid = t.add_ext('Resource', prof, res_uid(prof), prefer_id='%s_profile' % TAG.lower())
    pal_ids = []
    for n, (cname, skin) in enumerate(skins):
        # Oct 24: a path, not a scene reference, so the roster doesn't load every fighter (ColorPaletteElement.GetScene)
        sub = 'netsu_%s_pal%d' % (TAG.lower(), n)
        t.sub = [s for s in t.sub if s[0] != sub]
        t.sub.append([sub, 'Resource', ['script = ExtResource("%s")' % cp, 'PaletteName = "%s"' % cname, 'ScenePath = "%s"' % skin]])
        pal_ids.append(sub)
    el = 'netsu_%s' % TAG.lower()
    t.sub = [s for s in t.sub if s[0] != el]
    t.sub.append([el, 'Resource', ['script = ExtResource("%s")' % fe, 'Profile = ExtResource("%s")' % pid,
                                   'ColorPalettes = [%s]' % ', '.join('SubResource("%s")' % x for x in pal_ids)]])
    els = re.findall(r'SubResource\("([^"]+)"\)', t.res_get('elements') or '')
    if el not in els: els.append(el)
    t.res_set('elements', '[%s]' % ', '.join('SubResource("%s")' % x for x in els))
    t.prune(); write(p, t.text())

if __name__ == '__main__':
    make_artwork.main(CH)
    profile()
    skins = colors()
    quotes()
    command_list()
    roster(skins)
