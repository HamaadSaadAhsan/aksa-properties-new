"""Architect site plan (1:500, rendered at 10 px/m) -> site geometry in site-local metres.
Site frame: origin at the client's coordinate (midpoint between the two blocks), u = drawing right (bearing 164.2°),
v = drawing down (bearing 254.2°)."""
import json, numpy as np, cv2
from PIL import Image
a=np.array(Image.open('site10.png').convert('RGB')).astype(int)
AX,AY=1332.5,1029.3
toUV=lambda x,y:[round((x-AX)/10,2),round((y-AY)/10,2)]
def col(c,t=4): return ((abs(a[...,0]-c[0])<t)&(abs(a[...,1]-c[1])<t)&(abs(a[...,2]-c[2])<t)).astype(np.uint8)
ol=col((145,165,82))
n,l,st,cen=cv2.connectedComponentsWithStats(ol)
trees=[toUV(*cen[i]) for i in range(1,n) if 60<st[i,4]<400 and 0.5<st[i,2]/max(1,st[i,3])<2]
out={'anchor_px':[AX,AY],'bearing_up':74.2,'blocks':[toUV(805.06,1029.3),toUV(1860.0,1029.3)],'block_size':[89.2,64.9],
     'trees':trees,
     'commercial':{'u0':(1005-AX)/10,'u1':(1662-AX)/10,'v0':(59-AY)/10,'v1':(243-AY)/10},
     'pavilions':[{'u0':(2107-AX)/10,'u1':(2217-AX)/10,'v0':(157-AY)/10,'v1':(250-AY)/10,'h':3.4},
                  {'u0':(2243-AX)/10,'u1':(2302-AX)/10,'v0':(77-AY)/10,'v1':(236-AY)/10,'h':3.6}],
     'frame_px':[159,53,2551,1852]}
json.dump(out,open('site.json','w'))
print(len(trees),'trees; commercial',out['commercial'])
