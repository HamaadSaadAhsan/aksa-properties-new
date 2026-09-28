import numpy as np, cv2, json
from PIL import Image
from seg2 import seg
def footprint(n, close=31):
    res,lab,a=seg(n)
    r,g,b=a[...,0],a[...,1],a[...,2]; H,W=r.shape
    grey=((abs(r-g)<8)&(abs(g-b)<8)&(r>60)&(r<150)).astype(np.uint8)
    thick=cv2.morphologyEx(grey,cv2.MORPH_OPEN,np.ones((3,3),np.uint8))
    corr=(((abs(r-236)<6)&(abs(g-226)<6)&(abs(b-196)<8))|((abs(r-221)<6)&(abs(g-220)<6)&(abs(b-193)<8))).astype(np.uint8)
    units=np.isin(lab,[x[4] for x in res if x[3]>20]).astype(np.uint8)
    m=thick|corr|units
    m[:, int(W*0.9):]=0
    m=cv2.morphologyEx(m,cv2.MORPH_CLOSE,np.ones((close,close),np.uint8))
    cs,hier=cv2.findContours(m,cv2.RETR_CCOMP,cv2.CHAIN_APPROX_SIMPLE)
    hier=hier[0]; big=max(range(len(cs)),key=lambda i:cv2.contourArea(cs[i]) if hier[i][3]==-1 else 0)
    outer=cv2.approxPolyDP(cs[big],6,True).reshape(-1,2)
    holes=[cv2.approxPolyDP(cs[j],6,True).reshape(-1,2) for j in range(len(cs)) if hier[j][3]==big and cv2.contourArea(cs[j])>20000]
    return outer,holes,res,lab,a
if __name__=='__main__':
    out={}
    for n in ['04_Piso_1','07_Piso_Recuado','03_R_Cha_o']:
        o,h,res,lab,a=footprint(n)
        print(n,'outer pts',len(o),'area m2',cv2.contourArea(o)/400,'holes',[ (len(x),cv2.contourArea(x)/400) for x in h])
        vis=a.astype(np.uint8).copy()
        cv2.polylines(vis,[o],True,(255,0,0),5);[cv2.polylines(vis,[x],True,(0,0,255),5) for x in h]
        Image.fromarray(vis).resize((457,520)).save(f'fp_{n}.png')
        out[n]={'outer':o.tolist(),'holes':[x.tolist() for x in h]}
    json.dump(out,open('footprints.json','w'))
