"""Procedural low-poly crow: skeleton, skinned mesh, keyframed animations, GLB export.
glTF convention: meters, +Y up, crow faces +Z, crow's left wing on +X.
"""
import numpy as np, json, struct, math

# ---------------- quaternion helpers (x, y, z, w) ----------------
def qaxis(axis, deg):
    a = math.radians(deg) / 2
    ax = np.asarray(axis, float); ax = ax / np.linalg.norm(ax)
    return np.array([*(ax * math.sin(a)), math.cos(a)])

def qmul(a, b):
    x1, y1, z1, w1 = a; x2, y2, z2, w2 = b
    return np.array([w1*x2 + x1*w2 + y1*z2 - z1*y2,
                     w1*y2 - x1*z2 + y1*w2 + z1*x2,
                     w1*z2 + x1*y2 - y1*x2 + z1*w2,
                     w1*w2 - x1*x2 - y1*y2 - z1*z2])

def qinv(q): return np.array([-q[0], -q[1], -q[2], q[3]])

def qmat(q):
    x, y, z, w = q
    return np.array([[1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
                     [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)],
                     [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]])

def matq(m):
    t = np.trace(m)
    if t > 0:
        s = math.sqrt(t + 1) * 2
        q = [(m[2,1]-m[1,2])/s, (m[0,2]-m[2,0])/s, (m[1,0]-m[0,1])/s, s/4]
    elif m[0,0] > m[1,1] and m[0,0] > m[2,2]:
        s = math.sqrt(1 + m[0,0] - m[1,1] - m[2,2]) * 2
        q = [s/4, (m[0,1]+m[1,0])/s, (m[0,2]+m[2,0])/s, (m[2,1]-m[1,2])/s]
    elif m[1,1] > m[2,2]:
        s = math.sqrt(1 + m[1,1] - m[0,0] - m[2,2]) * 2
        q = [(m[0,1]+m[1,0])/s, s/4, (m[1,2]+m[2,1])/s, (m[0,2]-m[2,0])/s]
    else:
        s = math.sqrt(1 + m[2,2] - m[0,0] - m[1,1]) * 2
        q = [(m[0,2]+m[2,0])/s, (m[1,2]+m[2,1])/s, s/4, (m[1,0]-m[0,1])/s]
    q = np.array(q); return q / np.linalg.norm(q)

def R(x=0, y=0, z=0):
    """Local rotation: yaw about Y, then pitch about X, then roll about Z (degrees)."""
    return qmul(qmul(qaxis([0,1,0], y), qaxis([1,0,0], x)), qaxis([0,0,1], z))

def W(flap=0, sweep=0, twist=0, fold=0):
    """Left-wing local rotation. flap>0 = up, sweep>0 = back, twist>0 = leading edge down,
    fold = in-plane rotation (about wing normal); used for elbow (neg) / wrist (pos)."""
    return qmul(qmul(qaxis([0,1,0], sweep + fold), qaxis([0,0,1], flap)), qaxis([1,0,0], twist))

def qmirror(q):  # mirror a left-side local rotation to the right side (reflect across x=0)
    return np.array([q[0], -q[1], -q[2], q[3]])

def frame_quat(span, lead):
    X = np.asarray(span, float); X /= np.linalg.norm(X)
    Z = np.asarray(lead, float); Z = Z - Z.dot(X) * X; Z /= np.linalg.norm(Z)
    Y = np.cross(Z, X)
    return matq(np.column_stack([X, Y, Z]))

# ---------------- skeleton ----------------
BONES = []  # (name, parent, world_pos)
def bone(n, p, pos): BONES.append((n, p, np.array(pos, float)))

bone("root", None, (0, 0, 0))
bone("body", "root", (0, 0.13, 0))
bone("neck", "body", (0, 0.165, 0.09))
bone("head", "neck", (0, 0.205, 0.135))
bone("tail", "body", (0, 0.128, -0.12))
for s, sx in (("l", 1), ("r", -1)):
    bone(f"upperarm_{s}", "body", (0.045*sx, 0.17, 0.05))
    bone(f"lowerarm_{s}", f"upperarm_{s}", (0.165*sx, 0.17, 0.045))
    bone(f"hand_{s}", f"lowerarm_{s}", (0.295*sx, 0.17, 0.04))
    bone(f"thigh_{s}", "body", (0.025*sx, 0.10, 0.0))
    bone(f"calf_{s}", f"thigh_{s}", (0.025*sx, 0.075, 0.005))
    bone(f"foot_{s}", f"calf_{s}", (0.025*sx, 0.012, 0.012))

BI = {b[0]: i for i, b in enumerate(BONES)}
BPOS = {b[0]: b[2] for b in BONES}
BPAR = {b[0]: b[1] for b in BONES}
def local_offset(n):
    p = BPAR[n]
    return BPOS[n] - (BPOS[p] if p else 0)

# ---------------- mesh building ----------------
class Mesh:
    def __init__(self):
        self.parts = {}  # material -> dict(v, w, t, smooth)
    def part(self, mat):
        return self.parts.setdefault(mat, {"v": [], "w": [], "t": []})
    def add(self, mat, verts, weights, tris):
        p = self.part(mat); o = len(p["v"])
        p["v"] += [np.array(v, float) for v in verts]
        p["w"] += list(weights)
        p["t"] += [(a+o, b+o, c+o) for a, b, c in tris]

def orient_outward(verts, tris, center_fn):
    out = []
    for a, b, c in tris:
        n = np.cross(verts[b]-verts[a], verts[c]-verts[a])
        cen = (verts[a]+verts[b]+verts[c])/3
        if n.dot(cen - center_fn(cen)) < 0: out.append((a, c, b))
        else: out.append((a, b, c))
    return out

def loft(mesh, mat, stations, segs=14, front_cap=None, back_cap=None):
    """stations: (z, yc, rx, ry_top, ry_bot, weights)"""
    verts, wts, tris = [], [], []
    for (z, yc, rx, rt, rb, w) in stations:
        for k in range(segs):
            a = 2*math.pi*k/segs
            s = math.sin(a)
            verts.append(np.array([rx*math.cos(a), yc + (rt if s > 0 else rb)*s, z])); wts.append(w)
    n = len(stations)
    for i in range(n-1):
        for k in range(segs):
            a = i*segs + k; b = i*segs + (k+1) % segs
            c = (i+1)*segs + k; d = (i+1)*segs + (k+1) % segs
            tris += [(a, b, d), (a, d, c)]
    if back_cap is not None:
        verts.append(np.array(back_cap)); wts.append(stations[0][5]); bc = len(verts)-1
        tris += [(bc, (k+1) % segs, k) for k in range(segs)]
    if front_cap is not None:
        verts.append(np.array(front_cap)); wts.append(stations[-1][5]); fc = len(verts)-1
        base = (n-1)*segs
        tris += [(fc, base+k, base+(k+1) % segs) for k in range(segs)]
    zs = np.array([s[0] for s in stations]); ys = np.array([s[1] for s in stations])
    def center(p):
        return np.array([0, np.interp(p[2], zs, ys), p[2]])
    tris = orient_outward(verts, tris, center)
    mesh.add(mat, verts, wts, tris)

def tube(mesh, mat, p0, p1, r0, r1, w, segs=6, cap=True):
    p0, p1 = np.array(p0, float), np.array(p1, float)
    d = p1 - p0; L = np.linalg.norm(d); d /= L
    up = np.array([0, 1, 0]) if abs(d[1]) < 0.9 else np.array([1, 0, 0])
    u = np.cross(d, up); u /= np.linalg.norm(u); v = np.cross(d, u)
    verts, tris = [], []
    for p, r in ((p0, r0), (p1, r1)):
        for k in range(segs):
            a = 2*math.pi*k/segs
            verts.append(p + r*(math.cos(a)*u + math.sin(a)*v))
    for k in range(segs):
        a, b = k, (k+1) % segs
        tris += [(a, b, segs+b), (a, segs+b, segs+a)]
    if cap:
        verts.append(p1 + d*r1*0.5); t = len(verts)-1
        tris += [(t, segs+k, segs+(k+1) % segs) for k in range(segs)]
    def center(p):
        s = np.clip((p-p0).dot(d), 0, L); return p0 + d*s
    tris = orient_outward(verts, tris, center)
    ws = w if isinstance(w, list) else [w]*len(verts)
    mesh.add(mat, verts, ws, tris)

def sphere(mesh, mat, c, r, w, seg=8, ring=6):
    c = np.array(c, float); verts, tris = [], []
    for i in range(ring+1):
        th = math.pi*i/ring
        for k in range(seg):
            ph = 2*math.pi*k/seg
            verts.append(c + r*np.array([math.sin(th)*math.cos(ph), math.cos(th), math.sin(th)*math.sin(ph)]))
    for i in range(ring):
        for k in range(seg):
            a = i*seg+k; b = i*seg+(k+1) % seg; cc = (i+1)*seg+k; d = (i+1)*seg+(k+1) % seg
            tris += [(a, b, d), (a, d, cc)]
    tris = orient_outward(verts, tris, lambda p: c)
    mesh.add(mat, verts, [w]*len(verts), tris)

def feather(mesh, mat, root, direction, length, w_root, w_tip, curl, weight, normal=(0, 1, 0), segs=4):
    """Flat tapered feather strip (double-sided material)."""
    root = np.array(root, float); d = np.array(direction, float); d /= np.linalg.norm(d)
    n = np.array(normal, float); side = np.cross(n, d); side /= np.linalg.norm(side)
    verts, tris = [], []
    for i in range(segs+1):
        t = i/segs
        wdt = (w_root*(1-t) + w_tip*t) * (0.35 if i == segs else 1.0)
        p = root + d*length*t + n*curl*t*t
        verts += [p + side*wdt/2, p - side*wdt/2]
    verts.append(root + d*length*1.07 + n*curl*1.1)  # pointed tip
    for i in range(segs):
        a, b, c, e = 2*i, 2*i+1, 2*i+2, 2*i+3
        tris += [(a, c, b), (b, c, e)]
    t = len(verts)-1
    tris.append((2*segs, t, 2*segs+1))
    ws = weight if isinstance(weight, list) else [weight]*len(verts)
    mesh.add(mat, verts, ws, tris)

def wing_weights(x):
    """Spanwise skin weights for the left wing (x = distance out from body)."""
    def blend(x, a, b): return float(np.clip((x-a)/(b-a), 0, 1))
    t1 = blend(x, 0.150, 0.180); t2 = blend(x, 0.280, 0.310)
    w = {"upperarm": (1-t1), "lowerarm": t1*(1-t2), "hand": t2}
    return {k: v for k, v in w.items() if v > 1e-4}

def build_wing(mesh, side):
    sx = 1 if side == "l" else -1
    def W_(d): return {f"{k}_{side}": v for k, v in d.items()}
    def P(x, y, z): return (x*sx, y, z)
    # secondaries + coverts surface: lead / mid / trail per span station, serrated trailing edge
    verts, wts, tris = [], [], []
    xs = np.arange(0.045, 0.300 + 1e-6, 0.0105)
    for i, x in enumerate(xs):
        bz = np.interp(x, [0.045, 0.165, 0.295], [0.05, 0.045, 0.04])
        lead_z = bz + 0.014
        chord = np.interp(x, [0.045, 0.12, 0.30], [0.085, 0.125, 0.11])
        chord += 0.012 if i % 2 == 0 else -0.004  # feather tips / notches
        y = 0.17
        verts += [P(x, y, lead_z), P(x, y + 0.007, lead_z - chord*0.35), P(x, y, lead_z - chord)]
        w = W_(wing_weights(x)); wts += [w, w, w]
    for i in range(len(xs)-1):
        for j in range(2):
            a = 3*i+j; b = a+1; c = 3*(i+1)+j; d = c+1
            tris += [(a, c, b), (b, c, d)] if sx > 0 else [(a, b, c), (b, d, c)]
    mesh.add("feather", verts, wts, tris)
    # hand coverts (base of primaries)
    verts, wts, tris = [], [], []
    hx = np.linspace(0.295, 0.40, 6)
    for x in hx:
        lz = np.interp(x, [0.295, 0.40], [0.054, 0.03]); ch = np.interp(x, [0.295, 0.40], [0.085, 0.035])
        verts += [P(x, 0.171, lz), P(x, 0.176, lz - ch*0.4), P(x, 0.171, lz - ch)]
        w = W_(wing_weights(x)); wts += [w, w, w]
    for i in range(len(hx)-1):
        for j in range(2):
            a = 3*i+j; b = a+1; c = 3*(i+1)+j; d = c+1
            tris += [(a, c, b), (b, c, d)] if sx > 0 else [(a, b, c), (b, d, c)]
    mesh.add("feather", verts, wts, tris)
    # primaries: 7 "finger" feathers fanning from back (inner) to outward (outer)
    for i in range(7):
        t = i/6
        x = 0.30 + 0.095*t
        z = np.interp(x, [0.295, 0.40], [0.035, 0.02])
        ang = math.radians(-62 + 57*t)          # 0 = straight out, negative = toward the back
        d = (math.cos(ang)*sx, 0, math.sin(ang))
        length = 0.115 + 0.05*math.sin(math.pi*min(1, t*1.15))
        feather(mesh, "feather", P(x, 0.172 + 0.0018*i, z), d, length, 0.026, 0.014, 0.012,
                {f"hand_{side}": 1.0})

def build_crow():
    m = Mesh()
    B = lambda **k: k
    st = [
        (-0.150, 0.128, 0.010, 0.008, 0.008, B(tail=1.0)),
        (-0.125, 0.130, 0.028, 0.022, 0.024, B(tail=0.4, body=0.6)),
        (-0.075, 0.135, 0.048, 0.045, 0.050, B(body=1.0)),
        (-0.015, 0.140, 0.060, 0.055, 0.066, B(body=1.0)),
        (0.040, 0.150, 0.058, 0.052, 0.062, B(body=1.0)),
        (0.080, 0.163, 0.046, 0.040, 0.048, B(body=0.6, neck=0.4)),
        (0.110, 0.183, 0.034, 0.030, 0.034, B(neck=1.0)),
        (0.135, 0.205, 0.036, 0.034, 0.034, B(neck=0.3, head=0.7)),
        (0.160, 0.215, 0.040, 0.038, 0.036, B(head=1.0)),
        (0.182, 0.214, 0.033, 0.030, 0.028, B(head=1.0)),
        (0.197, 0.210, 0.016, 0.014, 0.013, B(head=1.0)),
    ]
    loft(m, "feather", st, segs=14, front_cap=(0, 0.209, 0.203), back_cap=(0, 0.128, -0.156))
    # beak: tapered, slightly hooked
    bw = {"head": 1.0}
    loft(m, "beak", [
        (0.188, 0.207, 0.0115, 0.0105, 0.0100, bw),
        (0.215, 0.205, 0.0085, 0.0085, 0.0065, bw),
        (0.240, 0.201, 0.0050, 0.0055, 0.0035, bw),
    ], segs=8, front_cap=(0, 0.194, 0.258), back_cap=None)
    for sx in (1, -1):
        sphere(m, "eye", (0.031*sx, 0.223, 0.170), 0.0072, {"head": 1.0})
    # tail fan
    for i in range(6):
        t = (i - 2.5) / 2.5
        d = (math.sin(math.radians(9*t)), 0, -1)
        feather(m, "feather", (0.014*t, 0.129 + 0.0012*abs(t), -0.115), d, 0.165 - 0.012*abs(t),
                0.032, 0.03, -0.006, {"tail": 1.0})
    # wings
    build_wing(m, "l"); build_wing(m, "r")
    # legs
    for s, sx in (("l", 1), ("r", -1)):
        tube(m, "beak", (0.025*sx, 0.085, 0.004), (0.025*sx, 0.012, 0.012), 0.0062, 0.0042, {f"calf_{s}": 1.0}, cap=False)
        ank = np.array([0.025*sx, 0.010, 0.012])
        for ang, ln in ((-28, 0.034), (0, 0.042), (28, 0.034)):
            a = math.radians(ang)
            tip = ank + np.array([math.sin(a)*ln*sx, -0.0075, math.cos(a)*ln])
            tube(m, "beak", ank, tip, 0.0034, 0.0016, {f"foot_{s}": 1.0}, segs=5)
        tube(m, "beak", ank, ank + np.array([0, -0.0075, -0.028]), 0.0034, 0.0016, {f"foot_{s}": 1.0}, segs=5)
    return m

# ---------------- posing / skinning ----------------
def world_mats(pose):
    """pose: {bone: quat} plus optional 'body_t': translation offset. Returns {bone: 4x4 world}."""
    mats = {}
    for n, p, pos in BONES:
        L = np.eye(4)
        L[:3, :3] = qmat(pose.get(n, np.array([0, 0, 0, 1.0])))
        off = local_offset(n).copy()
        if n == "body": off = off + pose.get("body_t", np.zeros(3))
        L[:3, 3] = off
        mats[n] = (mats[p] @ L) if p else L
    return mats

def skin_matrices(pose):
    W = world_mats(pose)
    out = np.zeros((len(BONES), 4, 4))
    for n, _, pos in BONES:
        ibm = np.eye(4); ibm[:3, 3] = -pos
        out[BI[n]] = W[n] @ ibm
    return out

def pack_part(part):
    V = np.array(part["v"]); T = np.array(part["t"], dtype=np.uint32)
    J = np.zeros((len(V), 4), np.uint16); Wt = np.zeros((len(V), 4), np.float32)
    for i, w in enumerate(part["w"]):
        items = sorted(w.items(), key=lambda kv: -kv[1])[:4]
        tot = sum(v for _, v in items)
        for k, (bn, v) in enumerate(items):
            J[i, k] = BI[bn]; Wt[i, k] = v/tot
    # smooth normals
    N = np.zeros_like(V)
    tri = V[T]
    fn = np.cross(tri[:, 1]-tri[:, 0], tri[:, 2]-tri[:, 0])
    for k in range(3): np.add.at(N, T[:, k], fn)
    N /= np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-9)
    return V.astype(np.float32), N.astype(np.float32), J, Wt, T

def skin(V, J, Wt, S):
    Vh = np.c_[V, np.ones(len(V))]
    out = np.zeros((len(V), 3))
    for k in range(4):
        M = S[J[:, k]]
        out += Wt[:, k:k+1] * np.einsum("nij,nj->ni", M, Vh)[:, :3]
    return out
