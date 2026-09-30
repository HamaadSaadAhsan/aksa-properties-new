import base64, time, json
from playwright.sync_api import sync_playwright
def save(url,path):
    open(path,'wb').write(base64.b64decode(url.split(',',1)[1]))
def open_page(p):
    b=p.chromium.launch(args=["--use-gl=angle","--use-angle=swiftshader","--enable-unsafe-swiftshader","--ignore-gpu-blocklist"])
    pg=b.new_page(viewport={"width":800,"height":450})
    pg.on("pageerror", lambda e: print("PAGEERR",e))
    pg.on("console", lambda m: print("C",m.text[:400]) if m.type=="error" else None)
    pg.goto("http://127.0.0.1:8777/"+__import__("os").environ.get("RENDER","render2.html"))
    pg.wait_for_function("window.ready===true",timeout=240000)
    return b,pg
