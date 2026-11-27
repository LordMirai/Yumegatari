import numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from crowlib import *

COL = {"feather": np.array([0.16, 0.17, 0.22]), "beak": np.array([0.30, 0.30, 0.30]), "eye": np.array([0.9, 0.75, 0.2])}
LIGHT = np.array([0.4, 0.8, 0.45]); LIGHT /= np.linalg.norm(LIGHT)

_packed = None
def packed():
    global _packed
    if _packed is None:
        m = build_crow()
        _packed = {k: pack_part(p) for k, p in m.parts.items()}
    return _packed

def draw(ax, pose, elev=15, azim=-60, title=None, lim=0.32, center=(0, 0.15, 0)):
    S = skin_matrices(pose)
    polys, cols = [], []
    for mat, (V, N, J, Wt, T) in packed().items():
        P = skin(V, J, Wt, S)
        for t in T:
            tri = P[t]
            n = np.cross(tri[1]-tri[0], tri[2]-tri[0]); nn = np.linalg.norm(n)
            if nn < 1e-12: continue
            sh = 0.35 + 0.65*abs(n.dot(LIGHT))/nn
            # map gltf (x, y-up, z-fwd) -> plot (x=z fwd, y=x, z=up)
            polys.append(tri[:, [2, 0, 1]]); cols.append(np.clip(COL[mat]*sh*1.6, 0, 1))
    pc = Poly3DCollection(polys, facecolors=cols, edgecolors=(0, 0, 0, 0.15), linewidths=0.2)
    ax.add_collection3d(pc)
    cx, cy, cz = center
    ax.set_xlim(cz-lim, cz+lim); ax.set_ylim(cx-lim, cx+lim); ax.set_zlim(cy-lim*0.75, cy+lim*0.75)
    ax.set_box_aspect((1, 1, 0.75)); ax.view_init(elev=elev, azim=azim); ax.set_axis_off()
    if title: ax.set_title(title, fontsize=9)

def sheet(poses, path, views=((15, -60),), lim=0.32, titles=None):
    n = len(poses); v = len(views)
    fig = plt.figure(figsize=(3.2*n, 3.0*v), dpi=110)
    for j, (el, az) in enumerate(views):
        for i, p in enumerate(poses):
            ax = fig.add_subplot(v, n, j*n+i+1, projection="3d")
            draw(ax, p, el, az, titles[i] if (titles and j == 0) else None, lim)
    plt.tight_layout(); fig.savefig(path); plt.close(fig)

if __name__ == "__main__":
    sheet([{}], "/home/claude/crow/rest.png", views=((15, -60), (90, -90), (0, 0), (5, -90)), lim=0.36)
