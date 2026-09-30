import asyncio, sys
from playwright.async_api import async_playwright
S="/home/claude/aksa/src/peek/"
async def route(r):
    u=r.request.url
    if 'motion' in u and 'jsdelivr' in u: await r.fulfill(path="/home/claude/aksa/tools/motion.js",content_type="application/javascript")
    elif 'fonts.g' in u: await r.fulfill(body="",content_type="text/css")
    else: await r.continue_()
async def main(w=1440,h=810,tag='v'):
    async with async_playwright() as p:
        b=await p.chromium.launch(args=["--use-gl=angle","--use-angle=swiftshader","--enable-unsafe-swiftshader","--autoplay-policy=no-user-gesture-required"])
        c=await b.new_context(viewport={"width":w,"height":h}); await c.route("**/*",route)
        pg=await c.new_page(); errs=[]
        pg.on("pageerror", lambda e: errs.append("ERR "+str(e)[:300]))
        pg.on("console", lambda m: errs.append("C "+m.text[:200]) if m.type=="error" else None)
        await pg.goto("http://localhost:8778/site/index.html")
        await pg.wait_for_function("window.__aksa && __aksa.state==='mp' && !__aksa.busy",timeout=120000)
        await pg.wait_for_timeout(1200); await pg.screenshot(path=S+f"{tag}1_mp.png")
        # hover the first block outline
        box=await pg.evaluate("(()=>{const e=document.querySelector('#hits .hit');const r=e.getBoundingClientRect();return [r.x+r.width/2,r.y+r.height/2]})()")
        await pg.mouse.move(*box); await pg.wait_for_timeout(700); await pg.screenshot(path=S+f"{tag}2_hover.png")
        await pg.click("#next"); await pg.wait_for_function("!__aksa.busy",timeout=30000); await pg.wait_for_timeout(600)
        await pg.screenshot(path=S+f"{tag}3_next.png"); print("hash", await pg.evaluate("location.hash"))
        await pg.click("#prev"); await pg.wait_for_function("!__aksa.busy",timeout=30000)
        await pg.evaluate("__aksa.enterClose()"); await pg.wait_for_function("__aksa.state==='close' && !__aksa.busy",timeout=30000); await pg.wait_for_timeout(600)
        box=await pg.evaluate("(()=>{const e=[...document.querySelectorAll('#hits .hit')][3];const r=e.getBoundingClientRect();return [r.x+r.width/2,r.y+r.height/2]})()")
        await pg.mouse.move(*box); await pg.wait_for_timeout(700); await pg.screenshot(path=S+f"{tag}4_close.png")
        await pg.evaluate("__aksa.openPlan('S',3)"); await pg.wait_for_timeout(1500)
        await pg.evaluate("(()=>{const e=document.querySelector('#plan-svg .u');e.dispatchEvent(new MouseEvent('click',{bubbles:true}))})()"); await pg.wait_for_timeout(900)
        await pg.screenshot(path=S+f"{tag}5_plan.png")
        await pg.keyboard.press("Escape"); await pg.wait_for_timeout(600)
        await pg.click("#crumbs button[data-go='amen']"); await pg.wait_for_function("__aksa.state==='amen' && !__aksa.busy",timeout=30000); await pg.wait_for_timeout(1500)
        await pg.screenshot(path=S+f"{tag}6_amen.png")
        await pg.click("#amen-grid .amen-card"); await pg.wait_for_timeout(1000); await pg.screenshot(path=S+f"{tag}7_amenlb.png")
        await pg.keyboard.press("Escape"); await pg.wait_for_timeout(400)
        await pg.click("#crumbs button[data-go='mp']"); await pg.wait_for_function("__aksa.state==='mp' && !__aksa.busy",timeout=30000); await pg.wait_for_timeout(800)
        await pg.evaluate("(()=>{const e=document.querySelector('.apin');e.dispatchEvent(new MouseEvent('click',{bubbles:true}))})()"); await pg.wait_for_timeout(1000)
        await pg.screenshot(path=S+f"{tag}8_pinlb.png")
        print("\n".join(errs[:15])); await b.close()
asyncio.run(main())
