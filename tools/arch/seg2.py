import json, sys, numpy as np, cv2
from PIL import Image
U=json.load(open('units.json'))
def seg(n, out=None):
    a=np.array(Image.open(f'p20_{n}.png').convert('RGB')).astype(int)
    r,g,b=a[...,0],a[...,1],a[...,2]
    grey=(abs(r-g)<8)&(abs(g-b)<8)&(r>60)&(r<150)
    white=(r>246)&(g>246)&(b>246)
    corr=((abs(r-236)<6)&(abs(g-226)<6)&(abs(b-196)<8))|((abs(r-221)<6)&(abs(g-220)<6)&(abs(b-193)<8))
    red=(r>200)&(g<60)&(b<60)
    bar=(grey|white|corr).astype(np.uint8)
    bar=cv2.morphologyEx(bar,cv2.MORPH_CLOSE,np.ones((3,3),np.uint8))
    free=(1-bar).astype(np.uint8)
    nlab,lab=cv2.connectedComponents(free,connectivity=4)
    res=[]
    for u in U[n]:
        x,y=int(u['x']),int(u['y'])
        # find nearest free pixel
        best=None
        for rr in range(0,15):
            ys,xs=np.nonzero(free[max(0,y-rr):y+rr+1,max(0,x-rr):x+rr+1])
            if len(xs): best=(ys[0]+max(0,y-rr),xs[0]+max(0,x-rr));break
        l=lab[best] if best else 0
        area=(lab==l).sum()/400 if l else 0
        res.append((u['frac'],u['type'],u['area'],round(area,1),l))
    return res,lab,a
if __name__=='__main__':
    n=sys.argv[1]; res,lab,a=seg(n)
    for r in res: print(r)
    # visualize
    vis=(a*0.5).astype(np.uint8); rng=np.random.RandomState(1); cols=rng.randint(60,255,(lab.max()+1,3))
    ids=set(r[4] for r in res)
    for l in ids:
        if l: vis[lab==l]=cols[l]
    Image.fromarray(vis).resize((914,1040)).save('segvis.png')
