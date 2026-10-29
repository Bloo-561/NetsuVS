"""PLACEHOLDER FIGHT SOUNDS (Oct 24 2026, night): every attack, special, super, throw and assist sound,
synthesized from noise and oscillators (nothing recorded or downloaded). They are stand-ins: replace any of
them with your own recording.

    python tools/fx/make_fight_sfx.py            # all of them
    python tools/fx/make_fight_sfx.py cecilia    # one group: common, cecilia, flan, leticia, mary, adin, eren, harie
    python tools/fx/make_fight_sfx.py --list     # names and where they go

Needs numpy and scipy (pip install numpy scipy).

WHERE THEY GO
    assets/audio/sfx/fight/<name>.wav          shared ones (throws)
    actors/<fighter>/Sounds/<name>.wav         a fighter's own
    actors/assists/<assist>/Sounds/<name>.wav  an assist's own

USING YOUR OWN SOUND
    Save your .wav over the file with the same name: Godot re-imports it (the game uses it at once).
    Running this script again would put the placeholder back: it SKIPS a file that isn't one it made
    (it remembers what it wrote in tools/fx/fight_sfx_written.json), so your files are safe unless you pass --force.
    Another format (.ogg/.mp3) or another name: change the sound's path in tools/sprite_port/sounds.py (SOUNDS)
    and run `python tools/sprite_port/sounds.py`.
    Which state plays which sound, on which frame: tools/sprite_port/sounds.py (CUES).
"""
import os, sys, json, wave, hashlib
import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.abspath(os.path.join(HERE, '..', '..'))
SR = 44100
WRITTEN = os.path.join(HERE, 'fight_sfx_written.json')

# ======================================================================================================
# small synth kit
# ======================================================================================================
_rng = np.random.default_rng(1)


def seed(n):
    global _rng
    _rng = np.random.default_rng(n)


def N(sec):
    return int(round(SR * sec))


def T(sec):
    return np.arange(N(sec)) / SR


def noise(sec):
    return _rng.standard_normal(N(sec))


def mix_at(dst, src, at, gain=1.0):
    """add src into dst starting at `at` seconds (dst grows if needed); returns dst"""
    i = N(at)
    if i + len(src) > len(dst):
        dst = np.concatenate([dst, np.zeros(i + len(src) - len(dst))])
    dst[i:i + len(src)] += gain * src
    return dst


def sos(kind, f, order=2):
    if kind == 'band':
        lo, hi = f
        hi = min(hi, SR * 0.45)
        return signal.butter(order, [lo, hi], 'band', fs=SR, output='sos')
    return signal.butter(order, min(f, SR * 0.45), kind, fs=SR, output='sos')


def lp(x, f, order=2):
    return signal.sosfilt(sos('low', f, order), x)


def hp(x, f, order=2):
    return signal.sosfilt(sos('high', f, order), x)


def bp(x, lo, hi, order=2):
    return signal.sosfilt(sos('band', (lo, hi), order), x)


def svf(x, fc, q, mode='band'):
    """state-variable filter whose cutoff follows the array fc (Hz, one value per sample): moving whooshes,
    whistles, explosions closing down. Zero-delay form: stable at any cutoff and q."""
    fc = np.clip(np.broadcast_to(np.asarray(fc, float), (len(x),)), 20, SR * 0.45)
    g = np.tan(np.pi * fc / SR); k = 1.0 / q
    a1 = 1.0 / (1.0 + g * (g + k)); a2 = g * a1; a3 = g * a2
    xs = x.tolist(); A1 = a1.tolist(); A2 = a2.tolist(); A3 = a3.tolist()
    out = np.empty(len(xs)); ic1 = ic2 = 0.0
    want_band = mode == 'band'
    for i in range(len(xs)):
        v3 = xs[i] - ic2
        v1 = A1[i] * ic1 + A2[i] * v3
        v2 = ic2 + A2[i] * ic1 + A3[i] * v3
        ic1 = 2.0 * v1 - ic1
        ic2 = 2.0 * v2 - ic2
        out[i] = v1 if want_band else v2
    return out


def svf_band(x, fc, q):
    return svf(x, fc, q, 'band')


def curve(n, pts):
    """piecewise exponential curve through (time fraction, value) points, n samples"""
    t = np.linspace(0, 1, n)
    xs = [p[0] for p in pts]; ys = np.log([p[1] for p in pts])
    return np.exp(np.interp(t, xs, ys))


def fade_end(x, sec=0.025):
    """every piece ends at zero (no hard cut where a layer stops in the middle of a sound)"""
    x = np.array(x, float)
    k = min(N(sec), len(x) // 4)
    if k > 1:
        x[-k:] *= 0.5 + 0.5 * np.cos(np.linspace(0, np.pi, k))
    return x


def env(n, attack, release, peak=None, hold=0.0, shape=2.0):
    """smooth rise over `attack` s, hold, then exponential fall with time constant `release` s"""
    t = np.arange(n) / SR
    a = np.clip(t / max(attack, 1e-4), 0, 1) ** shape
    d = np.where(t < attack + hold, 1.0, np.exp(-(t - attack - hold) / max(release, 1e-4)))
    return fade_end(a * d)


def decay(n, tau, start=0.0):
    t = np.arange(n) / SR
    return fade_end(np.where(t >= start, np.exp(-(t - start) / tau), 0.0))


def osc(freq, sec, kind='sine', phase=0.0):
    """oscillator; freq may be a number or an array (sweeps)"""
    n = N(sec)
    f = np.full(n, float(freq)) if np.isscalar(freq) else np.asarray(freq, float)[:n]
    ph = 2 * np.pi * np.cumsum(f) / SR + phase
    if kind == 'sine':
        return np.sin(ph)
    if kind == 'tri':
        return 2 / np.pi * np.arcsin(np.sin(ph))
    if kind == 'square':
        return np.tanh(4 * np.sin(ph))
    if kind == 'saw':   # additive, so it doesn't alias
        out = np.zeros(n); fmax = float(np.max(f))
        for k in range(1, max(2, int(9000 / max(fmax, 1)))):
            out += np.sin(ph * k) / k
        return out * 0.6
    raise ValueError(kind)


def thump(f0, f1, sec, tau, drive=1.5):
    """kick-like body: a sine falling from f0 to f1"""
    f = f1 + (f0 - f1) * np.exp(-T(sec) / (tau * 0.35))
    x = np.tanh(drive * osc(f, sec)) / np.tanh(drive)
    return x * env(len(x), 0.002, tau)


def burst(sec, lo, hi, tau, attack=0.001):
    x = bp(noise(sec), lo, hi)
    return x * env(len(x), attack, tau, shape=1.0) / (np.std(x) + 1e-9) * 0.3


def bell(f0, sec, ratios=(1.0, 2.76, 5.4, 8.93), taus=(0.4, 0.25, 0.12, 0.06), amps=(1.0, 0.5, 0.3, 0.15), detune=0.0018):
    t = T(sec); out = np.zeros(len(t))
    for r, tau, a in zip(ratios, taus, amps):
        f = f0 * r
        if f > SR * 0.45:
            continue
        ph = 2 * np.pi * f * t
        out += a * (np.sin(ph) + 0.5 * np.sin(ph * (1 + detune))) * np.exp(-t / tau)
    return out * env(len(t), 0.0015, 1e9, shape=1.0) / 1.5   # env() also fades the end


def metal(f0, sec, tau=0.5, bright=1.0):
    """struck metal plate: inharmonic partials"""
    ratios = (1.0, 1.59, 2.14, 2.30, 2.65, 2.92, 3.16, 3.50, 4.15, 5.43)
    taus = tuple(tau * k for k in (1.0, 0.8, 0.7, 0.65, 0.6, 0.5, 0.45, 0.4, 0.3, 0.2))
    amps = tuple(a * (bright ** i) for i, a in enumerate((1.0, 0.8, 0.7, 0.6, 0.5, 0.45, 0.4, 0.3, 0.25, 0.2)))
    return bell(f0, sec, ratios, taus, amps, detune=0.003)


def whoosh(sec, f0, f1, f2, peak, q=2.2, air=0.35):
    """moving air: band-passed noise whose centre rises f0 -> f1 (at `peak` s) -> f2"""
    n = N(sec)
    fc = curve(n, [(0, f0), (peak / sec, f1), (1, f2)])
    x = svf_band(noise(sec), fc, q)
    x2 = svf_band(noise(sec), fc * 2.1, q * 1.6)          # thin high "swish" on top
    body = lp(noise(sec), 500) * air
    t = np.arange(n) / SR
    a = np.where(t < peak, np.sin(0.5 * np.pi * np.clip(t / peak, 0, 1)) ** 2,
                 np.exp(-(t - peak) / max((sec - peak) / 3.5, 0.01)))
    out = (x / (np.std(x) + 1e-9) + 0.3 * x2 / (np.std(x2) + 1e-9) + body / (np.std(body) + 1e-9) * air) * fade_end(a)
    return out


def crackle(sec, rate, lo=1800, hi=9000, tau=0.6, seedv=None):
    """electric crackle: random tiny sparks"""
    n = N(sec); out = np.zeros(n)
    t = 0.0
    while True:
        t += _rng.exponential(1.0 / rate)
        if t >= sec:
            break
        L = int(SR * _rng.uniform(0.0006, 0.004))
        i = N(t)
        if i + L >= n:
            continue
        spark = _rng.standard_normal(L) * np.exp(-np.arange(L) / (L / 3.0)) * _rng.lognormal(0, 0.6)
        out[i:i + L] += spark
    out = bp(out, lo, hi)
    return out / (np.max(np.abs(out)) + 1e-9) * decay(n, tau)


def buzz(sec, f=110, jitter=0.08, lo=300, hi=4000):
    """electric hum: a jittery saw, band-limited"""
    n = N(sec)
    walk = np.cumsum(_rng.standard_normal(n)) / np.sqrt(SR * 0.05)
    walk = lp(walk, 8)
    fr = f * (1 + jitter * np.tanh(walk))
    x = bp(osc(fr, sec, 'saw'), lo, hi)
    gate = lp(np.abs(_rng.standard_normal(n)), 30)
    gate = np.clip(gate / (np.mean(gate) + 1e-9), 0, 2.2)
    return x * gate / (np.std(x) + 1e-9) * 0.35


def zap(sec, f0, f1, tau):
    """laser / spark 'pew': a fast pitch fall with a gritty edge"""
    f = curve(N(sec), [(0, f0), (1, f1)])
    x = 0.7 * osc(f, sec, 'square') + 0.5 * osc(f * 1.007, sec, 'sine')
    x *= 1 + 0.6 * bp(noise(sec), 2000, 8000) / 3
    return x * env(len(x), 0.001, tau, shape=1.0)


def crack(tau=0.03):
    """thunder / gun crack: broadband snap"""
    x = hp(noise(0.25), 900) * env(N(0.25), 0.0004, tau, shape=1.0)
    x += bp(noise(0.25), 400, 2500) * env(N(0.25), 0.0008, tau * 2.5, shape=1.0) * 0.6
    return x


def rumble(sec, f=160, tau=0.6, attack=0.02):
    x = lp(np.cumsum(noise(sec)) * 0.02, f, 4)
    x = hp(x, 25)
    am = 0.6 + 0.4 * lp(np.abs(noise(sec)), 6) / 0.8
    x = x / (np.std(x) + 1e-9) * am
    return x * env(len(x), attack, tau, shape=1.0)


def sparkle(sec, count, flo=2000, fhi=6000, tau=(0.06, 0.25), start=0.0, spread=None):
    """twinkles: little high bells at random times"""
    out = np.zeros(N(sec))
    scale = np.array([0, 2, 4, 7, 9])                      # pentatonic: always sweet
    base = 1046.5
    choices = [base * 2 ** (o + s / 12) for o in range(0, 4) for s in scale]
    choices = [c for c in choices if flo <= c <= fhi]
    span = spread if spread is not None else sec * 0.6
    for _ in range(count):
        at = start + _rng.uniform(0, span)
        f = _rng.choice(choices)
        b = bell(f, min(0.6, sec - at), ratios=(1.0, 2.0, 3.01), taus=(_rng.uniform(*tau), 0.05, 0.03), amps=(1.0, 0.25, 0.1))
        out = mix_at(out, b * _rng.uniform(0.4, 1.0), at)
    return fade_end(out[:N(sec)])


def bubbles(sec, rate, flo=350, fhi=1600, tau=0.6):
    out = np.zeros(N(sec)); t = 0.0
    while True:
        t += _rng.exponential(1.0 / rate)
        if t >= sec:
            break
        L = _rng.uniform(0.008, 0.04); f0 = _rng.uniform(flo, fhi)
        f = f0 * (1 + 0.6 * np.linspace(0, 1, N(L)) ** 1.5)
        b = osc(f, L) * env(N(L), 0.002, L / 3, shape=1.0)
        out = mix_at(out, b * _rng.uniform(0.3, 1.0) * np.exp(-t / tau), t)
    return fade_end(out[:N(sec)])


def flame(sec, attack=0.08, tau=0.5, lo=250, hi=2600):
    """fire: a rough roar with crackles"""
    x = bp(noise(sec), lo, hi)
    am = lp(np.abs(noise(sec)), 18)
    x = x * (0.4 + am / (np.mean(am) + 1e-9) * 0.6)
    x = x / (np.std(x) + 1e-9) * env(N(sec), attack, tau, shape=1.0)
    return x + crackle(sec, 60, 1500, 7000, tau * 1.4) * 0.7


def reverb(x, mix=0.2, decay_s=0.6, damp=5500, pre=0.012):
    """small plate: comb filters into all-passes (fast: scipy lfilter)"""
    tail = N(decay_s * 1.6)
    src = np.concatenate([x, np.zeros(tail)])
    src = np.concatenate([np.zeros(N(pre)), src])[:len(src)]
    wet = np.zeros(len(src))
    for d_ms in (29.7, 37.1, 41.1, 43.7):
        d = N(d_ms / 1000.0)
        g = 10 ** (-3 * (d_ms / 1000.0) / decay_s)
        a = np.zeros(d + 1); a[0] = 1.0; a[d] = -g
        wet += signal.lfilter([1.0], a, src) * 0.25
    for d_ms, g in ((5.0, 0.7), (1.7, 0.7)):
        d = N(d_ms / 1000.0)
        b = np.zeros(d + 1); b[0] = -g; b[d] = 1.0
        a = np.zeros(d + 1); a[0] = 1.0; a[d] = -g
        wet = signal.lfilter(b, a, wet)
    wet = lp(wet, damp)
    dry = np.concatenate([x, np.zeros(tail)])
    return dry * (1 - mix * 0.5) + wet * mix


def norm(x):
    m = np.max(np.abs(x))
    return x / m if m > 0 else x


# ======================================================================================================
# finishing: every sound gets the same clean-up and a loudness that fits next to the engine's hit sounds
# (Mahou's hit sounds peak around -16..-20 dB RMS; swings sit under them, supers a bit over)
# ======================================================================================================
LEVEL = dict(swing_l=-24.0, swing_m=-22.5, swing_h=-21.0, special=-19.0, shot=-18.0, big=-15.5, assist=-19.5, soft=-23.0)


TOP = dict(swing_l=8000, swing_m=7500, swing_h=7000, special=11000, shot=13000, big=11000, assist=11000, soft=11000)


def finish(x, level, fade=0.04):
    x = hp(x, 38, 2)
    x = lp(x, TOP[level], 2)
    # loudness: the loudest 50 ms
    w = N(0.05)
    c = np.concatenate([[0.0], np.cumsum(x ** 2)])
    r = np.sqrt(((c[w:] - c[:-w]) / w).max() if len(x) > w else np.mean(x ** 2)) + 1e-12
    x = x * (10 ** (LEVEL[level] / 20) / r)
    # soft limit to -1 dBFS
    lim = 10 ** (-1 / 20)
    over = np.abs(x) > lim * 0.7
    if over.any():
        k = lim * 0.7
        x = np.where(over, np.sign(x) * (k + (lim - k) * np.tanh((np.abs(x) - k) / (lim - k))), x)
    # trim silence at the end, short fades
    level_env = np.abs(x)
    loud = np.nonzero(level_env > 10 ** (-60 / 20))[0]
    end = min(len(x), (loud[-1] if len(loud) else len(x)) + N(0.02))
    x = x[:end].copy()
    f = min(N(fade), len(x) // 3)
    x[-f:] *= np.linspace(1, 0, f) ** 1.5
    s = min(N(0.0015), len(x) // 10)
    x[:s] *= np.linspace(0, 1, s)
    return x


# ======================================================================================================
# the sounds
# ======================================================================================================
# --- swings ---------------------------------------------------------------------------------------------
def swing(weight, flavour):
    """weight 0 light / 1 medium / 2 heavy; flavour: blade, fist, gun, plain"""
    sec, f0, f1, f2, peak = [(0.22, 700, 2600, 1100, 0.045), (0.30, 520, 2000, 800, 0.06), (0.42, 340, 1400, 520, 0.085)][weight]
    if flavour == 'fist':
        f0, f1, f2 = f0 * 0.65, f1 * 0.62, f2 * 0.7
    x = whoosh(sec, f0, f1, f2, peak, q=2.0 if weight else 2.6, air=0.25 + 0.15 * weight)
    if flavour == 'blade':
        ring = metal(2350 + 300 * (2 - weight), sec, tau=0.09 + 0.04 * weight, bright=0.85)
        scrape = burst(sec, 3500, 9000, 0.02 + 0.01 * weight)
        x = mix_at(x, norm(ring) * 0.35 + norm(scrape) * 0.3, peak * 0.8)
    if flavour == 'fist':
        fw = thump(150, 75, sec, 0.05 + 0.02 * weight, drive=2.0)
        flap = bp(noise(sec), 500, 2200) * (0.5 + 0.5 * np.sin(2 * np.pi * 28 * T(sec))) * env(N(sec), peak, 0.05)
        x = mix_at(x + norm(flap) * 0.25, norm(fw) * (0.6 + 0.2 * weight), peak * 0.9)
    if flavour == 'gun':
        hum = osc(curve(N(sec), [(0, 620), (1, 300)]), sec) * env(N(sec), peak, 0.08) * 0.3
        x = x + hum * (1 + weight * 0.5)
    return x


def heavy_energy_arc():
    """Leticia's j.C: a big gun swing with a blue energy trail"""
    x = swing(2, 'gun')
    vw = lp(osc(curve(N(0.5), [(0, 95), (0.3, 140), (1, 80)]), 0.5, 'saw'), 1400) * env(N(0.5), 0.06, 0.15)
    return mix_at(x, norm(vw) * 0.7, 0.0)


# --- common -----------------------------------------------------------------------------------------------
def throw_reach():
    return whoosh(0.18, 600, 1700, 900, 0.05, q=2.0, air=0.4)


def throw_grab():
    x = burst(0.3, 700, 3200, 0.025) * 3
    x = mix_at(x, thump(120, 65, 0.3, 0.08, 2.2) * 1.2, 0.006)
    x = mix_at(x, burst(0.2, 200, 900, 0.04) * 2, 0.01)
    return reverb(x, 0.12, 0.3)


def throw_break():
    x = np.zeros(N(0.5))
    for k, at in enumerate((0.0, 0.004, 0.011)):     # a sharp "clap" of two hands slapping apart
        x = mix_at(x, burst(0.08, 900, 4500, 0.01) * (1.6 - 0.4 * k), at)
    x = mix_at(x, whoosh(0.3, 1200, 2600, 800, 0.03, q=2.4, air=0.2) * 0.35, 0.01)
    x = mix_at(x, metal(1250, 0.45, tau=0.18, bright=0.8) * 0.3, 0.005)
    x = mix_at(x, thump(160, 90, 0.2, 0.05) * 0.5, 0.0)
    return reverb(x, 0.18, 0.4)


# --- Cecilia: sword and lightning ----------------------------------------------------------------------------
def cec_slash(weight):
    x = swing(weight, 'blade')
    if weight == 2:     # the heavy one leaves a crackle
        x = mix_at(x, crackle(0.35, 260, tau=0.12) * 0.35, 0.07)
    return x


def lightning_dash():
    x = crackle(0.5, 900, tau=0.18) * 0.9
    x = mix_at(x, zap(0.3, 2600, 320, 0.08) * 0.35, 0.0)
    x = mix_at(x, whoosh(0.4, 900, 3000, 900, 0.05, q=1.8, air=0.2) * 0.8, 0.0)
    x = mix_at(x, thump(90, 45, 0.3, 0.07) * 0.8, 0.0)
    x = mix_at(x, buzz(0.35, 140) * env(N(0.35), 0.01, 0.1), 0.0)
    return reverb(x, 0.15, 0.4)


def lightning_slash():
    x = cec_slash(2)
    x = mix_at(x, crack(0.02) * 0.9, 0.05)
    x = mix_at(x, zap(0.25, 3400, 500, 0.06) * 0.3, 0.05)
    x = mix_at(x, crackle(0.4, 500, tau=0.14) * 0.6, 0.05)
    return reverb(x, 0.15, 0.5)


def dash_rush():
    x = whoosh(0.34, 800, 2400, 700, 0.05, q=1.9, air=0.3)
    return mix_at(x, crackle(0.3, 420, tau=0.1) * 0.5, 0.0)


def teleport():
    sec = 0.34
    f = curve(N(0.09), [(0, 380), (1, 4200)])
    up = osc(f, 0.09, 'sine') * env(N(0.09), 0.06, 0.02)
    x = np.zeros(N(sec))
    x = mix_at(x, up * 0.6, 0.0)
    x = mix_at(x, crackle(0.25, 700, 2500, 10000, tau=0.06) * 0.7, 0.05)
    x = mix_at(x, burst(0.15, 1500, 7000, 0.02) * 1.5, 0.085)
    x = mix_at(x, thump(220, 110, 0.12, 0.03) * 0.3, 0.085)
    return reverb(x, 0.22, 0.45)


def counter_stance():
    sec = 0.9
    x = buzz(sec, 110, lo=200, hi=3500) * env(N(sec), 0.25, 0.3, hold=0.15)
    x += crackle(sec, 90, tau=0.5) * 0.5
    x = mix_at(x, metal(2900, 0.5, tau=0.14, bright=0.8) * 0.3 + burst(0.5, 3000, 9000, 0.03) * 0.5, 0.0)
    return reverb(x, 0.2, 0.6)


def thunder(big=1.0, sec=1.8):
    x = crack(0.025) * 1.2
    x = mix_at(x, thump(75, 38, 0.6, 0.22 * big, drive=2.2) * 1.1, 0.004)
    x = mix_at(x, rumble(sec, 190, 0.55 * big, 0.03) * 0.75, 0.01)
    x = mix_at(x, crackle(0.6, 380, tau=0.25) * 0.5, 0.0)
    x = mix_at(x, zap(0.2, 4200, 700, 0.05) * 0.18, 0.0)
    return reverb(x, 0.25, 0.9, damp=4000)


def thunderclap():
    return thunder(1.3, 2.0)


def thunder_barrage():
    sec = 1.3
    x = buzz(sec, 95, lo=250, hi=3000) * env(N(sec), 0.05, 0.25, hold=0.3) * 0.8
    for k in range(5):
        at = 0.02 + 0.083 * k
        x = mix_at(x, crack(0.018) * (0.7 + 0.08 * k), at)
        x = mix_at(x, zap(0.12, 3800 - 300 * k, 600, 0.03) * 0.25, at)
    x = mix_at(x, crackle(0.8, 500, tau=0.3) * 0.6, 0.0)
    x = mix_at(x, rumble(1.0, 170, 0.4, 0.15) * 0.7, 0.15)
    return reverb(x, 0.22, 0.8, damp=4500)


def thunder_impact():
    x = thunder(1.1, 1.5)
    for k in range(4):
        x = mix_at(x, crack(0.015) * 0.45, 0.083 * (k + 1))
    return x


def plunge_dive():
    sec = 0.55
    x = whoosh(sec, 2200, 1500, 400, 0.08, q=1.6, air=0.5)
    return x + crackle(sec, 380, tau=0.3) * 0.5


# --- Flan: star fists ------------------------------------------------------------------------------------------
def chime_arp(notes, gap, tau=0.25):
    out = np.zeros(N(gap * len(notes) + 0.8))
    for k, f in enumerate(notes):
        out = mix_at(out, bell(f, 0.8, ratios=(1.0, 2.0, 3.0, 4.2), taus=(tau, tau * 0.5, 0.06, 0.03), amps=(1.0, 0.3, 0.12, 0.05)), gap * k)
    return out


def star_fist():
    x = swing(1, 'fist')
    x = mix_at(x, chime_arp([1318.5, 1661.2, 1975.5, 2637.0], 0.035) * 0.35, 0.05)
    x = mix_at(x, sparkle(0.6, 7, 3000, 8000, start=0.08, spread=0.25) * 0.25, 0.0)
    return reverb(x, 0.2, 0.6)


def supernova():
    x = swing(2, 'fist')
    x = mix_at(x, thump(110, 45, 0.6, 0.18, 2.5) * 0.9, 0.08)
    x = mix_at(x, burst(0.4, 300, 3000, 0.06) * 1.5, 0.08)
    x = mix_at(x, chime_arp([1046.5, 1318.5, 1568.0, 2093.0, 2637.0], 0.03) * 0.4, 0.09)
    x = mix_at(x, sparkle(0.9, 16, 2500, 8400, start=0.1, spread=0.35) * 0.3, 0.0)
    return reverb(x, 0.25, 0.8)


def armor_glint():
    sec = 0.55
    x = metal(1760, sec, tau=0.3, bright=0.9) * env(N(sec), 0.012, 1e9, shape=1.0) * 0.6
    x += osc(220, sec, 'saw') * env(N(sec), 0.12, 0.12, hold=0.05) * 0.18
    x += sparkle(sec, 4, 3000, 7000, start=0.02, spread=0.2) * 0.3
    return reverb(x, 0.2, 0.5)


def rising(sec=0.7, notes=(1568.0, 2093.0, 2637.0, 3136.0), f=(300, 1700, 2600)):
    n = N(sec)
    fc = curve(n, [(0, f[0]), (0.45, f[1]), (1, f[2])])
    x = svf_band(noise(sec), fc, 1.8) * env(n, 0.08, 0.18, hold=0.06)
    x = x / (np.std(x) + 1e-9)
    x = mix_at(x, chime_arp(list(notes), 0.05, tau=0.18) * 1.1, 0.08)[:n + N(0.5)]
    x = mix_at(x, sparkle(sec, 8, 2600, 8400, start=0.1, spread=sec * 0.5) * 0.7, 0.0)
    return reverb(x, 0.2, 0.6)


def rising_star():
    return rising()


def star_burst():
    x = explosion(0.9, 0.7)
    x = mix_at(x, chime_arp([2093.0, 2637.0, 3136.0, 4186.0], 0.025, tau=0.3) * 0.4, 0.01)
    x = mix_at(x, sparkle(1.0, 22, 2600, 8400, start=0.02, spread=0.5) * 0.45, 0.0)
    return x


def meteor_rise():
    return whoosh(0.4, 280, 1300, 1700, 0.12, q=1.8, air=0.5) + sparkle(0.4, 4, 3000, 7000, start=0.05, spread=0.25) * 0.4


def meteor_fall():
    sec = 0.5
    f = curve(N(sec), [(0, 1900), (1, 480)]) * (1 + 0.012 * np.sin(2 * np.pi * 9 * T(sec)))
    wh = osc(f, sec, 'sine') * env(N(sec), 0.05, 0.25, hold=0.15) * 0.35
    wind = whoosh(sec, 600, 1500, 900, 0.3, q=1.5, air=0.6) * 0.8
    return wh + wind + sparkle(sec, 4, 2600, 6000, start=0.0, spread=0.3) * 0.2


def explosion(sec=1.6, size=1.0):
    n = N(sec)
    x = noise(sec)
    cut = curve(n, [(0, 5200), (0.25 / sec, 900), (1, 160)])
    body = svf(x, cut, 0.8, 'low') * env(n, 0.003, 0.28 * size, shape=1.0)
    body = body / (np.std(body[:N(0.2)]) + 1e-9)
    out = body * 0.8
    out = mix_at(out, thump(70, 32, sec, 0.35 * size, drive=2.6) * 1.3, 0.0)[:n]
    out = mix_at(out, crack(0.02) * 0.9, 0.0)[:n]
    out = mix_at(out, rumble(sec, 140, 0.6 * size, 0.04) * 0.6, 0.02)[:n]
    out = mix_at(out, crackle(sec, 90, 800, 6000, tau=0.5 * size) * 0.4, 0.05)[:n]
    return reverb(out, 0.22, 0.9, damp=3800)


def meteor_impact():
    x = explosion(0.9, 0.6)
    for k in range(6):   # debris
        x = mix_at(x, burst(0.06, 900, 5000, 0.008) * _rng.uniform(0.3, 0.7), 0.06 + _rng.uniform(0, 0.35))
    return x


def meteor_impact_big():
    x = explosion(1.3, 0.9)
    x = mix_at(x, sparkle(1.2, 14, 2600, 8400, start=0.04, spread=0.5) * 0.4, 0.0)
    return x


def radiant_rush():
    sec = 0.65
    x = whoosh(sec, 350, 1800, 600, 0.12, q=1.5, air=0.6) * 1.2
    x += sparkle(sec, 10, 2600, 8400, start=0.05, spread=0.4) * 0.6
    x = mix_at(x, chime_arp([1318.5, 1975.5, 2637.0], 0.06, tau=0.3) * 0.4, 0.0)[:N(sec) + N(0.5)]
    return reverb(x, 0.2, 0.6)


def radiant_burst():
    x = np.zeros(N(1.6))
    for k in range(5):
        at = 0.017 + 0.1 * k
        x = mix_at(x, thump(140, 60, 0.15, 0.04, 2.0) * 0.8, at)
        x = mix_at(x, burst(0.08, 600, 4000, 0.012) * 1.3, at)
        x = mix_at(x, bell(2093.0 * 2 ** (k * 2 / 12), 0.3, ratios=(1.0, 2.0), taus=(0.12, 0.05), amps=(1, 0.3)) * 0.3, at + 0.004)
    x = mix_at(x, explosion(1.1, 0.8) * 0.9, 0.42)
    x = mix_at(x, sparkle(1.5, 26, 2600, 8400, start=0.0, spread=0.9) * 0.35, 0.0)
    return x


def explosion_big():
    x = explosion(2.2, 1.4)
    x = mix_at(x, explosion(1.4, 0.8) * 0.5, 0.12)
    return x


# --- Leticia: guns, beams and the hover board ------------------------------------------------------------------
def gunshot(pitch=1.0):
    x = crack(0.012) * 1.4
    x = mix_at(x, zap(0.11, 3000 * pitch, 650 * pitch, 0.035) * 0.55, 0.0)
    x = mix_at(x, burst(0.12, 250, 2500, 0.03) * 1.6, 0.0)
    x = mix_at(x, thump(130, 60, 0.15, 0.05, 2.0) * 0.7, 0.0)
    return reverb(x, 0.18, 0.5, damp=5000)


def gunshot_double():
    x = gunshot(1.0)
    return mix_at(x, gunshot(0.9) * 0.85, 0.022)


def beam(sec, f0, size=1.0, attack=0.03):
    n = N(sec)
    vib = 1 + 0.004 * np.sin(2 * np.pi * 6 * T(sec))
    x = sum(osc(f0 * r * vib * (1 + d), sec, 'saw') for r, d in ((1, 0), (1, 0.006), (1.5, -0.004), (2, 0.003)))
    x = lp(x, 2400 * size, 2)
    whine = osc(f0 * 9 * vib, sec) * 0.15
    hiss = bp(noise(sec), 3000, 9000) * 0.25
    trem = 1 + 0.3 * np.sin(2 * np.pi * 34 * T(sec))
    x = (x / (np.std(x) + 1e-9) + whine + hiss / (np.std(hiss) + 1e-9) * 0.25) * trem
    return x * env(n, attack, sec * 0.18, hold=sec * 0.5, shape=1.0)


def photon_beam():
    x = gunshot(1.1) * 0.8
    x = mix_at(x, beam(0.75, 190, 1.0) * 0.9, 0.01)
    return reverb(x, 0.2, 0.6)


def ricochet():
    x = gunshot(1.0)
    sec = 0.4
    f = curve(N(sec), [(0, 3300), (1, 1500)]) * (1 + 0.02 * np.sin(2 * np.pi * 21 * T(sec)))
    ping = osc(f, sec) * env(N(sec), 0.002, 0.13, shape=1.0)
    x = mix_at(x, ping * 0.4, 0.13)
    x = mix_at(x, burst(0.05, 2000, 8000, 0.006) * 0.9, 0.13)
    return reverb(x, 0.25, 0.7)


def prism_beam():
    x = beam(1.05, 150, 1.2, attack=0.02) * 1.1
    x = mix_at(x, crack(0.02) * 1.2, 0.0)
    x = mix_at(x, thump(90, 40, 0.5, 0.18, 2.4) * 0.9, 0.0)
    return reverb(x, 0.22, 0.8)


def board_flip():
    sec = 0.38
    x = whoosh(sec, 500, 1700, 600, 0.1, q=1.7, air=0.4)
    hum = (osc(180, sec) + 0.4 * osc(360, sec, 'tri')) * (1 + 0.5 * np.sin(2 * np.pi * 60 * T(sec))) * env(N(sec), 0.05, 0.12)
    return x + hum * 0.25


def board_spin():
    sec = 0.75
    x = whoosh(sec, 500, 1500, 700, 0.25, q=1.6, air=0.4)
    x *= 0.55 + 0.45 * np.sin(2 * np.pi * 11 * T(sec)) ** 2
    hum = osc(curve(N(sec), [(0, 200), (1, 150)]), sec, 'tri') * env(N(sec), 0.05, 0.3, hold=0.2) * 0.25
    return x + hum


def comet_kick():
    return rising(0.6, notes=(2093.0, 2637.0, 3136.0, 4186.0), f=(400, 2200, 3000))


def stardrive_charge():
    sec = 0.4
    f = curve(N(sec), [(0, 180), (1, 1400)])
    x = sum(osc(f * r, sec, 'sine') * a for r, a in ((1, 1.0), (2.01, 0.5), (3.0, 0.25)))
    x = x * env(N(sec), sec * 0.9, 0.05, shape=2.0)
    x += bp(noise(sec), 2000, 8000) * env(N(sec), sec, 0.05, shape=3.0) * 0.4
    return reverb(x, 0.2, 0.5)


def stardrive_beam():
    x = beam(1.7, 95, 1.4, attack=0.015) * 1.2
    x = mix_at(x, crack(0.03) * 1.4, 0.0)
    x = mix_at(x, thump(80, 32, 0.9, 0.35, 2.8) * 1.0, 0.0)
    x = mix_at(x, rumble(1.6, 150, 0.6, 0.05) * 0.6, 0.0)
    return reverb(x, 0.25, 1.0, damp=4500)


def crimson_rush():
    sec = 0.65
    x = whoosh(sec, 400, 1600, 700, 0.12, q=1.5, air=0.6)
    x += flame(sec, 0.06, 0.25) * 0.5
    x += (osc(160, sec, 'saw') * env(N(sec), 0.05, 0.2, hold=0.2)) * 0.15
    return reverb(x, 0.18, 0.5)


def flame_shot():
    x = gunshot(0.95)
    return mix_at(x, flame(0.4, 0.01, 0.12) * 0.6, 0.0)


def flame_trap():
    x = flame(1.1, 0.12, 0.45, 200, 2200) * 1.1
    x = mix_at(x, thump(100, 50, 0.4, 0.12) * 0.5, 0.0)
    return reverb(x, 0.2, 0.6)


def flame_explosion():
    x = explosion(1.9, 1.2)
    return mix_at(x, flame(1.5, 0.02, 0.5) * 0.5, 0.0)


# --- Mary: violin ---------------------------------------------------------------------------------------------------
NOTE = {n: 440.0 * 2 ** ((i - 9) / 12 + o - 4) for o in range(3, 8) for i, n in enumerate(
    ['C%d', 'C#%d', 'D%d', 'D#%d', 'E%d', 'F%d', 'F#%d', 'G%d', 'G#%d', 'A%d', 'A#%d', 'B%d']) for n in [n % o]}


def violin_note(f, sec, accent=0.0, vib_delay=0.08):
    """a bowed string: harmonic stack with the bridge's bright hump, vibrato, bow noise"""
    n = N(sec + 0.25); t = np.arange(n) / SR
    vib = 1 + 0.0045 * np.sin(2 * np.pi * 5.6 * t) * np.clip((t - vib_delay) / 0.15, 0, 1)
    ph = 2 * np.pi * np.cumsum(f * vib) / SR
    x = np.zeros(n)
    for k in range(1, 30):
        fk = f * k
        if fk > 11000:
            break
        hump = 1.0 + 1.6 * np.exp(-((fk - 2900) / 1400) ** 2) + 0.8 * np.exp(-((fk - 500) / 250) ** 2)
        x += np.sin(ph * k + k * 0.7) * hump / k ** 0.95
    bow = bp(noise(sec + 0.25), 1500, 7000) * 0.06
    a = env(n, 0.04 - 0.025 * accent, 0.09, hold=sec - 0.04, shape=1.5)
    sw = 1 + accent * 0.8 * np.exp(-t / 0.06)
    return (x / 6 + bow) * a * sw


def violin_phrase(notes):
    out = np.zeros(N(2.6))
    for at, names, sec, acc in notes:
        for nm in names.split('+'):
            out = mix_at(out, violin_note(NOTE[nm], sec, acc), at)
    body = bp(out, 250, 6000)
    return reverb(body, 0.3, 1.1, damp=6000)


def encore():
    # starts on frame 14; the song peaks with two strokes on frames 50 and 54 (0.6 s and 0.67 s in)
    return violin_phrase([(0.00, 'D5', 0.11, 0.3), (0.10, 'E5', 0.10, 0.2), (0.20, 'F5', 0.10, 0.2),
                          (0.30, 'A5', 0.10, 0.2), (0.40, 'C6', 0.10, 0.2), (0.50, 'D6', 0.11, 0.3),
                          (0.60, 'A5+F6', 0.07, 1.0), (0.67, 'A5+D6', 0.55, 1.0)])


def fermata():
    # plays frames 14-38; the note leaves on frame 26 (0.2 s in)
    return violin_phrase([(0.00, 'A5', 0.1, 0.3), (0.1, 'C6', 0.1, 0.2), (0.2, 'E6', 0.38, 1.0)])


def note_chime():
    x = bell(NOTE['E6'], 0.9, ratios=(1.0, 2.0, 3.0), taus=(0.35, 0.12, 0.05), amps=(1, 0.2, 0.08))
    x = mix_at(x, bell(NOTE['B6'], 0.9, ratios=(1.0, 2.0), taus=(0.3, 0.1), amps=(1, 0.2)) * 0.6, 0.04)
    return reverb(x, 0.3, 0.8)


def note_burst():
    x = thump(260, 120, 0.2, 0.05, 1.5) * 0.6 + burst(0.2, 1500, 7000, 0.03) * 1.2
    x = mix_at(x, chime_arp([NOTE['F6'], NOTE['D6'], NOTE['A5'], NOTE['F5']], 0.03, tau=0.3) * 0.5, 0.0)
    x = mix_at(x, sparkle(0.8, 14, 2600, 8400, start=0.0, spread=0.3) * 0.4, 0.0)
    return reverb(x, 0.25, 0.7)


# --- Adin: shield ---------------------------------------------------------------------------------------------------
def shield_raise():
    x = burst(0.12, 2500, 8000, 0.03) * 1.0
    x = mix_at(x, metal(420, 0.5, tau=0.18, bright=0.9) * 0.6, 0.02)
    x = mix_at(x, thump(140, 80, 0.15, 0.04) * 0.5, 0.02)
    return reverb(x, 0.15, 0.4)


def shield_block():
    x = metal(310, 0.9, tau=0.35, bright=0.95) * 1.2
    x += burst(0.9, 1500, 7000, 0.015) * 1.4
    x = mix_at(x, thump(110, 55, 0.4, 0.09, 2.2) * 0.9, 0.0)
    return reverb(x, 0.22, 0.6)


def shield_bash():
    x = whoosh(0.3, 350, 1300, 500, 0.08, q=1.8, air=0.5) * 0.9
    x = mix_at(x, metal(360, 0.6, tau=0.22, bright=0.9) * 0.8 + thump(120, 50, 0.6, 0.1, 2.4) * 1.0, 0.08)
    return reverb(x, 0.18, 0.5)


def rush_run():
    x = np.zeros(N(1.0))
    for k in range(7):
        at = 0.02 + 0.115 * k
        x = mix_at(x, thump(120, 70, 0.1, 0.03) * 0.6 + burst(0.1, 1800, 6000, 0.01) * 0.4, at)
        x = mix_at(x, metal(1150 + 90 * (k % 2), 0.2, tau=0.05, bright=0.8) * 0.12, at + 0.005)
    x = mix_at(x, whoosh(0.9, 300, 900, 600, 0.45, q=1.4, air=0.6) * 0.5, 0.0)
    return x


# --- Eren: sword -----------------------------------------------------------------------------------------------------
def eren_slash():
    return swing(1, 'blade')


def eren_dash():
    return whoosh(0.32, 450, 1300, 600, 0.05, q=1.6, air=0.6)


def eren_jump():
    return whoosh(0.25, 400, 1100, 1400, 0.06, q=2.0, air=0.5)


def eren_spin():
    sec = 0.6
    x = whoosh(sec, 600, 1800, 800, 0.15, q=1.8, air=0.3)
    x *= 0.45 + 0.55 * np.sin(2 * np.pi * 9 * T(sec)) ** 2
    return mix_at(x, metal(2600, 0.4, tau=0.1, bright=0.8) * 0.15, 0.1)


# --- Harie: water ------------------------------------------------------------------------------------------------------
def splash(sec=0.7, size=1.0):
    x = burst(sec, 900, 8000, 0.12 * size, attack=0.004) * 2.2
    x += bubbles(sec, 90 * size, tau=0.3 * size) * 0.5
    x = mix_at(x, thump(160, 80, 0.2, 0.05) * 0.5, 0.0)[:N(sec)]
    return reverb(x, 0.15, 0.5)


def harie_dive():
    x = whoosh(0.2, 600, 1200, 800, 0.08, q=1.5, air=0.4) * 0.5
    return mix_at(x, splash(0.7, 1.0), 0.12)


def harie_burst():
    x = splash(0.9, 1.5)
    x = mix_at(x, whoosh(0.45, 400, 1500, 2000, 0.1, q=1.6, air=0.6) * 0.6, 0.06)
    return x


def harie_wave():
    sec = 2.4
    n = N(sec)
    x = lp(noise(sec), 1800, 2) + bp(noise(sec), 400, 3500) * 0.6
    am = 0.55 + 0.45 * lp(np.abs(noise(sec)), 3) / 0.8
    x = x / (np.std(x) + 1e-9) * am * env(n, 0.35, 0.5, hold=1.0, shape=1.5)
    x += bubbles(sec, 60, tau=2.0) * 0.4
    for k in range(4):
        x = mix_at(x, burst(0.3, 1200, 7000, 0.06) * 0.7, 0.25 + 0.45 * k)[:n]
    return reverb(x, 0.2, 0.7)


def wave_launch():
    return splash(0.65, 1.2)


# ======================================================================================================
# the list: name -> (group, file, maker, level)
# ======================================================================================================
SFX = {
    # shared
    'throw_reach':       ('common', 'assets/audio/sfx/fight/throw_reach.wav', throw_reach, 'swing_m'),
    'throw_grab':        ('common', 'assets/audio/sfx/fight/throw_grab.wav', throw_grab, 'special'),
    'throw_break':       ('common', 'assets/audio/sfx/fight/throw_break.wav', throw_break, 'special'),
    # Cecilia
    'cec_slash_light':   ('cecilia', 'actors/cecilia/Sounds/slash_light.wav', lambda: cec_slash(0), 'swing_l'),
    'cec_slash_medium':  ('cecilia', 'actors/cecilia/Sounds/slash_medium.wav', lambda: cec_slash(1), 'swing_m'),
    'cec_slash_heavy':   ('cecilia', 'actors/cecilia/Sounds/slash_heavy.wav', lambda: cec_slash(2), 'swing_h'),
    'cec_lightning_dash': ('cecilia', 'actors/cecilia/Sounds/lightning_dash.wav', lightning_dash, 'special'),
    'cec_lightning_slash': ('cecilia', 'actors/cecilia/Sounds/lightning_slash.wav', lightning_slash, 'special'),
    'cec_dash_rush':     ('cecilia', 'actors/cecilia/Sounds/dash_rush.wav', dash_rush, 'swing_h'),
    'cec_teleport':      ('cecilia', 'actors/cecilia/Sounds/teleport.wav', teleport, 'special'),
    'cec_counter_stance': ('cecilia', 'actors/cecilia/Sounds/counter_stance.wav', counter_stance, 'soft'),
    'cec_thunderclap':   ('cecilia', 'actors/cecilia/Sounds/thunderclap.wav', thunderclap, 'big'),
    'cec_thunder_barrage': ('cecilia', 'actors/cecilia/Sounds/thunder_barrage.wav', thunder_barrage, 'big'),
    'cec_thunder_impact': ('cecilia', 'actors/cecilia/Sounds/thunder_impact.wav', thunder_impact, 'big'),
    'cec_plunge_dive':   ('cecilia', 'actors/cecilia/Sounds/plunge_dive.wav', plunge_dive, 'special'),
    # Flan
    'fln_punch_light':   ('flan', 'actors/flan/Sounds/punch_light.wav', lambda: swing(0, 'fist'), 'swing_l'),
    'fln_punch_medium':  ('flan', 'actors/flan/Sounds/punch_medium.wav', lambda: swing(1, 'fist'), 'swing_m'),
    'fln_punch_heavy':   ('flan', 'actors/flan/Sounds/punch_heavy.wav', lambda: swing(2, 'fist'), 'swing_h'),
    'fln_star_fist':     ('flan', 'actors/flan/Sounds/star_fist.wav', star_fist, 'special'),
    'fln_supernova':     ('flan', 'actors/flan/Sounds/supernova.wav', supernova, 'special'),
    'fln_armor_glint':   ('flan', 'actors/flan/Sounds/armor_glint.wav', armor_glint, 'soft'),
    'fln_rising_star':   ('flan', 'actors/flan/Sounds/rising_star.wav', rising_star, 'special'),
    'fln_star_burst':    ('flan', 'actors/flan/Sounds/star_burst.wav', star_burst, 'big'),
    'fln_meteor_rise':   ('flan', 'actors/flan/Sounds/meteor_rise.wav', meteor_rise, 'swing_h'),
    'fln_meteor_fall':   ('flan', 'actors/flan/Sounds/meteor_fall.wav', meteor_fall, 'special'),
    'fln_meteor_impact': ('flan', 'actors/flan/Sounds/meteor_impact.wav', meteor_impact, 'special'),
    'fln_meteor_impact_big': ('flan', 'actors/flan/Sounds/meteor_impact_big.wav', meteor_impact_big, 'big'),
    'fln_radiant_rush':  ('flan', 'actors/flan/Sounds/radiant_rush.wav', radiant_rush, 'special'),
    'fln_radiant_burst': ('flan', 'actors/flan/Sounds/radiant_burst.wav', radiant_burst, 'big'),
    'fln_explosion_big': ('flan', 'actors/flan/Sounds/explosion_big.wav', explosion_big, 'big'),
    # Leticia
    'let_swing_light':   ('leticia', 'actors/leticia/Sounds/swing_light.wav', lambda: swing(0, 'gun'), 'swing_l'),
    'let_swing_medium':  ('leticia', 'actors/leticia/Sounds/swing_medium.wav', lambda: swing(1, 'gun'), 'swing_m'),
    'let_swing_heavy':   ('leticia', 'actors/leticia/Sounds/swing_heavy.wav', heavy_energy_arc, 'swing_h'),
    'let_gunshot':       ('leticia', 'actors/leticia/Sounds/gunshot.wav', gunshot, 'shot'),
    'let_gunshot_double': ('leticia', 'actors/leticia/Sounds/gunshot_double.wav', gunshot_double, 'shot'),
    'let_comet_kick':    ('leticia', 'actors/leticia/Sounds/comet_kick.wav', comet_kick, 'special'),
    'let_photon_beam':   ('leticia', 'actors/leticia/Sounds/photon_beam.wav', photon_beam, 'special'),
    'let_ricochet':      ('leticia', 'actors/leticia/Sounds/ricochet.wav', ricochet, 'shot'),
    'let_prism_beam':    ('leticia', 'actors/leticia/Sounds/prism_beam.wav', prism_beam, 'big'),
    'let_board_flip':    ('leticia', 'actors/leticia/Sounds/board_flip.wav', board_flip, 'swing_m'),
    'let_board_spin':    ('leticia', 'actors/leticia/Sounds/board_spin.wav', board_spin, 'swing_h'),
    'let_stardrive_charge': ('leticia', 'actors/leticia/Sounds/stardrive_charge.wav', stardrive_charge, 'special'),
    'let_stardrive_beam': ('leticia', 'actors/leticia/Sounds/stardrive_beam.wav', stardrive_beam, 'big'),
    'let_crimson_rush':  ('leticia', 'actors/leticia/Sounds/crimson_rush.wav', crimson_rush, 'special'),
    'let_flame_shot':    ('leticia', 'actors/leticia/Sounds/flame_shot.wav', flame_shot, 'shot'),
    'let_flame_trap':    ('leticia', 'actors/leticia/Sounds/flame_trap.wav', flame_trap, 'special'),
    'let_flame_explosion': ('leticia', 'actors/leticia/Sounds/flame_explosion.wav', flame_explosion, 'big'),
    # assists
    'mry_encore':        ('mary', 'actors/assists/mary/Sounds/encore.wav', encore, 'assist'),
    'mry_fermata':       ('mary', 'actors/assists/mary/Sounds/fermata.wav', fermata, 'assist'),
    'mry_note_chime':    ('mary', 'actors/assists/mary/Sounds/note_chime.wav', note_chime, 'soft'),
    'mry_note_burst':    ('mary', 'actors/assists/mary/Sounds/note_burst.wav', note_burst, 'special'),
    'adn_shield_raise':  ('adin', 'actors/assists/adin/Sounds/shield_raise.wav', shield_raise, 'soft'),
    'adn_shield_block':  ('adin', 'actors/assists/adin/Sounds/shield_block.wav', shield_block, 'special'),
    'adn_shield_bash':   ('adin', 'actors/assists/adin/Sounds/shield_bash.wav', shield_bash, 'special'),
    'adn_rush_run':      ('adin', 'actors/assists/adin/Sounds/rush_run.wav', rush_run, 'assist'),
    'ern_slash':         ('eren', 'actors/assists/eren/Sounds/slash.wav', eren_slash, 'swing_m'),
    'ern_dash':          ('eren', 'actors/assists/eren/Sounds/dash.wav', eren_dash, 'swing_m'),
    'ern_jump':          ('eren', 'actors/assists/eren/Sounds/jump.wav', eren_jump, 'swing_l'),
    'ern_spin':          ('eren', 'actors/assists/eren/Sounds/spin.wav', eren_spin, 'swing_h'),
    'hre_dive':          ('harie', 'actors/assists/harie/Sounds/dive.wav', harie_dive, 'assist'),
    'hre_burst':         ('harie', 'actors/assists/harie/Sounds/burst.wav', harie_burst, 'special'),
    'hre_wave':          ('harie', 'actors/assists/harie/Sounds/wave.wav', harie_wave, 'assist'),
    'hre_wave_launch':   ('harie', 'actors/assists/harie/Sounds/wave_launch.wav', wave_launch, 'assist'),
}


# ======================================================================================================
def md5_file(p):
    return hashlib.md5(open(p, 'rb').read()).hexdigest()


def write_wav(path, x):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = (np.clip(x, -1, 1) * 32767).astype('<i2')
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(data.tobytes())


def main(argv):
    force = '--force' in argv
    args = [a for a in argv if not a.startswith('--')]
    if '--list' in argv:
        for k, (g, f, _, lv) in SFX.items():
            print('%-24s %-8s %s' % (k, g, f))
        return
    written = json.load(open(WRITTEN)) if os.path.exists(WRITTEN) else {}
    for i, (name, (group, rel, make, level)) in enumerate(SFX.items()):
        if args and group not in args and name not in args:
            continue
        path = os.path.join(PROJ, rel)
        if os.path.exists(path) and not force and written.get(rel) != md5_file(path):
            print('SKIPPED (not made by this script, or changed since: your own sound?) ' + rel)
            continue
        seed(1000 + i * 17)
        x = finish(np.asarray(make(), float), level)
        write_wav(path, x)
        written[rel] = md5_file(path)
        print('wrote %-52s %.2f s' % (rel, len(x) / SR))
    json.dump(written, open(WRITTEN, 'w'), indent=1, sort_keys=True)


if __name__ == '__main__':
    main(sys.argv[1:])
