import json, math, sys, numpy as np, cv2
SC=json.load(open('/home/claude/aksa/tools/scene/scene.json')); PL=SC['plot']; GY=0.8
TH=math.radians(-74.2); C,S=math.cos(TH),math.sin(TH)
def W(u,v,y):  # site-local -> world (x,y,z)
    return [PL['x']+u*C+v*S, GY+y, PL['z']-u*S+v*C]
def solve(pts, size=(1600,900), fs=None):
    obj=np.array([W(*p[0]) for p in pts],np.float64); img=np.array([p[1] for p in pts],np.float64)
    w,h=size; best=None
    for f in (fs or np.arange(500,6000,20)):
        K=np.array([[f,0,w/2],[0,f,h/2],[0,0,1]],np.float64)
        ok,rv,tv=cv2.solvePnP(obj,img,K,None,flags=cv2.SOLVEPNP_ITERATIVE if len(pts)>=6 else cv2.SOLVEPNP_EPNP)
        if not ok: continue
        ok,rv,tv=cv2.solvePnP(obj,img,K,None,rv,tv,True,cv2.SOLVEPNP_ITERATIVE)
        pr,_=cv2.projectPoints(obj,rv,tv,K,None);e=np.sqrt(((pr.reshape(-1,2)-img)**2).sum(1)).mean()
        Rm,_=cv2.Rodrigues(rv);Cw=(-Rm.T@tv).ravel()
        if Cw[1]<GY: continue
        if best is None or e<best[0]: best=(e,f,rv,tv)
    e,f,rv,tv=best;Rm,_=cv2.Rodrigues(rv);Cw=(-Rm.T@tv).ravel()
    K=np.array([[f,0,w/2],[0,f,h/2],[0,0,1]]);pr,_=cv2.projectPoints(obj,rv,tv,K,None)
    fov=2*math.degrees(math.atan(h/2/f))
    # three.js basis: right=R0, up=-R1, back=-R2
    basis=np.stack([Rm[0],-Rm[1],-Rm[2]],1)
    return dict(err=float(e),f=float(f),fov=fov,pos=Cw.tolist(),basis=basis.T.tolist(),res=(pr.reshape(-1,2)-img).round(1).tolist())
if __name__=='__main__':
    d=json.load(open(sys.argv[1])); r=solve([(p['w'],p['i']) for p in d['pts']],tuple(d.get('size',[1600,900])))
    print(json.dumps({k:r[k] for k in ('err','f','fov','pos')}),'\n',r['res'])
    d['cam']=r; json.dump(d,open(sys.argv[1],'w'),indent=1)
