import json, numpy as np, cv2
from PIL import Image, ImageFilter
fp=json.load(open('footprints.json')); site=json.load(open('site.json'))
CX,CY,PXM=896.5,1060,20
conv=lambda pts:[[round((x-CX)/PXM,2),round((y-CY)/PXM,2)] for x,y in pts]
arch={'p1':{'outer':conv(fp['04_Piso_1']['outer']),'holes':[conv(h) for h in fp['04_Piso_1']['holes']]},
      'rec':{'outer':conv(fp['07_Piso_Recuado']['outer']),'holes':[conv(h) for h in fp['07_Piso_Recuado']['holes']]},
      'site':site,'FH':2.9,'BASE':0.6}
X0,Y0,X1,Y1=site['frame_px'];AX,AY=site['anchor_px']
arch['frame']=[(X0-AX)/10,(Y0-AY)/10,(X1-AX)/10,(Y1-AY)/10]
json.dump(arch,open('/home/claude/aksa/tools/scene/arch.json','w'))
im=np.array(Image.open('site10.png').convert('RGB'))[Y0:Y1,X0:X1].copy()
a=im.astype(int)
blk=(abs(a[...,0]-182)<3)&(abs(a[...,1]-182)<3)&(abs(a[...,2]-182)<3)
im[blk]=(226,220,205)
red=(a[...,0]>140)&(a[...,1]<60)&(a[...,2]<60)
im[red]=(184,122,104)
black=(a.sum(-1)<90)
im[black]=(70,70,68)
white=(a[...,0]>250)&(a[...,1]>250)&(a[...,2]>250)
alpha=np.where(white,0,255).astype(np.uint8)
alpha=cv2.morphologyEx(alpha,cv2.MORPH_OPEN,np.ones((5,5),np.uint8))
H,W=alpha.shape;e=40
ramp=np.minimum.outer(np.minimum(np.arange(H),np.arange(H)[::-1]),np.minimum(np.arange(W),np.arange(W)[::-1]))
alpha=(alpha*np.clip(ramp/e,0,1)).astype(np.uint8)
alpha=np.array(Image.fromarray(alpha).filter(ImageFilter.GaussianBlur(2)))
Image.fromarray(np.dstack([im,alpha])).save('/home/claude/aksa/tools/scene/siteplan.png',optimize=True)
print('frame m',arch['frame'],'p1 pts',len(arch['p1']['outer']),'rec pts',len(arch['rec']['outer']))
