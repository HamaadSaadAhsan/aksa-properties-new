import sys, json, os
sys.path.insert(0,'/home/claude/aksa/tools'); os.chdir('/home/claude/aksa/tools')
from drv import sync_playwright, open_page, save
names=sys.argv[1:]
with sync_playwright() as p:
    b,pg=open_page(p)
    for n in names:
        d=json.load(open(f'/home/claude/aksa/cam/{n}.json'));w,h=d.get('size',[1600,900])
        pg.evaluate("s=>R.size(s[0],s[1])",[w,h]);pg.evaluate("c=>R.cam(c)",d['cam'])
        for mode in ('blocks','floors'):
            save(pg.evaluate("m=>R.mask(m)",mode),f'/home/claude/aksa/cam/{n}_{mode}.png')
    b.close()
