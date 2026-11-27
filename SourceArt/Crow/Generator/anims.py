import numpy as np, math
from scipy.interpolate import CubicSpline
from crowlib import *

ID = np.array([0, 0, 0, 1.0])
FPS = 30

# ---------- wing helpers (defined for left side, mirrored to right) ----------
def wing(upper, lower, hand):
    return {"upperarm": upper, "lowerarm": lower, "hand": hand}

def folded_wing():
    """Wing tucked against the body side, expressed in the body frame."""
    up = frame_quat((0.10, -0.25, -1.0), (1.4, 1.0, 0.0))
    lo = frame_quat((0.18, 0.15, 1.0), (1.4, 1.0, 0.0))
    ha = frame_quat((0.10, 0.03, -1.0), (1.1, 1.0, 0.0))
    lo_l = qmul(qinv(up), lo)
    ha_l = qmul(qinv(lo), ha)
    return wing(up, lo_l, ha_l)

FOLD = folded_wing()

def ext(flap=0, sweep=0, twist=0, elbow=0, eflap=0, wrist=0, wflap=0):
    return wing(W(flap, sweep, twist), W(eflap, 0, 0, elbow), W(wflap, 0, 0, wrist))

def blend_wing(a, b, t):
    return {k: slerp(a[k], b[k], t) for k in a}

def slerp(a, b, t):
    a = np.asarray(a); b = np.asarray(b)
    if a.dot(b) < 0: b = -b
    d = np.clip(a.dot(b), -1, 1)
    if d > 0.9995: q = a + t*(b-a); return q/np.linalg.norm(q)
    th = math.acos(d)
    return (math.sin((1-t)*th)*a + math.sin(t*th)*b)/math.sin(th)

# ---------- full pose builder ----------
def pose(wingL, wingR=None, body=(0, 0, 0), body_t=(0, 0, 0), neck=(0, 0, 0), head=(0, 0, 0),
         tail=(0, 0, 0), legs="stand", ground=False):
    wingR = wingR if wingR is not None else wingL
    p = {"body": R(*body), "neck": R(*neck), "head": R(*head), "tail": R(*tail),
         "body_t": np.array(body_t, float), "_ground": 1.0 if ground else 0.0}
    for k, q in wingL.items(): p[f"{k}_l"] = q
    for k, q in wingR.items(): p[f"{k}_r"] = qmirror(q)
    if isinstance(legs, str):
        legs = {"stand": (-body[0], 0, 0), "tucked": (80, 0, -40), "reach": (-55, -10, 0),
                "crouch": (-body[0] - 35, 70, -35)}[legs]
    th, ca, fo = legs
    for s in "lr":
        p[f"thigh_{s}"] = R(x=th); p[f"calf_{s}"] = R(x=ca); p[f"foot_{s}"] = R(x=fo)
    return p

PERCH = dict(body=(-22, 0, 0), neck=(14, 0, 0), head=(6, 0, 0), tail=(-6, 0, 0))

def perch(**over):
    k = dict(PERCH); k.update(over)
    return pose(FOLD, ground=True, **k)

# flight flap cycle key poses (phase 0..1)
FLAP_KEYS = [
    (0.00, ext(flap=58, sweep=8, twist=-6, elbow=-22, eflap=8, wrist=30, wflap=-6)),     # top
    (0.18, ext(flap=18, sweep=0, twist=14, elbow=-4, wrist=6, wflap=4)),                  # mid downstroke
    (0.42, ext(flap=-42, sweep=-10, twist=6, elbow=0, wrist=0, wflap=-14)),               # bottom
    (0.70, ext(flap=-2, sweep=12, twist=-18, elbow=-50, eflap=10, wrist=62, wflap=-8)),  # mid upstroke (folded)
]
GLIDE = ext(flap=8, sweep=-3, twist=2, elbow=-6, wrist=10, wflap=4)

def flap_wing(phase):
    """Periodic cubic interpolation through FLAP_KEYS."""
    return interp_wings(FLAP_KEYS, phase % 1.0, periodic=True)

def interp_wings(keys, t, periodic=False):
    ts = [k[0] for k in keys]
    out = {}
    for b in keys[0][1]:
        qs = [np.array(k[1][b]) for k in keys]
        for i in range(1, len(qs)):
            if qs[i].dot(qs[i-1]) < 0: qs[i] = -qs[i]
        tt = list(ts); Q = np.array(qs)
        if periodic:
            if Q[0].dot(Q[-1]) < 0: pass
            tt = tt + [1.0]; Q = np.vstack([Q, Q[0]])
            if Q[-1].dot(Q[-2]) < 0: Q[-1] = -Q[-1]
            if not np.allclose(Q[-1], Q[0]): Q[-1] = Q[0] if Q[0].dot(Q[-2]) >= 0 else -Q[0]
            cs = CubicSpline(tt, Q, bc_type="periodic" if np.allclose(Q[0], Q[-1]) else "not-a-knot")
        else:
            cs = CubicSpline(tt, Q, bc_type="clamped")
        q = cs(t); out[b] = q/np.linalg.norm(q)
    return out

# ---------- generic keyed track: list of (time, pose) -> sampled frames ----------
def sample_track(keys, duration, fps=FPS, loop=False):
    times = [k[0] for k in keys]
    names = [n for n, *_ in BONES if n != "root"]
    frames = []
    nfr = int(round(duration*fps)) + 1
    # build splines per bone
    splines = {}
    for n in names + ["body_t", "_ground"]:
        vals = []
        for _, p in keys:
            v = np.array(p.get(n, ID if n not in ("body_t", "_ground") else (np.zeros(3) if n == "body_t" else 0.0)), float)
            vals.append(np.atleast_1d(v))
        V = np.array(vals)
        if V.shape[1] == 4:
            for i in range(1, len(V)):
                if V[i].dot(V[i-1]) < 0: V[i] = -V[i]
        if n == "_ground":
            splines[n] = lambda t, T=np.array(times), Vv=V[:, 0]: np.interp(t, T, Vv)
        else:
            bc = "clamped"
            if loop:
                if V.shape[1] == 4 and V[0].dot(V[-1]) < 0: V[-1] = -V[-1]
                bc = "periodic" if np.allclose(V[0], V[-1], atol=1e-6) else "clamped"
            if len(times) == 2:
                splines[n] = (lambda t, T=times, Vv=V: Vv[0] + (Vv[1]-Vv[0]) * smooth((t-T[0])/(T[1]-T[0])))
            else:
                splines[n] = CubicSpline(times, V, bc_type=bc)
    for f in range(nfr):
        t = min(f/fps, duration)
        p = {}
        for n in names:
            q = np.asarray(splines[n](t)); p[n] = q/np.linalg.norm(q)
        p["body_t"] = np.asarray(splines["body_t"](t))
        g = float(splines["_ground"](t))
        if g > 0: ground_fix(p, g)
        frames.append(p)
    return frames

def smooth(x): x = np.clip(x, 0, 1); return x*x*(3-2*x)

FOOT_Y = BPOS["foot_l"][1]
def ground_fix(p, weight):
    Wm = world_mats(p)
    low = min(Wm["foot_l"][1, 3], Wm["foot_r"][1, 3])
    p["body_t"] = p["body_t"] + np.array([0, (FOOT_Y - low)*weight, 0])

# ---------- the animations ----------
def anim_idle():
    D = 4.0
    keys = [
        (0.0, perch()),
        (0.7, perch(head=(4, 0, 0))),
        (1.0, perch(head=(2, 42, 8))),          # look left
        (1.8, perch(head=(2, 40, 6))),
        (2.2, perch(head=(6, -38, -8))),        # look right
        (2.9, perch(head=(8, -36, -6), tail=(-2, 0, 0))),
        (3.15, perch(head=(6, 0, 0), tail=(-16, 0, 0))),  # tail flick
        (3.35, perch(tail=(2, 0, 0))),
        (4.0, perch()),
    ]
    fr = sample_track(keys, D, loop=True)
    # breathing
    for i, p in enumerate(fr):
        p["body_t"] = p["body_t"] + np.array([0, 0.0015*math.sin(2*math.pi*i/FPS/1.333), 0])
    return fr

def anim_peck():
    D = 1.6
    down = dict(body=(18, 0, 0), neck=(48, 0, 0), head=(26, 0, 0), tail=(-14, 0, 0))
    up = dict(body=(8, 0, 0), neck=(34, 0, 0), head=(14, 0, 0), tail=(-10, 0, 0))
    keys = [(0.0, perch()), (0.30, perch(**down)), (0.40, perch(**up)), (0.50, perch(**down)),
            (0.62, perch(**up)), (0.74, perch(**down)), (1.10, perch()), (1.6, perch())]
    return sample_track(keys, D)

def flight_pose(w, bob=0.0, **kw):
    return pose(w, body_t=(0, bob, 0), legs="tucked", neck=(-8, 0, 0), head=(6, 0, 0), **kw)

def anim_fly():
    D = 0.40
    n = int(D*FPS)
    frames = []
    for f in range(n+1):
        ph = (f/n) % 1.0
        w = flap_wing(ph)
        bob = -0.010*math.cos(2*math.pi*(ph - 0.30))  # body rises during the downstroke
        p = flight_pose(w, bob=bob, tail=(-3*math.sin(2*math.pi*ph), 0, 0))
        p.pop("_ground", None); frames.append(p)
    return frames

def anim_glide():
    D = 2.0
    n = int(D*FPS); frames = []
    for f in range(n+1):
        t = f/n; s = math.sin(2*math.pi*t)
        w = ext(flap=8 + 2.5*s, sweep=-3, twist=2 + 1.5*math.sin(2*math.pi*t + 1), elbow=-6, wrist=10 + 3*s, wflap=4)
        wr = ext(flap=8 - 2.5*s, sweep=-3, twist=2 - 1.5*math.sin(2*math.pi*t + 1), elbow=-6, wrist=10 - 3*s, wflap=4)
        p = flight_pose(w, wingR=wr, bob=0.002*s, tail=(-2, 0, 4*s), body=(0, 0, -5*s))
        p.pop("_ground", None); frames.append(p)
    return frames

def anim_takeoff():
    D = 0.75
    crouch = pose(blend_wing(FOLD, FLAP_KEYS[0][1], 0.25), body=(8, 0, 0), neck=(-6, 0, 0), head=(4, 0, 0),
                  tail=(-10, 0, 0), body_t=(0, -0.018, 0), legs=(-43, 70, -35))
    keys = [
        (0.00, perch()),
        (0.14, crouch),
        (0.27, pose(FLAP_KEYS[0][1], body=(-12, 0, 0), neck=(-6, 0, 0), body_t=(0, 0.012, 0), legs=(22, -10, 30), tail=(-8, 0, 0))),
        (0.40, pose(FLAP_KEYS[2][1], body=(-8, 0, 0), neck=(-8, 0, 0), body_t=(0, 0.02, 0), legs=(45, 0, -20))),
        (0.56, pose(FLAP_KEYS[3][1], body=(-4, 0, 0), neck=(-8, 0, 0), head=(6, 0, 0), body_t=(0, 0.004, 0), legs=(70, 0, -40))),
        (0.75, flight_pose(FLAP_KEYS[0][1], bob=-0.010*math.cos(2*math.pi*(0 - 0.30)))),
    ]
    keys[0][1]["_ground"] = 1.0
    for _, p in keys[1:]: p["_ground"] = 0.0
    return sample_track(keys, D)

def anim_land():
    D = 1.1
    flare_w = ext(flap=42, sweep=-28, twist=-26, elbow=-10, wrist=14, wflap=-6)
    back_w = ext(flap=-28, sweep=-32, twist=-20, elbow=-6, wrist=8, wflap=-10)
    touch_w = ext(flap=62, sweep=6, twist=-10, elbow=-30, wrist=40)
    keys = [
        (0.00, flight_pose(GLIDE)),
        (0.22, pose(flare_w, body=(-38, 0, 0), neck=(20, 0, 0), head=(10, 0, 0), legs=(-30, 10, 0), tail=(-18, 0, 0))),
        (0.38, pose(back_w, body=(-42, 0, 0), neck=(22, 0, 0), head=(10, 0, 0), legs=(-10, 0, 10), tail=(-20, 0, 0))),
        (0.55, pose(flare_w, body=(-36, 0, 0), neck=(18, 0, 0), head=(8, 0, 0), legs=(20, 5, 0), tail=(-14, 0, 0))),
        (0.70, pose(touch_w, body=(-14, 0, 0), neck=(4, 0, 0), head=(4, 0, 0), legs=(-14, 40, -10),
                    body_t=(0, -0.012, 0), tail=(-4, 0, 0), ground=True)),
        (0.88, pose(blend_wing(FOLD, touch_w, 0.35), body=(-24, 0, 0), neck=(16, 0, 0), head=(6, 0, 0), tail=(-8, 0, 0), ground=True)),
        (1.10, perch()),
    ]
    return sample_track(keys, D)

ANIMS = {
    "Crow_Idle": anim_idle,
    "Crow_Peck": anim_peck,
    "Crow_TakeOff": anim_takeoff,
    "Crow_Fly": anim_fly,
    "Crow_Glide": anim_glide,
    "Crow_Land": anim_land,
}
