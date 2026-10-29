"""Builds Leticia's CPU (AI) files for all six difficulties.

    python tools/ai/build_leticia_ai.py        (run from the project folder)

Writes actors/leticia/AI/LET_AIData.tres (her action list) and LET_AI_Beginner / Easy / Normal / Hard /
VeryHard / Pro.tres (one behaviour per difficulty). The files keep their uids, so nothing that points at them
breaks. How the engine reads these, and the difficulty levels every fighter shares (speed, reactions,
guarding...): tools/ai/ai_common.py.

Her plan (a zoner with twin guns and a hover board, from tools/sprite_port/moves_leticia.py): keep them out with
Photon Line (214A, a beam across the screen) and Ricochet Prism (214B, for jumpers and far away), Crossfire
(236A/B) from mid range, back off when they get close, anti-air with Rising Comet (623B), punish whiffs with a
Photon Line from anywhere, and cash meter into Crossfire EX or Stardrive Cannon (236BC).
Distances: 10000 = 1 metre.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ai_common import *

# name, inputs [(direction, buttons)], auto_advance, start_delay
ACTIONS = [
    ("Walk Forward",        [(F, 0)], False, 0),                              # 0
    ("Walk Back / Guard",   [(B, 0)], False, 0),                              # 1
    ("Dash Forward",        [(F, 0), (N, 0), (F, 0)], True, 0),               # 2   (after a shot: the shot dash)
    ("Back Dash",           [(B, 0), (N, 0), (B, 0), (N, 0)], True, 0),       # 3
    ("Jump Neutral",        [(U, 0), (N, 0)], True, 0),                       # 4
    ("Jump Forward",        [(U | F, 0), (N, 0)], True, 0),                   # 5
    ("Jump Back",           [(U | B, 0), (N, 0)], True, 0),                   # 6
    ("Crouch",              [(D, 0)], False, 0),                              # 7
    ("Crouch Guard",        [(D | B, 0)], False, 0),                          # 8
    ("A",                   [(N, BA), (N, 0)], False, 0),                     # 9   5A / j.A
    ("B",                   [(N, BB), (N, 0)], False, 0),                     # 10  5B / j.B
    ("C",                   [(N, BC), (N, 0)], False, 0),                     # 11  5C / j.C
    ("2A",                  [(D, BA), (N, 0)], False, 0),                     # 12
    ("2B",                  [(D, BB), (N, 0)], False, 0),                     # 13
    ("2C",                  [(D, BC), (N, 0)], False, 0),                     # 14
    ("Tech / Recover",      [(N, BA), (N, 0)], False, 0),                     # 15
    ("236C Crossfire EX",   [(D, 0), (D | F, 0), (F, BC), (N, 0)], False, 0),            # 16  (4000) all three shots
    ("236B Crossfire",      [(D, 0), (D | F, 0), (F, BB), (N, 0)], False, 0),            # 17
    ("236A Crossfire",      [(D, 0), (D | F, 0), (F, BA), (N, 0)], False, 0),            # 18
    ("623C Comet Burst",    [(F, 0), (D, 0), (D | F, BC), (N, 0)], False, 0),            # 19  (4000) invincible
    ("214C Prism Overdrive", [(D, 0), (D | B, 0), (B, BC), (N, 0)], False, 0),           # 20  (4000)
    ("236BC Stardrive Cannon", [(D, 0), (D | F, 0), (F, 0), (N, BB | BC), (N, 0)], False, 0),   # 21 (6000) big beam
    ("6B Crossfire follow-up", [(F, BB), (N, 0)], False, 0),                             # 22  (after 236A/B, twice)
    ("Wait",                [(N, 0)], True, 10),                              # 23  short pause (timing)
    ("Jump-in B (late)",    [(N, BB), (N, 0)], False, 14),                    # 24
    ("Jump-in C (late)",    [(N, BC), (N, 0)], False, 14),                    # 25
    ("2B after landing",    [(D, BB), (N, 0)], False, 10),                    # 26
    ("623B Rising Comet",   [(F, 0), (D, 0), (D | F, BB), (N, 0)], False, 0),            # 27  invincible start: anti-air
    ("2A after dash",       [(D, BA), (N, 0)], False, 6),                     # 28
    ("214BC Crimson Waltz", [(D, 0), (D | B, 0), (B, 0), (N, BB | BC), (N, 0)], False, 0),   # 29 (6000) board rush super
    ("214A Photon Line",    [(D, 0), (D | B, 0), (B, BA), (N, 0)], False, 0),            # 30  straight beam
    ("623A Rising Comet",   [(F, 0), (D, 0), (D | F, BA), (N, 0)], False, 0),            # 31
    ("214B Ricochet Prism", [(D, 0), (D | B, 0), (B, BB), (N, 0)], False, 0),            # 32  up-shot that bounces
    ("j.236B Flux Dive",    [(D, 0), (D | F, 0), (F, BB), (N, 0)], False, 8),            # 33  in the air, after a jump
]
X = add_common_actions(ACTIONS)            # throw, back_throw, dash_throw, wait_long, wait_short
THROW, BACK_THROW, DASH_THROW_A, WAIT_LONG = X["throw"], X["back_throw"], X["dash_throw"], X["wait_long"]

# Combos and plans (lists of action numbers)
BNB = [9, 10, 13, 17]                     # 5A > 5B > 2B > 236B (the 6B follow-ups don't reach after a long string)
LOW_BNB = [12, 13, 17]                    # 2A > 2B > 236B
REKKA = [17, 22, 22]                      # 236B > 6B > 6B: the whole Crossfire (point blank: a punish)
SHORT = [9, 10]                           # 5A > 5B
LOW_SHORT = [12, 13]                      # 2A > 2B
METER_BNB = [9, 10, 13, 16]               # ... > 236C Crossfire EX (4000)
SUPER_BNB = [9, 10, 13, 21]               # ... > 236BC Stardrive Cannon (6000)
LINE = [30]                               # 214A Photon Line
PRISM = [32]                              # 214B Ricochet Prism (jumpers / far ground)
LINE_SUPER = [21]                         # 236BC Stardrive Cannon from anywhere (6000)
SHOT_DASH = [18, 2, 28, 13]               # 236A > shot dash > 2A > 2B: zone in behind the shot
FRAME_TRAP = [12, 23, 12, 13]             # 2A, pause, 2A > 2B
DASH_IN = [2, 28, 13, 17]                 # dash > 2A > 2B > 236B
DASH_THROW = [2, DASH_THROW_A]            # dash > throw
JUMP_IN = [5, 24, 26]                     # jump in > late j.B > land 2B
JUMP_IN_C = [5, 25, 26]                   # same with j.C
FLUX_IN = [5, 33]                         # jump in > j.236B Flux Dive
MEATY = [23, 12, 13, 17]                  # wait for wake-up > 2A > 2B > 236B
TICK_THROW = [WAIT_LONG, THROW]           # (they're blocking) let blockstun end > throw
KEEP_OUT = [3]                            # back dash away when they get close
JUMP_BACK_SHOT = [6, 24]                  # jump back > j.B (shoots both ways)
AIR_TO_AIR = [4, 9]                       # neutral jump > j.A
ANTI_AIR = [27]                           # 623B Rising Comet (invincible start)
ANTI_AIR_EX = [19]                        # 623C Comet Burst (4000)
AA_T, AA_EX_T, A2A_T = 4, 0, 10           # anti-air start-ups: frames from the press to the hit (the EX's flash freezes them first)
RUSH_SUPER = [29]                         # 214BC Crimson Waltz: board rush (6000)
WAKEUP = [27]                             # wake-up reversal: 623B

BEHAVIOURS = {
    "Beginner": dict(
        near=[c(NEAR, [9]), c(NEAR, [12], 4), c(NEAR, [10], 3), c(NEAR, [1], 3, DEF), c(NEAR, [4], 2), c(NEAR, [23], 3),
              react(AA, AIR_TO_AIR, AIR, startup=A2A_T)],
        mid=[c(MID2, [0]), c(MID2, [18], 2), c(MID2, [23], 3), c(MID2, [1], 3, DEF), c(MID2, [5], 2)],
        far=[c(FAR, [0]), c(FAR, LINE, 2), c(FAR, [23], 4), c(FAR, [5], 1)],
        distant=[c(DIST, [0]), c(DIST, [23], 3)],
    ),
    "Easy": dict(
        near=[c(NEAR, SHORT), c(NEAR, LOW_SHORT, 5), c(NEAR, [10], 3), c(NEAR, [9], 3), c(NEAR, [THROW], 2),
              c(NEAR, [1], 3, DEF), c(NEAR, KEEP_OUT, 2),
              react(AA, AIR_TO_AIR, AIR, startup=A2A_T), react(NEAR, SHORT, RECOVERY)],
        mid=[c(MID2, [0]), c(MID2, [18], 4), c(MID2, LINE, 3), c(MID2, [5, 24], 3), c(MID2, [1], 3, DEF)],
        far=[c(FAR, LINE), c(FAR, [0], 5), c(FAR, [18], 4), c(FAR, [2], 3)],
        distant=[c(DIST, [2]), c(DIST, [0], 5), c(DIST, LINE, 3)],
        wakeup_actions=WAKEUP,
    ),
    "Normal": dict(
        near=[c(NEAR, BNB), c(NEAR, LOW_BNB, 5), c(NEAR, FRAME_TRAP, 3), c(NEAR, [THROW], 3), c(NEAR, [13], 2),
              c(NEAR, KEEP_OUT, 3), c(NEAR, [8], 2, DEF), c(NEAR, SHORT, 3),
              react(AA_DP, ANTI_AIR, AIR, startup=AA_T), react(AA, AIR_TO_AIR, AIR, startup=A2A_T),
              react(NEAR, REKKA, RECOVERY), react(NEAR, LOW_SHORT, BLOCKSTUN), react(NEAR, TICK_THROW, BLOCKSTUN),
              react(NEAR, MEATY, KNOCKDOWN)],
        mid=[c(MID1, [0]), c(MID1, SHOT_DASH, 4), c(MID1, JUMP_IN, 3), c(MID1, [10], 2), c(MID1, KEEP_OUT, 2),
             c(MID1, [1], 3, DEF),
             react(MID1, [18], RECOVERY),
             c(MID2, LINE), c(MID2, [18], 5), c(MID2, PRISM, 3), c(MID2, [2], 3),
             react(MID2, PRISM, AIR), react(MID2, LINE, RECOVERY)],
        far=[c(FAR, LINE), c(FAR, PRISM, 4), c(FAR, [18], 4), c(FAR, [2], 2), react(FAR, LINE, RECOVERY)],
        distant=[c(DIST, [2]), c(DIST, LINE, 4)],
        wakeup_actions=WAKEUP,
    ),
    "Hard": dict(
        near=[c(NEAR, BNB), c(NEAR, LOW_BNB, 6), c(NEAR, METER_BNB, 5, gauge=4000),
              c(NEAR, FRAME_TRAP, 3), c(NEAR, [THROW], 3), c(NEAR, KEEP_OUT, 3), c(NEAR, JUMP_BACK_SHOT, 2),
              c(NEAR, [8], 2, DEF),
              c(NEAR, SUPER_BNB, 5, AGG, gauge=6000),   # last = wins most often
              react(AA_DP, ANTI_AIR, AIR, startup=AA_T), react(AA_DP, ANTI_AIR_EX, AIR, gauge=4000, startup=AA_EX_T),
              react(NEAR, REKKA, RECOVERY), react(NEAR, SUPER_BNB, RECOVERY, gauge=6000, chance=5),
              react(NEAR, FRAME_TRAP, BLOCKSTUN), react(NEAR, TICK_THROW, BLOCKSTUN), react(NEAR, MEATY, KNOCKDOWN)],
        mid=[c(MID1, SHOT_DASH), c(MID1, JUMP_IN, 4), c(MID1, FLUX_IN, 3), c(MID1, KEEP_OUT, 2), c(MID1, [1], 3, DEF),
             react(MID1, [18], RECOVERY), react(MID1, RUSH_SUPER, ATTACK, gauge=6000, chance=2), react(MID1, MEATY, KNOCKDOWN),
             c(MID2, LINE), c(MID2, [18], 4), c(MID2, PRISM, 3), c(MID2, [2], 3),
             react(MID2, PRISM, AIR), react(MID2, LINE, RECOVERY)],
        far=[c(FAR, LINE), c(FAR, PRISM, 3), c(FAR, [2], 3), c(FAR, JUMP_IN, 2),
             react(FAR, LINE, RECOVERY), react(FAR, LINE_SUPER, RECOVERY, gauge=6000, chance=5)],
        distant=[c(DIST, [2]), c(DIST, LINE, 4), react(DIST, LINE, RECOVERY)],
        wakeup_actions=WAKEUP,
    ),
    "VeryHard": dict(
        near=[c(NEAR, BNB), c(NEAR, LOW_BNB, 6), c(NEAR, METER_BNB, 6, gauge=4000),
              c(NEAR, FRAME_TRAP, 4), c(NEAR, [THROW], 3), c(NEAR, KEEP_OUT, 3), c(NEAR, JUMP_BACK_SHOT, 2),
              c(NEAR, [8], 2, DEF),
              c(NEAR, SUPER_BNB, 6, AGG, gauge=6000),
              react(AA_DP, ANTI_AIR, AIR, startup=AA_T), react(AA_DP, ANTI_AIR_EX, AIR, gauge=4000, startup=AA_EX_T),
              react(NEAR, REKKA, RECOVERY), react(NEAR, SUPER_BNB, RECOVERY, gauge=6000, chance=5),
              react(NEAR, FRAME_TRAP, BLOCKSTUN), react(NEAR, TICK_THROW, BLOCKSTUN), react(NEAR, MEATY, KNOCKDOWN)],
        mid=[c(MID1, SHOT_DASH), c(MID1, JUMP_IN, 4), c(MID1, JUMP_IN_C, 3), c(MID1, FLUX_IN, 3), c(MID1, KEEP_OUT, 2),
             c(MID1, [1], 2, DEF),
             react(MID1, [18], RECOVERY), react(MID1, RUSH_SUPER, ATTACK, gauge=6000, chance=2), react(MID1, MEATY, KNOCKDOWN),
             c(MID2, LINE), c(MID2, SHOT_DASH, 4), c(MID2, PRISM, 3),
             react(MID2, PRISM, AIR), react(MID2, LINE, RECOVERY)],
        far=[c(FAR, LINE), c(FAR, PRISM, 3), c(FAR, [2], 3),
             react(FAR, LINE, RECOVERY), react(FAR, LINE_SUPER, RECOVERY, gauge=6000, chance=5)],
        distant=[c(DIST, [2]), c(DIST, LINE, 4), react(DIST, LINE, RECOVERY)],
        wakeup_actions=WAKEUP,
    ),
    "Pro": dict(
        near=[c(NEAR, BNB), c(NEAR, LOW_BNB, 6), c(NEAR, METER_BNB, 7, gauge=4000),
              c(NEAR, FRAME_TRAP, 4), c(NEAR, [THROW], 3), c(NEAR, KEEP_OUT, 3), c(NEAR, JUMP_BACK_SHOT, 2),
              c(NEAR, [8], 2, DEF),
              c(NEAR, SUPER_BNB, 7, AGG, gauge=6000),
              react(AA_DP, ANTI_AIR, AIR, startup=AA_T), react(AA_DP, ANTI_AIR_EX, AIR, gauge=4000, startup=AA_EX_T),
              react(NEAR, REKKA, RECOVERY), react(NEAR, SUPER_BNB, RECOVERY, gauge=6000, chance=5),
              react(NEAR, LOW_BNB, BLOCKSTUN), react(NEAR, TICK_THROW, BLOCKSTUN), react(NEAR, MEATY, KNOCKDOWN)],
        mid=[c(MID1, SHOT_DASH), c(MID1, JUMP_IN, 3), c(MID1, JUMP_IN_C, 4), c(MID1, FLUX_IN, 3), c(MID1, KEEP_OUT, 2),
             c(MID1, [1], 2, DEF),
             react(MID1, [18], RECOVERY), react(MID1, RUSH_SUPER, ATTACK, gauge=6000, chance=2), react(MID1, MEATY, KNOCKDOWN),
             c(MID2, LINE), c(MID2, SHOT_DASH, 5), c(MID2, PRISM, 3),
             react(MID2, PRISM, AIR), react(MID2, LINE, RECOVERY)],
        far=[c(FAR, LINE), c(FAR, PRISM, 3), c(FAR, [2], 2),
             react(FAR, LINE, RECOVERY), react(FAR, LINE_SUPER, RECOVERY, gauge=6000, chance=5)],
        distant=[c(DIST, [2]), c(DIST, LINE, 4), react(DIST, LINE, RECOVERY)],
        wakeup_actions=WAKEUP,
    ),
}

if __name__ == "__main__":
    build("leticia", "LET", ACTIONS, BEHAVIOURS, X)
