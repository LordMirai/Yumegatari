import sys, io, numpy as np, matplotlib.pyplot as plt
from PIL import Image
from preview import draw
from anims import ANIMS
def gif(name, path, views=((12,-60),(0,0)), step=1, lim=0.34):
    fr = ANIMS[name]()[::step]; imgs=[]
    for p in fr:
        fig = plt.figure(figsize=(3.2*len(views),3.0), dpi=80)
        for i,(e,a) in enumerate(views):
            ax=fig.add_subplot(1,len(views),i+1,projection="3d"); draw(ax,p,e,a,None,lim)
        fig.suptitle(name, fontsize=9); b=io.BytesIO(); fig.savefig(b,format="png"); plt.close(fig)
        imgs.append(Image.open(b).convert("P", palette=Image.ADAPTIVE))
    imgs[0].save(path, save_all=True, append_images=imgs[1:], duration=int(1000/30*step), loop=0)
    return fr
if __name__=="__main__":
    for n in sys.argv[1:]:
        gif(n, f"{n}.gif", step=1 if n in ("Crow_Fly","Crow_TakeOff") else 2)
