#!/usr/bin/env python3
"""Frame data spreadsheets (Oct 25 2026): makes data/frame_data/Cecilia.xlsx, Flan.xlsx, Leticia.xlsx, Noah.xlsx, Assists.xlsx
and data/frame_data/frame_data.json from the game's own data.

The game reads them back at the start of every match (and in Training the moment one is saved):
engine/sakuga/Game/NetsuFrameData.cs. Only cells that no longer say what frame_data.json remembers are used.

HOW TO REBUILD THEM (after moves change in the game):
 1. Dump what the game really uses (Godot test runner, container copy only):
      rtrun -- "--rt-fddump=DUMPDIR;res://actors/cecilia/0_CEC_Data.tres;res://actors/flan/0_FLN_Data.tres;
               res://actors/leticia/0_LET_Data.tres;res://actors/noah/0_NOA_Data.tres;res://actors/assists/mary/0_MRY_Data.tres;
               res://actors/assists/mary/0_MRYN_Data.tres;res://actors/assists/adin/0_ADN_Data.tres;
               res://actors/assists/eren/0_ERN_Data.tres;res://actors/assists/harie/0_HRE_Data.tres"
    (NetsuFrameData.Describe for each one, plus assist_list.json.)
 2. python3 tools/frame_data/make_sheets.py DUMPDIR --keep OLDDIR
    OLDDIR = a copy of data/frame_data as the user has it now (their .xlsx and frame_data.json): every cell they
    changed is carried over into the new sheets, so their changes keep applying. Without --keep the sheets start
    clean (no changes).
 3. python3 <xlsx skill>/scripts/recalc.py on each .xlsx (fills in the formulas' values for previewers).
"""
import argparse
import datetime
import json
import os
import re
import sys

from openpyxl import Workbook, load_workbook
from openpyxl.comments import Comment
from openpyxl.formatting.rule import CellIsRule, FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUT = os.path.join(ROOT, 'data', 'frame_data')

FIGHTERS = [
    dict(file='Cecilia.xlsx', name='Cecilia', data='res://actors/cecilia/0_CEC_Data.tres', dump='0_CEC_Data.json',
         cmd='actors/cecilia/command_list.json'),
    dict(file='Flan.xlsx', name='Flan', data='res://actors/flan/0_FLN_Data.tres', dump='0_FLN_Data.json',
         cmd='actors/flan/command_list.json'),
    dict(file='Leticia.xlsx', name='Leticia', data='res://actors/leticia/0_LET_Data.tres', dump='0_LET_Data.json',
         cmd='actors/leticia/command_list.json'),
    dict(file='Noah.xlsx', name='Noah', data='res://actors/noah/0_NOA_Data.tres', dump='0_NOA_Data.json',
         cmd='actors/noah/command_list.json'),
]
# what an assist sends out (its own actor and data): rows "Mary (note):2"
ASSIST_PARTS = {'Mary': [('Mary (note)', 'res://actors/assists/mary/0_MRYN_Data.tres', '0_MRYN_Data.json',
                          '6S note')]}

# inputs the move files' names and the command list can't tell
INPUT_OVERRIDES = {
    '59_FLN_FallingStar': "A/B/C at Rising Star's top",
    '65_FLN_FallingStar_Air': 'j.236A/B',
    '62_LET_RicochetPrism': '214B (hold B: 2nd angle)',
    '55_LET_Crossfire_2': '236A/B again',
    '56_LET_Crossfire_3': '236A/B again',
    '69_CEC_214R2': '214A/B again',
    '70_CEC_214R3': '214A/B again',
    '59_NOA_Collapse': '623A/B/C (a hole open)',
    '63_NOA_OverflowRay': '214A/B (energy stocked)',
    '64_NOA_FallenGrasp': 'j.214A',
    '65_NOA_AbyssHammer_Air': 'j.214B',
    '61_NOA_AbyssHammer': '214B',
    '66_NOA_RagingStorm': '236236 any',
    '68_NOA_RagingStorm_BC': '236BC',
    '67_NOA_GodPress': '214214 any',
    '69_NOA_GodPress_BC': '214BC',
}

# --- look -----------------------------------------------------------------------------------------------------------
FONT = 'Arial'
NAVY = '1B2350'
INK = '1F2433'
GREY_TEXT = '6B7280'
EDIT_FILL = PatternFill('solid', fgColor='FFFFFF')
GREY_FILL = PatternFill('solid', fgColor='EEF0F4')
HEAD_FILL = PatternFill('solid', fgColor=NAVY)
GROUP_FILL = PatternFill('solid', fgColor='2E3A7A')
SECTION_FILL = PatternFill('solid', fgColor='D9E2F7')
CHANGED_FILL = PatternFill('solid', fgColor='FFE680')
THIN = Side(style='thin', color='C9CED8')
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)


def font(**kw):
    base = dict(name=FONT, size=10, color=INK)
    base.update(kw)
    return Font(**base)


# --- columns --------------------------------------------------------------------------------------------------------
# (header, key, width, help). The headers are what the game looks for: keep them as they are.
MOVE_COLUMNS = [
    ('ID', 'id', 6, 'The move\'s number in the game (its state). The game finds the row by it: don\'t change it.'),
    ('Move', 'move', 34, 'The move (follow-ups are indented under the move they come from).'),
    ('Input', 'input', 18, 'How it\'s done (numpad notation, facing right).'),
    ('Hits', 'hits', 6, 'How many times it can hit.'),
    ('Startup', 'startup', 9, 'The frame its first hitbox appears on (the move\'s first frame is 1).'),
    ('Active', 'active', 13, 'Frames from its first hitbox to its last one.'),
    ('Recovery', 'recovery', 10, 'Frames after its last hitbox until the fighter can act again.'),
    ('Total', 'total', 8, 'The whole move: Startup - 1 + Active + Recovery. On a part with no hitbox (a dash, a landing) '
                          'it\'s the length of that part, and you can change it.'),
    ('On hit', 'onhit', 8, 'Frame advantage when the first active frame hits (what Training shows). KD = knocks down.'),
    ('On block', 'onblock', 9, 'Frame advantage when the first active frame is blocked (what Training shows). '
                               'Negative = the opponent recovers first.'),
    ('Damage', 'damage', 9, 'Damage of the first hit. Several hits: all of them change by the same percentage.'),
    ('Chip', 'chip', 7, 'Damage done when blocked.'),
    ('Guard', 'guard', 12, 'High = block standing (overhead), Mid = block either way, Low = block crouching, '
                           'Unblockable.'),
    ('Hitstun', 'hitstun', 9, 'Frames a standing / crouching opponent is stunned by the hit.'),
    ('Air hitstun', 'air_hitstun', 11, 'Frames an opponent hit in the air is stunned.'),
    ('Blockstun', 'blockstun', 10, 'Frames the opponent is stuck blocking.'),
    ('Hitstop', 'hitstop', 9, 'Frames both fighters freeze when it connects.'),
    ('Knockdown', 'knockdown', 12, 'On a grounded hit. None, Soft (they can recover) or Hard (they can\'t).'),
    ('Air knockdown', 'air_knockdown', 14, 'On a hit in the air. None, Soft or Hard.'),
    ('Push (hit)', 'push_hit', 11, 'How hard it pushes them away on hit (0 = not at all; 30000 = a normal hit).'),
    ('Push (block)', 'push_block', 12, 'How hard it pushes them away on block.'),
    ('Launch', 'launch', 9, 'Upward speed when it hits a grounded opponent (0 = they stay on the ground).'),
    ('Air launch', 'air_launch', 11, 'Upward speed when it hits an opponent in the air.'),
    ('Meter', 'meter', 8, 'Craft Gauge the fighter gains when it hits (2000 = 1 bar).'),
    ('Scaling', 'scaling', 9, 'How much this hit lowers the damage of the hits after it in a combo (%).'),
    ('Cost', 'cost', 7, 'Craft Gauge bars it costs.'),
    ('Pause', 'pause', 7, 'Frames the fight freezes at its flash (60 = 1 second).'),
    ('Notes', 'notes', 64, 'Anything you like: the game doesn\'t read this column.'),
]
ASSIST_COLUMNS = ([('ID', 'id', 14, MOVE_COLUMNS[0][3]),
                   ('Assist', 'assist', 10, 'The assist.'),
                   ('Call', 'call', 22, 'How you call it (S + direction) and what it is.'),
                   ('Part', 'move', 30, 'Which part of the call this row is.')]
                  + [c for c in MOVE_COLUMNS[3:] if c[1] not in ('cost', 'pause', 'notes')]
                  + [('Cooldown', 'cooldown', 10, 'Frames the assist gauge takes to refill after this call (60 = 1 '
                                                  'second).'),
                     MOVE_COLUMNS[-1]])
NUMBER_KEYS = {'startup', 'active', 'recovery', 'total', 'damage', 'chip', 'hitstun', 'air_hitstun', 'blockstun',
               'hitstop', 'push_hit', 'push_block', 'launch', 'air_launch', 'meter', 'scaling', 'cost', 'pause',
               'cooldown'}
VALUE_KEYS = ['damage', 'chip', 'guard', 'hitstun', 'air_hitstun', 'blockstun', 'hitstop', 'knockdown',
              'air_knockdown', 'push_hit', 'push_block', 'launch', 'air_launch', 'meter', 'scaling']
GROUPS = [('MOVE', 'id', 'hits'), ('FRAMES', 'startup', 'total'), ('ADVANTAGE', 'onhit', 'onblock'),
          ('DAMAGE', 'damage', 'guard'), ('STUN', 'hitstun', 'hitstop'), ('KNOCKDOWN', 'knockdown', 'air_knockdown'),
          ('PUSH & LAUNCH', 'push_hit', 'air_launch'), ('METER', 'meter', 'scaling'), ('SUPER', 'cost', 'pause'),
          ('ASSIST', 'cooldown', 'cooldown'), ('', 'notes', 'notes')]
ASSIST_GROUPS = [('ASSIST', 'id', 'hits')] + GROUPS[1:]
GUARDS = ['High', 'Mid', 'Low', 'Unblockable']
KNOCKDOWNS = ['None', 'Soft', 'Hard', 'No stun', 'Dizzy', 'Stagger', 'Grab']


# --- reading the game's data ----------------------------------------------------------------------------------------

def move_stem(path):
    return os.path.splitext(os.path.basename(path))[0]


def load_command_list(path):
    entries = []
    try:
        d = json.load(open(os.path.join(ROOT, path), encoding='utf-8'))
        for s in d.get('sections', []):
            for m in s.get('moves', []):
                entries.append((m[0].strip(), m[1].strip()))
        # Nov 2 2026: the new format (docs/command_list.md): "moves" keyed by the engine move name; only moves with
        # an "input" note say anything here (the game works the rest out from the move data).
        for name, note in d.get('moves', {}).items():
            if isinstance(note, dict) and note.get('input'):
                entries.append((name.strip(), new_to_old_input(note['input'])))
    except FileNotFoundError:
        pass
    return entries


def new_to_old_input(text):
    """The command list notation ('j. 236 A|B', '214 B+C') -> the old one ('in air: 236 + A / B', '214 + B + C')."""
    t = text.strip().split(' or ')[0].lstrip('> ').strip()
    air = t.startswith('j.')
    t = t[2:].strip() if air else t
    parts = t.split(' ', 1)
    if len(parts) == 2 and parts[0].isdigit():
        dirs, btn = parts
    else:
        dirs, btn = '', t
    btn = btn.strip('[]').replace('|', ' / ').replace('+', ' + ')
    out = (dirs + ' + ' + btn) if dirs else btn
    return ('in air: ' + out) if air else out


def short_input(text, letter=None):
    """'236 + A / B' -> '236A/B'; 'in air: 236 + C (2 bars)' -> 'j.236C'; '214 + B + C (3 bars)' -> '214BC'."""
    t = re.sub(r'\s*\((\d+ bars?|hold[^)]*)\)', '', text).strip()
    air = t.startswith('in air:')
    if air:
        t = t[len('in air:'):].strip()
    m = re.match(r'^(\d+)\s*\+\s*(.+)$', t)
    if m and m.group(2).strip().lower() == 'any':
        t = m.group(1) + ' + any'
    elif m:
        buttons = m.group(2).replace(' ', '')
        if letter and '/' in buttons and letter in buttons.split('/'):
            buttons = letter
        buttons = buttons.replace('+', '')
        t = m.group(1) + buttons
    elif re.match(r'^[ABC](\s*/\s*[ABC])*$', t):
        t = t.replace(' ', '')
    return ('j.' if air else '') + t


def input_for(move, command_list):
    """The Input column for one of the game's moves (MoveSettings)."""
    stem = move_stem(move['path'])
    if stem in INPUT_OVERRIDES:
        return INPUT_OVERRIDES[stem]
    tail = re.sub(r'^\d+_[A-Z]+_', '', stem)
    tail = re.sub(r'^[A-Z]{3}_', '', tail)
    m = re.match(r'^(J|j_)?(\d+)([ABC])$', tail)
    if m:
        notation = m.group(2) + m.group(3)
        if m.group(1):
            return 'j.' + (m.group(3) if m.group(2) == '5' else notation)
        return notation
    if tail == 'Throw':
        return 'B+C'
    if tail == 'Breakthrough':
        return 'A+B (blocking)'
    letter = None
    lm = re.search(r'_([ABC])$', tail)
    if lm:
        letter = lm.group(1)
    elif tail.endswith('_EX') or tail.endswith('EX'):
        letter = 'C'
    name = move['name'].strip()
    found = ''
    norm = lambda s: re.sub(r'[^a-z]', '', s.lower())   # "Crossfire (EX)" is "Crossfire EX"
    exact = [(e, x) for e, x in command_list if norm(e) == norm(name)]
    close = [(e, x) for e, x in command_list if norm(e) != norm(name) and (e.startswith(name) or name.startswith(e))]
    for entry, text in exact + close:
        candidate = short_input(text, letter)
        if letter and letter not in candidate.replace('j.', ''):
            continue   # "Crossfire EX" is the C one: not the "Crossfire 236 + A / B" line
        found = candidate
        break
    if not found and exact + close:
        found = short_input((exact + close)[0][1], letter)
    if found and move.get('air') and not move.get('ground') and not found.startswith('j.'):
        found = 'j.' + found   # the air version of a move done the same way
    return found


def section_of(state):
    moves = state.get('moves', [])
    cost = max([m['cost'] for m in moves] or [0])
    names = {m['name'] for m in moves}
    if names & {'Throw', 'Pushblock'} or state['name'] in ('Throw Break', 'Assist Call'):
        return 'THROWS & SYSTEM'
    if cost >= 6000:
        return 'SUPERS'
    if cost >= 2000:   # Oct 28: EX moves cost 1 bar (Pushblock, also 2000, is caught above)
        return 'EX MOVES'
    stems = [re.sub(r'^\d+_[A-Z]+_', '', move_stem(m['path'])) for m in moves]
    if any(re.match(r'^(j_)?[2456][ABC]$', s) for s in stems):
        return 'NORMALS'
    return 'SPECIALS'


SECTION_ORDER = ['NORMALS', 'SPECIALS', 'EX MOVES', 'SUPERS', 'THROWS & SYSTEM']

# Oct 28: the engine sets the on-block advantage of every GROUND normal itself (StanceManager.NetsuBlockAdvantage,
# applied in SakugaActor when the block happens): the hitbox's Blockstun is replaced so the attacker is at exactly
# this many frames, whatever the move's length. Keep in step with the engine. Air normals keep their own numbers.
NORMAL_BLOCK_ADV = {'A': -4, 'B': -5, 'C': -8}


def ground_normal_strength(state):
    """'A' / 'B' / 'C' for a ground normal's own row (5A, 2B, 4A, 6C...), None otherwise."""
    for m in state.get('moves', []):
        stem = re.sub(r'^\d+_[A-Z]+_', '', move_stem(m['path']))
        hit = re.match(r'^[2456]([ABC])$', stem)
        if hit:
            return hit.group(1)
    return None


def row_of(state, depth, name, call_input, pronoun='she'):
    """One sheet row: its shown values and which cells can be changed."""
    atk = state['attack']
    box = state.get('box')
    hitlike = box in ('HITBOX', 'PROJECTILE')
    first, last, dur = state['first'], state['last'], state['duration']
    cap = state['landing'] and dur >= 60   # the state's length is only a cap: it ends when they land
    r = dict(id=state['index'], move=('    ' * depth + ('> ' if depth else '') + name), input=call_input,
             hits=state['hits'] if atk else None, edit=set(), notes=[], state=state, depth=depth)
    if atk:
        r['startup'] = first + 1
        if first > 0:
            r['edit'].add('startup')
        if cap and last == dur - 1:
            r['active'] = 'until landing'
        else:
            r['active'] = last - first + 1
            r['edit'].add('active')
        if cap:
            r['recovery'] = 'landing'
        else:
            r['recovery'] = dur - last - 1
            if dur - last - 1 > 0:
                r['edit'].add('recovery')
        r['total'] = 'landing' if cap else '=formula'
    else:
        r['total'] = 'landing' if cap else dur
        if not cap:
            r['edit'].add('total')
    if hitlike:
        for k in VALUE_KEYS:
            r[k] = state[k]
            r['edit'].add(k)
        if not cap:
            r['onhit'] = '=formula'
            r['onblock'] = '=formula'
    moves = state.get('moves', [])
    cost = max([m['cost'] for m in moves] or [0])
    if cost > 0:
        r['cost'] = round(cost / 2000.0, 2)
        if r['cost'] == int(r['cost']):
            r['cost'] = int(r['cost'])
        r['edit'].add('cost')
    if cost >= 2000 and not ({m['name'] for m in moves} & {'Pushblock'}):   # Oct 28: EX = 1 bar
        r['pause'] = moves[0]['pause']
        r['edit'].add('pause')
    # notes
    if atk and state['hits'] > 1 and hitlike:
        r['notes'].append('%d hits: the row shows the first, a change goes to every hit' % state['hits'])
    if cap:
        r['notes'].append('Ends when %s lands' % pronoun)
    if box == 'COUNTER':
        r['notes'].append('Counter stance: catches attacks during its active frames')
    if box == 'THROW':
        r['notes'].append('Throw: grabs during its active frames')
    if not atk and not cap:
        r['notes'].append('No hitbox: Total is how long this part lasts')
    if atk and first == 0:
        r['notes'].append('Hits from its first frame (start-up comes from the part before)')
    return r


def fighter_rows(dump, command_list):
    states = {s['index']: s for s in dump['states']}
    combat = [s for s in dump['states'] if s['type'] == 2]
    by_section = {k: [] for k in SECTION_ORDER}
    placed = set()
    followers = {}   # state -> move states done from it (rekka follow-ups)
    for s in combat:
        for m in s.get('moves', []):
            for f in m.get('from', []):
                followers.setdefault(f, [])
                if s['index'] not in followers[f]:
                    followers[f].append(s['index'])

    def name_of(s):
        moves = s.get('moves', [])
        return moves[0]['name'] if moves else s['name']

    def input_of(s):
        parts = []
        for m in s.get('moves', []):
            i = input_for(m, command_list)
            if i and i not in parts:
                parts.append(i)
        return ' / '.join(parts)

    def add(s, depth, out):
        if s['index'] in placed:
            return
        placed.add(s['index'])
        out.append(row_of(s, depth, name_of(s), input_of(s)))
        for t in sorted(s['targets']) + followers.get(s['index'], []):
            st = states.get(t)
            if st is None or st['type'] != 2 or st['index'] in placed:
                continue
            if st.get('moves') and t not in followers.get(s['index'], []):
                continue   # a move of its own: listed in its own place
            add(st, depth + 1, out)

    # moves done from another move (rekka follow-ups) are listed under it
    sequence = {i for v in followers.values() for i in v}
    for s in combat:
        if s.get('moves') and s['index'] not in sequence:
            add(s, 0, by_section[section_of(s)])
    for r in by_section['NORMALS']:
        strength = ground_normal_strength(r['state']) if r['depth'] == 0 else None
        if strength and r.get('onblock') == '=formula':
            r['table_block'] = NORMAL_BLOCK_ADV[strength]
            r['notes'].append('On block is set by the engine (A -4, B -5, C -8 for every ground normal); '
                              'Blockstun here does nothing on the ground')
    for s in combat:
        if s['index'] not in placed:
            add(s, 0, by_section['THROWS & SYSTEM'])
    return by_section


def shared_animation_notes(rows):
    by_anim = {}
    for r in rows:
        by_anim.setdefault(r['state'].get('animation', ''), []).append(r)
    for anim, rs in by_anim.items():
        if anim and len(rs) > 1:
            for r in rs:
                others = ', '.join(str(o['id']) for o in rs if o is not r)
                r['notes'].append('Shares its frames with ID %s: a timing change moves both' % others)


# --- writing the workbook ---------------------------------------------------------------------------------------------

def write_table(ws, columns, groups, sections, title, subtitle, group_rows_label=None):
    """The Moves / Assists sheet. Returns (rows by line number, column letters by key)."""
    letters = {key: get_column_letter(i + 1) for i, (_, key, _, _) in enumerate(columns)}
    ncol = len(columns)
    for i, (_, key, width, _) in enumerate(columns):
        ws.column_dimensions[get_column_letter(i + 1)].width = width
    ws['A1'] = title
    ws['A1'].font = font(size=16, bold=True, color=NAVY)
    ws['A2'] = subtitle
    ws['A2'].font = font(size=10, color=GREY_TEXT)
    ws['A3'] = ('White cells: change them, then save.   Grey cells: worked out, or not changeable here.   '
                'Yellow: a cell you changed.   Hover over a heading to see what it means.')
    ws['A3'].font = font(size=10, italic=True, color=INK)
    # group band (row 4) and headings (row 5)
    keys = [c[1] for c in columns]
    for label, a, b in groups:
        if a not in keys or b not in keys:
            continue
        ca, cb = keys.index(a) + 1, keys.index(b) + 1
        for c in range(ca, cb + 1):
            cell = ws.cell(row=4, column=c)
            cell.fill = GROUP_FILL
        cell = ws.cell(row=4, column=ca, value=label)
        cell.font = font(size=9, bold=True, color='FFFFFF')
        cell.alignment = Alignment(horizontal='left', vertical='center', indent=0)
    for i, (head, key, _, help_text) in enumerate(columns):
        cell = ws.cell(row=5, column=i + 1, value=head)
        cell.font = font(bold=True, color='FFFFFF')
        cell.fill = HEAD_FILL
        cell.alignment = Alignment(horizontal='center' if key not in ('move', 'notes', 'call') else 'left',
                                   vertical='center', wrap_text=True)
        cell.border = BORDER
        comment = Comment(help_text, 'Netsu VS')
        comment.width = 260
        comment.height = 90
        cell.comment = comment
    ws.row_dimensions[5].height = 30
    line = 6
    placed = []
    for section, rows in sections:
        if not rows:
            continue
        for c in range(1, ncol + 1):
            ws.cell(row=line, column=c).fill = SECTION_FILL
        cell = ws.cell(row=line, column=2, value=section)
        cell.font = font(bold=True, color=NAVY)
        line += 1
        for r in rows:
            placed.append((line, r))
            line += 1
    return placed, letters, line - 1


def fill_rows(ws, placed, letters, columns):
    """Values, formulas, looks."""
    L = letters
    for line, r in placed:
        for i, (_, key, _, _) in enumerate(columns):
            col = i + 1
            cell = ws.cell(row=line, column=col)
            value = r.get(key)
            if key == 'notes':
                value = '; '.join(r['notes']) if r['notes'] else None
            shown = value
            if value == '=formula':
                if key == 'total':
                    value = '=%s%d-1+%s%d+%s%d' % (L['startup'], line, L['active'], line, L['recovery'], line)
                    shown = r['startup'] - 1 + r['active'] + r['recovery']
                elif key == 'onblock' and r.get('table_block') is not None:
                    value = shown = r['table_block']   # Oct 28: set by the engine (NORMAL_BLOCK_ADV)
                elif key == 'onblock':
                    value = '=%s%d-%s%d-%s%d' % (L['blockstun'], line, L['active'], line, L['recovery'], line)
                    shown = r['blockstun'] - r['active'] - r['recovery']
                elif key == 'onhit':
                    kd = '%s%d' % (L['knockdown'], line)
                    value = '=IF(OR(%s="Soft",%s="Hard"),"KD",IF(%s%d>0,"launch",%s%d-%s%d-%s%d))' % (
                        kd, kd, L['launch'], line, L['hitstun'], line, L['active'], line, L['recovery'], line)
                    if r['knockdown'] in ('Soft', 'Hard'):
                        shown = 'KD'
                    elif r['launch'] > 0:
                        shown = 'launch'
                    else:
                        shown = r['hitstun'] - r['active'] - r['recovery']
            cell.value = value
            editable = key in r['edit']
            if key in ('id',):
                cell.font = font(color=GREY_TEXT, size=9)
                cell.alignment = Alignment(horizontal='center')
            elif key in ('move', 'call', 'assist'):
                cell.font = font(bold=(r['depth'] == 0 and key == 'move'))
            elif key == 'notes':
                cell.font = font(color=GREY_TEXT, size=9)
            else:
                cell.alignment = Alignment(horizontal='center')
                cell.font = font(color=INK if editable else GREY_TEXT, bold=editable)
            if key not in ('notes',):
                cell.fill = EDIT_FILL if editable else GREY_FILL
                cell.border = BORDER


def plain(r, key):
    """What a cell shows (a formula's result worked out here)."""
    v = r.get(key)
    if v != '=formula':
        return v
    if key == 'onblock' and r.get('table_block') is not None:
        return r['table_block']
    if key == 'total':
        return r['startup'] - 1 + r['active'] + r['recovery']
    if key == 'onblock':
        return r['blockstun'] - r['active'] - r['recovery']
    if key == 'onhit':
        if r['knockdown'] in ('Soft', 'Hard'):
            return 'KD'
        if r['launch'] > 0:
            return 'launch'
        return r['hitstun'] - r['active'] - r['recovery']
    return None


def fill_original(original, placed, columns, letters):
    """The hidden Original sheet: every cell's value as the sheet starts (the yellow "you changed this" compares to
    it). Same rows and columns as the main sheet."""
    for line, r in placed:
        for i, (_, key, _, _) in enumerate(columns):
            if key in ('notes',):
                continue
            original.cell(row=line, column=i + 1, value=plain(r, key))
    original.sheet_view.showGridLines = True


def add_rules(ws, letters, columns, first, last):
    keys = [c[1] for c in columns]
    a = letters['startup']
    b = get_column_letter(keys.index('notes'))   # the column before Notes
    rng = '%s%d:%s%d' % (a, first, b, last)
    formula = '%s%d<>INDIRECT("Original!"&ADDRESS(ROW(%s%d),COLUMN(%s%d)))' % (a, first, a, first, a, first)
    ws.conditional_formatting.add(rng, FormulaRule(formula=[formula], fill=CHANGED_FILL, stopIfTrue=False))
    for key in ('onblock', 'onhit'):
        col = letters[key]
        r = '%s%d:%s%d' % (col, first, col, last)
        ws.conditional_formatting.add(r, CellIsRule(operator='lessThan', formula=['0'], font=Font(name=FONT,
                                      color='C0392B', bold=True)))
        ws.conditional_formatting.add(r, CellIsRule(operator='greaterThanOrEqual', formula=['0'],
                                      font=Font(name=FONT, color='1E8449', bold=True)))


def add_lists(ws, placed, letters):
    guard = DataValidation(type='list', formula1='"%s"' % ','.join(GUARDS), allow_blank=True)
    kd = DataValidation(type='list', formula1='"%s"' % ','.join(KNOCKDOWNS), allow_blank=True)
    guard.error = 'Guard is High, Mid, Low or Unblockable.'
    kd.error = 'Knockdown is None, Soft or Hard (or No stun, Dizzy, Stagger, Grab).'
    for v in (guard, kd):
        v.showErrorMessage = True
        ws.add_data_validation(v)
    for line, r in placed:
        if 'guard' in r['edit']:
            guard.add('%s%d' % (letters['guard'], line))
        for k in ('knockdown', 'air_knockdown'):
            if k in r['edit']:
                kd.add('%s%d' % (letters[k], line))


def how_to_sheet(wb, who, assists=False):
    ws = wb.create_sheet('How to use')
    ws.column_dimensions['A'].width = 3
    ws.column_dimensions['B'].width = 120
    lines = [
        ('h', 'How these spreadsheets work'),
        ('p', 'Each fighter has a workbook in data/frame_data (Cecilia.xlsx, Flan.xlsx, Leticia.xlsx, Noah.xlsx); the assists '
              'share Assists.xlsx. One row per move. Change a white cell, save the file (keep the name and the .xlsx '
              'format), and the game uses the new number.'),
        ('p', 'When: at the start of every match. In Training it happens the moment you save: a FRAME DATA UPDATED '
              'note under the timer lists what changed. (In Godot, run the game as usual: nothing to build.)'),
        ('p', 'Only the cells you change are used. Everything else keeps the game\'s own values, so moves that are '
              'updated in the game later still get their new numbers unless you changed that cell. Cells you '
              'changed turn yellow.'),
        ('p', 'To undo a change, type the old number back (the yellow goes away), or delete the cell\'s contents.'),
        ('h', 'The frames'),
        ('p', 'Startup = the frame the first hitbox appears on, counting the move\'s first frame as 1. Active = frames '
              'from the first hitbox to the last. Recovery = frames after the last hitbox until the fighter can act. '
              'Total = Startup - 1 + Active + Recovery.'),
        ('p', 'Changing them re-times the whole move to fit: its pictures, hitboxes, sounds, effects, movement, cancel '
              'windows and follow-up timings all slide along with the part of the move they belong to. Moves that '
              'travel go less far when their start-up gets shorter.'),
        ('p', 'Inputs are in numpad notation, facing right: 6 = forward, 4 = back, 2 = down, 236 = quarter circle '
              'forward; j. = in the air.'),
        ('p', 'Rows marked "landing" end when the fighter lands, not after a set number of frames: their landing is '
              'its own row (for example "Skyfall Slash (landing)"), with a Total you can change.'),
        ('p', 'Parts with no hitbox (the dash before a slash, a landing) only have a Total: how long that part lasts.'),
        ('h', 'The hit'),
        ('p', 'A move with several hits shows its first hit. A change goes to every hit: Damage, Chip, Push, Launch '
              'and Meter by the same percentage; Hitstun, Blockstun, Hitstop and Scaling by the same number of frames. '
              'For example, a 5-hit super doing 450 per hit set to 500 makes every hit about 11% stronger.'),
        ('p', 'On hit / On block = the frame advantage Training shows when the move\'s FIRST active frame connects. '
              'Hitting later in the active frames is better by that many frames. They update by themselves: '
              'On block = Blockstun - Active - Recovery. KD = it knocks down; "launch" = they go into the air. '
              'Ground normals are the exception: the engine sets their On block itself (A -4, B -5, C -8) and '
              'ignores their Blockstun on the ground.'),
        ('p', 'Guard: High = must be blocked standing (an overhead), Mid = either way, Low = must be blocked '
              'crouching, Unblockable. Knockdown: None, Soft (they can recover) or Hard (they can\'t).'),
        ('p', 'Push: how hard the hit or the block pushes them away (30000 is a normal hit, 0 = no push). Launch: '
              'upward speed on a grounded hit (0 = they stay on the ground). Air launch: upward speed when they\'re '
              'hit in the air. Meter: Craft Gauge gained on hit (2000 = 1 bar). Scaling: how much this hit lowers '
              'the damage of the hits after it in a combo.'),
        ('p', 'Cost: bars of Craft Gauge (EX moves 2, supers 3). Moves costing 2 bars or more flash and stop the '
              'fight for Pause frames (EX 30, supers 60 = 1 second).'),
    ]
    if not assists:
        lines.append(('p', 'The Fighter sheet has her Health, Attack and Defense (100 = normal). These three count from '
                           'the next match (in Training too: go back to the character select).'))
    else:
        lines.append(('p', 'Cooldown: frames the assist gauge takes to refill after that call (60 = 1 second). An '
                           'assist\'s call is often several parts in a row (it runs in, then attacks): each part is '
                           'its own row.'))
    lines += [
        ('h', 'Good to know'),
        ('p', 'Online, both players need the same spreadsheets: two different ones can\'t connect ("different frame '
              'data").'),
        ('p', 'A cell the game can\'t use (letters in a number cell, an impossible value like 0 active frames) is '
              'skipped; Training\'s note and Godot\'s Output panel say which one.'),
        ('p', 'Don\'t rename the sheets, the headings or the ID column: the game finds everything by them. You can '
              'add notes in the Notes column, colour cells, sort rows, or add columns of your own.'),
        ('p', 'The hidden "Original" sheet keeps the values the sheet started with (that\'s what the yellow compares '
              'to). Unhide it if you want to look at them.'),
        ('p', 'Made %s from the game\'s data.' % datetime.date.today().isoformat()),
    ]
    row = 2
    for kind, text in lines:
        cell = ws.cell(row=row, column=2, value=text)
        if kind == 'h':
            cell.font = font(size=13, bold=True, color=NAVY)
            row += 1
        else:
            cell.font = font(size=10)
            cell.alignment = Alignment(wrap_text=True, vertical='top')
            ws.row_dimensions[row].height = 15 * max(1, (len(text) // 135) + 1)
            row += 1
        if kind == 'p':
            row += 0
    ws.sheet_view.showGridLines = False
    return ws


def fighter_sheet(wb, dump):
    ws = wb.create_sheet('Fighter')
    ws.column_dimensions['A'].width = 10
    ws.column_dimensions['B'].width = 16
    ws.column_dimensions['C'].width = 10
    ws.column_dimensions['D'].width = 70
    heads = ['ID', 'Setting', 'Value', 'What it does']
    for i, h in enumerate(heads):
        c = ws.cell(row=1, column=i + 1, value=h)
        c.font = font(bold=True, color='FFFFFF')
        c.fill = HEAD_FILL
        c.border = BORDER
    items = [('Health', 'Health', dump['health'], 'The fighter\'s health (10000 = normal).'),
             ('Attack', 'Attack', dump['attack'], 'How hard the fighter\'s hits land, in % (100 = normal).'),
             ('Defense', 'Defense', dump['defense'], 'How well the fighter takes hits, in % (100 = normal).')]
    baseline = {}
    for r, (key, label, value, what) in enumerate(items, start=2):
        ws.cell(row=r, column=1, value=key).font = font(color=GREY_TEXT, size=9)
        ws.cell(row=r, column=2, value=label).font = font(bold=True)
        v = ws.cell(row=r, column=3, value=value)
        v.font = font(bold=True)
        v.alignment = Alignment(horizontal='center')
        ws.cell(row=r, column=4, value=what).font = font(color=GREY_TEXT, size=9)
        for c in range(1, 5):
            ws.cell(row=r, column=c).border = BORDER
        baseline[key] = {'Value': value}
    return baseline


def baseline_of(placed, columns):
    """The cells the game compares: every changeable cell's value now."""
    heads = {key: head for head, key, _, _ in columns}
    out = {}
    for _, r in placed:
        cells = {}
        for key in sorted(r['edit']):
            v = r.get(key)
            if v is None:
                continue
            cells[heads[key]] = v
        if cells:
            out[str(r['id'])] = cells
    return out


def carry_edits(placed, columns, old_cells):
    """--keep: the user's changed cells (by ID and heading) go into the new rows."""
    heads = {head: key for head, key, _, _ in columns}
    n = 0
    for _, r in placed:
        changed = old_cells.get(str(r['id']), {})
        for head, value in changed.items():
            key = heads.get(head)
            if key in r['edit']:
                r[key] = value
                n += 1
    return n


def old_edits(old_dir, file, sheet, old_manifest):
    """{row ID: {heading: value}} for the cells the user changed in their copy of the sheet."""
    path = os.path.join(old_dir, file)
    entry = next((f for f in old_manifest.get('files', []) if f['file'] == file), None)
    if not os.path.exists(path) or entry is None:
        return {}
    base = entry.get('baseline', {}).get(sheet, {})
    wb = load_workbook(path, data_only=True)
    if sheet not in wb.sheetnames:
        return {}
    ws = wb[sheet]
    head_row, id_col, cols = None, None, {}
    for row in ws.iter_rows(min_row=1, max_row=20):
        for c in row:
            if c.value is not None and str(c.value).strip() == 'ID':
                head_row, id_col = c.row, c.column
                break
        if head_row:
            break
    if not head_row:
        return {}
    for c in ws[head_row]:
        if c.value is not None:
            cols[str(c.value).strip()] = c.column
    out = {}
    for row in ws.iter_rows(min_row=head_row + 1):
        idv = row[id_col - 1].value
        if idv is None:
            continue
        rid = str(int(idv)) if isinstance(idv, float) and idv == int(idv) else str(idv).strip()
        for head, was in base.get(rid, {}).items():
            if head not in cols:
                continue
            v = ws.cell(row=row[0].row, column=cols[head]).value
            if v is None or str(v).strip() == '':
                continue
            if isinstance(was, (int, float)):
                try:
                    if abs(float(v) - float(was)) < 1e-6:
                        continue
                except ValueError:
                    pass
            elif str(v).strip().lower() == str(was).strip().lower():
                continue
            out.setdefault(rid, {})[head] = v
    return out


def build_fighter(spec, dump_dir, old_dir, old_manifest):
    dump = json.load(open(os.path.join(dump_dir, spec['dump']), encoding='utf-8'))
    cmd = load_command_list(spec['cmd'])
    by_section = fighter_rows(dump, cmd)
    all_rows = [r for s in SECTION_ORDER for r in by_section[s]]
    shared_animation_notes(all_rows)
    wb = Workbook()
    ws = wb.active
    ws.title = 'Moves'
    full = cmd_fighter_name(spec)
    placed, letters, last = write_table(ws, MOVE_COLUMNS, GROUPS, [(s, by_section[s]) for s in SECTION_ORDER],
                                        '%s - frame data' % full,
                                        'Netsu VS. Change the white cells and save: the game uses them at the next '
                                        'match (in Training, right away). See "How to use".')
    baseline = baseline_of(placed, MOVE_COLUMNS)   # the game's own values, before any carried-over change
    original = wb.create_sheet('Original')
    fill_original(original, placed, MOVE_COLUMNS, letters)
    carried = 0
    if old_dir:
        carried = carry_edits(placed, MOVE_COLUMNS, old_edits(old_dir, spec['file'], 'Moves', old_manifest))
    fill_rows(ws, placed, letters, MOVE_COLUMNS)
    add_rules(ws, letters, MOVE_COLUMNS, 6, last)
    add_lists(ws, placed, letters)
    ws.freeze_panes = 'E6'
    fighter_base = fighter_sheet(wb, dump)
    if old_dir:
        old = old_edits(old_dir, spec['file'], 'Fighter', old_manifest)
        fs = wb['Fighter']
        for r in range(2, 5):
            key = fs.cell(row=r, column=1).value
            if key in old and 'Value' in old[key]:
                fs.cell(row=r, column=3, value=old[key]['Value'])
                carried += 1
    how_to_sheet(wb, full)
    _finish(wb, ['Moves', 'Fighter', 'How to use', 'Original'])
    wb.save(os.path.join(OUT, spec['file']))
    entry = dict(file=spec['file'], kind='fighter', name=spec['name'], data=spec['data'],
                 baseline={'Moves': baseline, 'Fighter': fighter_base})
    return entry, len(placed), carried


def cmd_fighter_name(spec):
    try:
        return json.load(open(os.path.join(ROOT, spec['cmd']), encoding='utf-8')).get('fighter', spec['name'])
    except FileNotFoundError:
        return spec['name']


def build_assists(dump_dir, old_dir, old_manifest):
    alist = json.load(open(os.path.join(dump_dir, 'assist_list.json'), encoding='utf-8'))
    sections = []
    manifest_assists = {}
    for a in alist:
        name = a['name']
        stem = move_stem(a['data'])
        dump = json.load(open(os.path.join(dump_dir, stem + '.json'), encoding='utf-8'))
        manifest_assists[name] = a['data']
        states = {s['index']: s for s in dump['states']}
        rows = []
        placed = set()

        def chain(s, depth, call, first_row, prefix, states_map, cooldown=None):
            if s['index'] in placed_key(prefix):
                return
            placed_key(prefix).add(s['index'])
            r = row_of(s, depth, s['name'], '', pronoun='the assist')
            r['id'] = '%s:%d' % (prefix, s['index'])
            r['assist'] = prefix if first_row else ''
            r['call'] = call if first_row else ''
            if cooldown is not None:
                r['cooldown'] = cooldown
                r['edit'].add('cooldown')
            r.pop('cost', None)
            r.pop('pause', None)
            r['edit'].discard('cost')
            r['edit'].discard('pause')
            rows.append(r)
            for t in s['targets']:
                st = states_map.get(t)
                if st is not None and st['type'] == 2:
                    chain(st, depth + 1, call, False, prefix, states_map)

        placed_sets = {}

        def placed_key(prefix):
            return placed_sets.setdefault(prefix, set())

        for m in a['moves']:
            st = states.get(m['state'])
            if st is None:
                continue
            call = '%s  %s' % (m['move'], m['name'])
            chain(st, 0, call, True, name, states, cooldown=m['cooldown'])
        for part, data_path, dump_file, call in ASSIST_PARTS.get(name, []):
            manifest_assists[part] = data_path
            pdump = json.load(open(os.path.join(dump_dir, dump_file), encoding='utf-8'))
            pstates = {s['index']: s for s in pdump['states']}
            for s in pdump['states']:
                if s['type'] == 2 and s['index'] not in placed_key(part):
                    roots = [x for x in pdump['states'] if s['index'] in x['targets']]
                    if roots:
                        continue   # reached from another part: listed under it
                    chain(s, 0, call, True, part, pstates)
        shared_animation_notes(rows)
        sections.append(('%s' % name.upper(), rows))
    wb = Workbook()
    ws = wb.active
    ws.title = 'Assists'
    placed, letters, last = write_table(ws, ASSIST_COLUMNS, ASSIST_GROUPS, sections, 'Assists - frame data',
                                        'Netsu VS. Change the white cells and save: the game uses them at the next '
                                        'match (in Training, right away). See "How to use".')
    baseline = baseline_of(placed, ASSIST_COLUMNS)
    original = wb.create_sheet('Original')
    fill_original(original, placed, ASSIST_COLUMNS, letters)
    carried = 0
    if old_dir:
        carried = carry_edits(placed, ASSIST_COLUMNS, old_edits(old_dir, 'Assists.xlsx', 'Assists', old_manifest))
    fill_rows(ws, placed, letters, ASSIST_COLUMNS)
    add_rules(ws, letters, ASSIST_COLUMNS, 6, last)
    add_lists(ws, placed, letters)
    ws.freeze_panes = 'F6'
    how_to_sheet(wb, 'Assists', assists=True)
    _finish(wb, ['Assists', 'How to use', 'Original'])
    wb.save(os.path.join(OUT, 'Assists.xlsx'))
    entry = dict(file='Assists.xlsx', kind='assists', name='Assists', assists=manifest_assists,
                 baseline={'Assists': baseline})
    return entry, len(placed), carried


def _finish(wb, order):
    wb._sheets = [wb[name] for name in order]
    for ws in wb.worksheets:   # printing: landscape, as wide as the page
        ws.page_setup.orientation = 'landscape'
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        ws.print_options.gridLines = False
    for name in order[:1]:
        wb[name].print_title_rows = '4:5'
    wb.active = 0
    wb['Original'].sheet_state = 'hidden'
    for ws in wb.worksheets:
        ws.sheet_view.tabSelected = ws.title == order[0]
    wb.calculation.fullCalcOnLoad = True


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('dump', help='folder with the --rt-fddump JSON files')
    ap.add_argument('--keep', help='a copy of data/frame_data as the user has it: carry their changes over')
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    old_manifest = {}
    if args.keep:
        p = os.path.join(args.keep, 'frame_data.json')
        if os.path.exists(p):
            old_manifest = json.load(open(p, encoding='utf-8'))
    files = []
    for spec in FIGHTERS:
        entry, n, carried = build_fighter(spec, args.dump, args.keep, old_manifest)
        files.append(entry)
        print('%-14s %3d rows, %d changes carried over' % (spec['file'], n, carried))
    entry, n, carried = build_assists(args.dump, args.keep, old_manifest)
    files.append(entry)
    print('%-14s %3d rows, %d changes carried over' % ('Assists.xlsx', n, carried))
    manifest = {
        'version': 1,
        'made': datetime.date.today().isoformat(),
        'note': 'Made by tools/frame_data/make_sheets.py. What every changeable cell said when the sheets were made: '
                'the game (engine/sakuga/Game/NetsuFrameData.cs) only uses cells that say something else now.',
        'files': files,
    }
    with open(os.path.join(OUT, 'frame_data.json'), 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=1, ensure_ascii=False)
        f.write('\n')


if __name__ == '__main__':
    main()
