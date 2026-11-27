import json, struct, numpy as np
from crowlib import *
from anims import ANIMS, FPS

MATS = {
    "feather": {"name": "M_Crow_Feathers", "pbrMetallicRoughness": {"baseColorFactor": [0.018, 0.019, 0.026, 1], "metallicFactor": 0.0, "roughnessFactor": 0.42}, "doubleSided": True},
    "beak":    {"name": "M_Crow_BeakLegs", "pbrMetallicRoughness": {"baseColorFactor": [0.035, 0.035, 0.035, 1], "metallicFactor": 0.0, "roughnessFactor": 0.55}},
    "eye":     {"name": "M_Crow_Eyes", "pbrMetallicRoughness": {"baseColorFactor": [0.006, 0.006, 0.006, 1], "metallicFactor": 0.0, "roughnessFactor": 0.08}},
}

class Buf:
    def __init__(self): self.data = bytearray(); self.views = []; self.acc = []
    def add(self, arr, ctype, typ, target=None, minmax=False):
        while len(self.data) % 4: self.data.append(0)
        b = arr.tobytes(); off = len(self.data); self.data += b
        v = {"buffer": 0, "byteOffset": off, "byteLength": len(b)}
        if target: v["target"] = target
        self.views.append(v)
        a = {"bufferView": len(self.views)-1, "componentType": ctype, "count": int(arr.shape[0]), "type": typ}
        if minmax:
            a["min"] = [float(x) for x in np.atleast_1d(arr.min(axis=0))]
            a["max"] = [float(x) for x in np.atleast_1d(arr.max(axis=0))]
        self.acc.append(a); return len(self.acc)-1

FLOAT, U16, U32 = 5126, 5123, 5125
B = Buf()
mesh = build_crow()

# nodes: 0 = scene root "Crow", 1 = mesh node, 2.. = joints
nodes = [{"name": "Crow", "children": [1, 2]}, {"name": "SK_Crow", "mesh": 0, "skin": 0}]
JN = {}
for i, (n, p, pos) in enumerate(BONES):
    JN[n] = 2 + i
for n, p, pos in BONES:
    nd = {"name": n, "translation": [float(x) for x in local_offset(n)]}
    kids = [JN[c] for c, pp, _ in BONES if pp == n]
    if kids: nd["children"] = kids
    nodes.append(nd)

prims, materials = [], []
for k, (mat, part) in enumerate(mesh.parts.items()):
    V, N, J, Wt, T = pack_part(part)
    materials.append(MATS[mat])
    prims.append({"attributes": {
        "POSITION": B.add(V, FLOAT, "VEC3", 34962, True),
        "NORMAL": B.add(N, FLOAT, "VEC3", 34962),
        "JOINTS_0": B.add(J, U16, "VEC4", 34962),
        "WEIGHTS_0": B.add(Wt, FLOAT, "VEC4", 34962)},
        "indices": B.add(T.reshape(-1).astype(np.uint32), U32, "SCALAR", 34963),
        "material": k})

ibm = []
for n, p, pos in BONES:
    m = np.eye(4); m[:3, 3] = -pos; ibm.append(m.flatten(order="F"))
ibm_acc = B.add(np.array(ibm, np.float32), FLOAT, "MAT4")

animations = []
for name, fn in ANIMS.items():
    frames = fn()
    times = np.arange(len(frames), dtype=np.float32) / FPS
    tin = B.add(times.reshape(-1, 1), FLOAT, "SCALAR", minmax=True)
    samplers, channels = [], []
    for n, p, pos in BONES:
        if n == "root": continue
        Q = np.array([f.get(n, np.array([0, 0, 0, 1.0])) for f in frames], np.float32)
        for i in range(1, len(Q)):
            if Q[i].dot(Q[i-1]) < 0: Q[i] = -Q[i]
        samplers.append({"input": tin, "output": B.add(Q, FLOAT, "VEC4"), "interpolation": "LINEAR"})
        channels.append({"sampler": len(samplers)-1, "target": {"node": JN[n], "path": "rotation"}})
        if n == "body":
            Tr = np.array([local_offset("body") + f.get("body_t", np.zeros(3)) for f in frames], np.float32)
            samplers.append({"input": tin, "output": B.add(Tr, FLOAT, "VEC3"), "interpolation": "LINEAR"})
            channels.append({"sampler": len(samplers)-1, "target": {"node": JN[n], "path": "translation"}})
    animations.append({"name": name, "samplers": samplers, "channels": channels})

gltf = {
    "asset": {"version": "2.0", "generator": "Yumegatari procedural crow"},
    "scene": 0, "scenes": [{"name": "Scene", "nodes": [0]}],
    "nodes": nodes,
    "meshes": [{"name": "SK_Crow", "primitives": prims}],
    "materials": materials,
    "skins": [{"name": "Crow_Skeleton", "joints": [JN[n] for n, _, _ in BONES], "skeleton": JN["root"],
               "inverseBindMatrices": ibm_acc}],
    "animations": animations,
    "accessors": B.acc, "bufferViews": B.views,
    "buffers": [{"byteLength": len(B.data)}],
}
js = json.dumps(gltf, separators=(",", ":")).encode()
js += b" " * ((4 - len(js) % 4) % 4)
bin_ = bytes(B.data) + b"\0" * ((4 - len(B.data) % 4) % 4)
out = struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(js) + 8 + len(bin_))
out += struct.pack("<II", len(js), 0x4E4F534A) + js + struct.pack("<II", len(bin_), 0x004E4942) + bin_
open("SK_Crow.glb", "wb").write(out)
tris = sum(len(p["t"]) for p in mesh.parts.values())
print("bones", len(BONES), "tris", tris, "anims", [(a["name"]) for a in animations], "bytes", len(out))
