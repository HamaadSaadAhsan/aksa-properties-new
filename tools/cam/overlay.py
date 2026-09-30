import sys, json, os, numpy as np, cv2
sys.path.insert(0,'/home/claude/aksa/tools'); os.chdir('/home/claude/aksa/tools')
from drv import sync_playwright, open_page, save
from PIL import Image
names=sys.argv[1:]
with sync_playwright() as p:
    b,pg=open_page(p)
    for n in names:
        d=json.load(open(f'/home/claude/aksa/cam/{n}.json'));w,h=d.get('size',[1600,900])
        pg.evaluate("s=>R.size(s[0],s[1])",[w,h]);pg.evaluate("c=>R.cam(c)",d['cam'])
        for mode in ('dev','floors'):
            save(pg.evaluate("m=>R.mask(m)",mode),f'/home/claude/aksa/cam/{n}_{mode}.png')
        save(pg.evaluate("R.shot(0)"),f'/home/claude/aksa/cam/{n}_model.jpg')
        im=cv2.imread('/home/claude/aksa/site/media/gallery/'+d['img']);im=cv2.resize(im,(w,h))
        m=cv2.imread(f'/home/claude/aksa/cam/{n}_floors.png')
        e=cv2.Canny(m,10,30);e=cv2.dilate(e,np.ones((2,2),np.uint8))
        im[e>0]=(0,0,255)
        md=cv2.imread(f'/home/claude/aksa/cam/{n}_dev.png');ed=cv2.dilate(cv2.Canny(md,10,30),np.ones((2,2),np.uint8));im[ed>0]=(255,255,0)
        cv2.imwrite(f'/home/claude/aksa/cam/{n}_ov.jpg',im)
    b.close()
