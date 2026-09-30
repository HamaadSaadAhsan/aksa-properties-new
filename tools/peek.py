import sys, json, time
from drv import sync_playwright, open_page, save
views=json.loads(sys.argv[1])
with sync_playwright() as p:
    t=time.time();b,pg=open_page(p);print('init',round(time.time()-t,1))
    pg.evaluate("s=>R.size(s[0],s[1])",[1280,720])
    for i,v in enumerate(views):
        t=time.time();pg.evaluate("v=>R.view(v)",v);save(pg.evaluate("R.shot(0)"),f'/home/claude/aksa/src/peek/v{i}.jpg');print(i,round(time.time()-t,1))
        if v.get('mask'):save(pg.evaluate("m=>R.mask(m)",v['mask']),f'/home/claude/aksa/src/peek/m{i}.png')
    print(json.dumps(pg.evaluate("R.data()")['panos']))
    b.close()
