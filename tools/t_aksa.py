import asyncio, sys
from playwright.async_api import async_playwright
S="/home/claude/aksa/src/peek/"
async def route(r):
    u=r.request.url
    if 'motion.js' in u and 'jsdelivr' in u: await r.fulfill(path="/home/claude/aksa/tools/motion.js",content_type="application/javascript")
    elif 'fonts.g' in u: await r.fulfill(body="",content_type="text/css")
    elif u.endswith('.html'): 
        await r.fulfill(path="/home/claude/aksa"+u.split('8778')[1],content_type="text/html; charset=utf-8")
    else: await r.continue_()
async def main(w=1440,h=810,tag='d'):
    async with async_playwright() as p:
        b=await p.chromium.launch(args=["--use-gl=angle","--use-angle=swiftshader","--enable-unsafe-swiftshader","--ignore-gpu-blocklist","--autoplay-policy=no-user-gesture-required"])
        c=await b.new_context(viewport={"width":w,"height":h}); await c.route("**/*",route)
        pg=await c.new_page(); errs=[]
        pg.on("pageerror", lambda e: errs.append("ERR "+str(e)[:300]))
        pg.on("console", lambda m: errs.append("C "+m.text[:200]) if m.type=="error" else None)
        await pg.goto("http://localhost:8778/site/index.html")
        await pg.wait_for_timeout(1200); await pg.screenshot(path=S+f"{tag}0_loader.png")
        await pg.wait_for_function("window.__aksa && __aksa.state==='mp' && !__aksa.busy",timeout=180000)
        await pg.wait_for_timeout(1500); await pg.screenshot(path=S+f"{tag}1_mp.png")
        await pg.mouse.move(w*.5,h*.45); await pg.wait_for_timeout(900); await pg.screenshot(path=S+f"{tag}2_hover.png")
        await pg.click("#next"); await pg.wait_for_function("!__aksa.busy",timeout=30000); await pg.wait_for_timeout(500)
        print("hash", await pg.evaluate("location.hash"))
        await pg.evaluate("__aksa.enterClose()")
        await pg.wait_for_function("__aksa.state==='close' && !__aksa.busy",timeout=40000); await pg.wait_for_timeout(600)
        await pg.mouse.move(w*.5,h*.4); await pg.wait_for_timeout(900); await pg.screenshot(path=S+f"{tag}3_close.png")
        await pg.mouse.click(w*.5,h*.4); await pg.wait_for_timeout(1600); await pg.screenshot(path=S+f"{tag}4_plan.png")
        await pg.evaluate("(()=>{const u=__aksa.DATA.units.find(u=>u.floor===3&&u.status==='available');__aksa.openPlan(u.tower,u.floor,u.id);})()"); await pg.wait_for_timeout(1500)
        await pg.screenshot(path=S+f"{tag}5_unit.png")
        await pg.click("#u-tour"); await pg.wait_for_timeout(3500); await pg.screenshot(path=S+f"{tag}6_tour.png")
        await pg.click("#btn-close"); await pg.wait_for_timeout(2200)
        await pg.keyboard.press("Escape"); await pg.wait_for_timeout(600)
        await pg.click("#btn-close"); await pg.wait_for_function("__aksa.state==='mp' && !__aksa.busy",timeout=40000)
        await pg.click("#crumbs button[data-go='loc']"); await pg.wait_for_function("__aksa.state==='loc' && !__aksa.busy",timeout=40000); await pg.wait_for_timeout(2200)
        await pg.screenshot(path=S+f"{tag}7_loc.png")
        await pg.evaluate("document.querySelector('#loc').scrollTop=2000"); await pg.wait_for_timeout(800); await pg.screenshot(path=S+f"{tag}8_loc2.png")
        await pg.click("#loc-gallery button"); await pg.wait_for_timeout(1000); await pg.screenshot(path=S+f"{tag}9_lb.png")
        await pg.keyboard.press("Escape"); await pg.wait_for_timeout(500)
        await pg.click("#crumbs button[data-go='gal']"); await pg.wait_for_function("__aksa.state==='gal' && !__aksa.busy",timeout=40000); await pg.wait_for_timeout(1500)
        await pg.screenshot(path=S+f"{tag}11_gal.png"); print("hash", await pg.evaluate("location.hash"))
        await pg.click("#gal .gal-tabs button:nth-child(4)"); await pg.wait_for_timeout(900); await pg.screenshot(path=S+f"{tag}12_galc.png")
        await pg.click("#gal .gal-grid button"); await pg.wait_for_timeout(1000); await pg.screenshot(path=S+f"{tag}13_gallb.png")
        await pg.keyboard.press("Escape"); await pg.wait_for_timeout(500)
        await pg.click("#crumbs button[data-go='mp']"); await pg.wait_for_function("__aksa.state==='mp' && !__aksa.busy",timeout=40000)
        await pg.evaluate("__aksa.openPano('courtyard')"); await pg.wait_for_function("__aksa.state==='pano'",timeout=40000); await pg.wait_for_timeout(1500)
        await pg.screenshot(path=S+f"{tag}10_pano.png")
        print("\n".join(errs[:15]))
        await b.close()
if __name__=="__main__":
    a=sys.argv[1:]; asyncio.run(main(int(a[0]),int(a[1]),a[2]) if a else main())
