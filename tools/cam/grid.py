import sys
from PIL import Image, ImageDraw
def grid(src,out,box=None,step=50,scale=1.0):
    im=Image.open(src).convert('RGB')
    if box: im=im.crop(box)
    ox,oy=(box[0],box[1]) if box else (0,0)
    if scale!=1: im=im.resize((int(im.width*scale),int(im.height*scale)))
    d=ImageDraw.Draw(im)
    for X in range((ox//step)*step,ox+int(im.width/scale)+1,step):
        x=(X-ox)*scale
        d.line([(x,0),(x,im.height)],fill=(255,0,255) if X%100==0 else (0,255,255),width=1)
        if X%100==0: d.text((x+2,2),str(X),fill=(255,0,255))
    for Y in range((oy//step)*step,oy+int(im.height/scale)+1,step):
        y=(Y-oy)*scale
        d.line([(0,y),(im.width,y)],fill=(255,0,255) if Y%100==0 else (0,255,255),width=1)
        if Y%100==0: d.text((2,y+2),str(Y),fill=(255,0,255))
    im.save(out,quality=90)
if __name__=='__main__':
    a=sys.argv; box=tuple(map(int,a[3].split(','))) if len(a)>3 else None
    grid(a[1],a[2],box,int(a[4]) if len(a)>4 else 50,float(a[5]) if len(a)>5 else 1.0)
