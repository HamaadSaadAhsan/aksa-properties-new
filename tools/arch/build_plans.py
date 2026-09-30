"""Architect floor plans (PDF, 1:100) -> plan images + unit polygons for the site."""
import json, math, numpy as np, cv2, subprocess, os
from PIL import Image
from seg2 import seg
OUT='/home/claude/aksa/site/media/plans'; os.makedirs(OUT,exist_ok=True)
PXM=20                                  # seg resolution: px per metre
X0,Y0,X1,Y1=186,106,1607,2014            # crop (20 px/m), P1 building bbox + 3 m
S=30                                     # plan image resolution: px per metre
FLOORS=[('03_R_Cha_o',[0],'Ground floor'),('04_Piso_1',[1],'Level 1'),('05_Piso_2_e_3',[2,3],'Level 2–3'),('06_Piso_4',[4],'Level 4'),('07_Piso_Recuado',[5],'Level 5 · penthouse')]
BEAR={'left':254,'right':74,'top':344,'bottom':164}
def compass(b):
    return ['N','NNE','NE','ENE','E','ESE','SE','SSE','S','SSW','SW','WSW','W','WNW','NW','NNW'][int(((b%360)+11.25)//22.5)%16]
plans={}; floors={}
for n,fl,name in FLOORS:
    dpi=S*72/28.3465
    subprocess.run(f'pdftoppm -r {dpi:.3f} -png -singlefile -x {int(X0*S/PXM)} -y {int(Y0*S/PXM)} -W {int((X1-X0)*S/PXM)} -H {int((Y1-Y0)*S/PXM)} {n}.pdf /tmp/plan_{n}',shell=True,check=True)
    im=Image.open(f'/tmp/plan_{n}.png').convert('RGB'); im.save(f'{OUT}/{n}.jpg',quality=80,optimize=True,progressive=True)
    res,lab,a=seg(n)
    units=[]
    seen=set()
    for frac,typ,area,netA,l in res:
        if netA<=20 or l in seen: continue
        seen.add(l)
        m=(lab==l).astype(np.uint8)
        m=cv2.morphologyEx(m,cv2.MORPH_CLOSE,np.ones((5,5),np.uint8))
        cs,_=cv2.findContours(m,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        c=max(cs,key=cv2.contourArea); c=cv2.approxPolyDP(c,2.0,True).reshape(-1,2)
        poly=[[round((x-X0)/PXM,2),round((y-Y0)/PXM,2)] for x,y in c]
        M=cv2.moments(m); cx,cy=M['m10']/M['m00'],M['m01']/M['m00']
        # which outer facades does the unit touch? (distance of its pixels to the block edges)
        ys,xs=np.nonzero(m); sides=[]
        if xs.min()<246+60: sides.append('left')
        if xs.max()>1547-60: sides.append('right')
        if ys.min()<166+60: sides.append('top')
        if ys.max()>1954-60: sides.append('bottom')
        court = not (xs.min()<600 and xs.max()>1200) and len(sides)<2 or True
        units.append({'frac':frac,'type':typ,'area':area,'net':round(float(netA),1),'poly':poly,'cx':round((cx-X0)/PXM,2),'cy':round((cy-Y0)/PXM,2),
                      'aspect':[compass(BEAR[s]) for s in sides]})
    # number units clockwise around the ring, starting top-left
    CX,CY=(X1-X0)/2/PXM,(Y1-Y0)/2/PXM
    units.sort(key=lambda u:(math.atan2(u['cy']-CY,u['cx']-CX)+math.pi*0.75)%(2*math.pi))
    for k,u in enumerate(units): u['n']=k+1
    for f in fl: floors[f]={'name':name,'image':f'media/plans/{n}.jpg','units':units}
    print(n,len(units),im.size,os.path.getsize(f'{OUT}/{n}.jpg')//1024,'KB')
json.dump({'viewBox':[0,0,round((X1-X0)/PXM,2),round((Y1-Y0)/PXM,2)],'floors':floors,'crop':[X0,Y0,X1,Y1],'pxm':PXM},open('plans.json','w'))
