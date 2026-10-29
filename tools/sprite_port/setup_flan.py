"""FLAN'S CUT-INS, SKINS, QUOTES AND MOVE LIST (Oct 24). Run after moves_flan.py:

    python setup_flan.py            (--no-art: everything but the cut-in pictures)

  * Artwork/CutIn_EX.png from 12_EX_Cut_In/Flan_EX_Cut_In.png (EX banner), Artwork/CutIn_Super.png from her
    select render Flan_MainRender.png (super cut-in); her other menu pictures stay as they are
  * her 3 colour skins point at her own colour files again (the rebuild copied Cecilia's colour uids
    into them, Oct 24) and every skin shows her own idle in the editor
  * 0_FLN_Data.tres: win quotes (she had Cecilia's), health 11000 (a sturdier brawler)
  * command_list.json (pause-menu move list)
Her profile, colours (Starlight / Polaris / Stigmata / Rose Gold) and roster slot stay as they were.
Everything replaced is backed up once in _backup_stage_select/pre_flan_setup/. Edit the tables and run again.
"""
import os, sys, re, json, shutil
HERE = os.path.dirname(os.path.abspath(__file__)); PROJ = os.path.abspath(os.path.join(HERE, '..', '..')); sys.path.insert(0, HERE)
from PIL import Image
from fdk import res_uid
from tres import Tres
from analyze import cfg, source_root
from make_artwork import trim, to_height

CH, TAG, NAME = 'flan', 'FLN', 'Flan'
BK = os.path.join(PROJ, '_backup_stage_select', 'pre_flan_setup')
MAX_HEALTH = 11000
SKIN_PREVIEW = 'res://actors/flan/Sprites/v2/idle_base.png'
# win quotes: (opponent ShortName or None for the default, quote)
QUOTES = [
    (None, "Yay! That one really sparkled!\nWanna go again?"),
    ('Cecilia', "Your blade's quick, Cecilia...\nbut my fists hit harder!"),
    ('Leticia', "Gotcha! You can't hover\naway from me forever!"),
    ('Flan', "Two of me? That's twice\nthe starlight!"),
]
COMMANDS = {
    "fighter": "Flan Returna",
    "note": "Numpad notation, facing right: 6 = forward, 4 = back, 2 = down, 8 = up, 236 = quarter circle forward. Craft Gauge: 6 bars, kept between rounds. Overdrive: more damage and Craft Gauge until the Burst gauge runs out.",
    "sections": [
        {"title": "Normals", "moves": [
            ["5A / 5B / 5C", "A / B / C", "chains A > B > C; 5C reaches with a burst of light"],
            ["2A / 2B / 2C", "2 + A / B / C", "low hits; 2C is a sliding punch that knocks down"],
            ["6C", "6 + C", "fist pump: hits above her (anti-air)"],
            ["Air A / B / C", "in air: A / B / C", "air B is a knee"]]},
        {"title": "Specials", "moves": [
            ["Star Fist", "236 + A", "short lunging punch"],
            ["Twirling Star Fist", "236 + B", "arm twirl that absorbs one hit, then a punch that knocks them away"],
            ["Supernova Fist (EX)", "236 + C (2 bars)", "invincible punch with a big light; crumples them for a follow-up. Without 2 bars = 236 + B"],
            ["Rising Star", "623 + A / B", "uppercut that rises with a burst of light at the top (B: higher, invincible start: her anti-air)"],
            ["Falling Star", "A / B / C at the top of Rising Star", "beam down at an angle that slams them to the floor"],
            ["Spiral Star (EX)", "623 + C (2 bars)", "invincible spinning rise, many hits"],
            ["Meteor Drop", "214 + A / B", "rising knee, then a falling punch (hit high: block standing) into a ground impact (B: higher)"],
            ["Meteor Impact (EX)", "214 + C (2 bars)", "invincible start; the bigger impact crumples them"]]},
        {"title": "Supers", "moves": [
            ["Radiant Breaker", "236 + B + C (3 bars)", "windmill windup, dash punch; on hit a point-blank radiant burst"],
            ["Big Bang Crash", "214 + B + C (3 bars)", "rising punch; on hit she dives with them into a huge explosion"]]},
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
    if os.path.exists(p) and open(p, encoding='utf-8').read() == text: return
    backup(p); open(p, 'w', encoding='utf-8', newline='\n').write(text); print('wrote', os.path.relpath(p, PROJ))

def artwork():
    c = cfg(CH); root = source_root(c); out = path('Artwork'); os.makedirs(out, exist_ok=True)
    ex = trim(Image.open(os.path.join(root, c['artwork']['cutin_ex'])).convert('RGBA'), 0.0)
    ex.save(os.path.join(out, 'CutIn_EX.png')); print('wrote Artwork/CutIn_EX.png %dx%d' % ex.size)
    render = path('Artwork/Flan_MainRender.png')
    sup = to_height(trim(Image.open(render).convert('RGBA')), 1500) if os.path.exists(render) else ex
    sup.save(os.path.join(out, 'CutIn_Super.png')); print('wrote Artwork/CutIn_Super.png %dx%d' % sup.size)

def skins():
    for n in range(4):
        p = path('Instances/%s_Fighter_Skin%02d.tscn' % (TAG, n)); t = open(p, encoding='utf-8').read(); t2 = t
        m = re.search(r'\[ext_resource type="Material"[^\]]*path="(res://actors/%s/Palettes/[^"]+)"[^\]]*\]' % CH, t2)
        if m:
            used = re.search(r'material_override = ExtResource\("([^"]+)"\)', t2)
            line = '[ext_resource type="Material" uid="%s" path="%s" id="%s"]' % (res_uid(m.group(1)), m.group(1), used.group(1))
            t2 = t2.replace(m.group(0), line)
        t2 = re.sub(r'path="res://actors/(?:cecilia|flan)/Sprites/(?:v2/idle_O0|idle1)\.png"', 'path="%s"' % SKIN_PREVIEW, t2)
        t2 = re.sub(r'(\[ext_resource type="Texture2D") uid="[^"]+"( path="%s")' % re.escape(SKIN_PREVIEW), r'\1\2', t2)
        write(p, t2)

def data():
    p = path('0_%s_Data.tres' % TAG); t = Tres(open(p, encoding='utf-8').read())
    fo = t.ext_id_for_path('res://engine/sakuga/Resources/FighterOutro.cs')
    old = re.findall(r'SubResource\("([^"]+)"\)', t.res_get('Outros') or '')
    t.sub = [s for s in t.sub if not s[0].startswith('outro_') and s[0] not in old]
    ids = []
    for n, (opp, q) in enumerate(QUOTES):
        body = ['script = ExtResource("%s")' % fo, 'StateIndex = -1']
        if opp: body.append('ForOpponent = "%s"' % opp)
        body += ['FinalMessage = "%s"' % q.replace('\\', '\\\\').replace('"', '\\"'), 'metadata/_custom_type_script = "uid://bne635raru5sj"']
        t.sub.append(['outro_%d' % n, 'Resource', body]); ids.append('outro_%d' % n)
    t.res_set('Outros', '[%s]' % ', '.join('SubResource("%s")' % i for i in ids))
    t.res_set('MaxHealth', str(MAX_HEALTH), after='Stances')
    t.prune()
    write(p, t.text())

def command_list():
    # Oct 25 night: the json is edited directly now (6C, the EX moves' texts): COMMANDS only makes a missing file
    if not os.path.exists(path('command_list.json')):
        write(path('command_list.json'), json.dumps(COMMANDS, indent='\t', ensure_ascii=False))

if __name__ == '__main__':
    if '--no-art' not in sys.argv: artwork()
    skins()
    data()
    command_list()
