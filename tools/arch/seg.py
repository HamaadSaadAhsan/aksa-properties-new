import re, json, sys, numpy as np, cv2
from PIL import Image
K=50.8/72  # px per pt at 20 px/m
def labels(n):
    h=open(n+'.bbox.html').read()
    ws=re.findall(r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">([^<]*)</word>',h)
    ws=[(float(a),float(b),float(c),float(d),w) for a,b,c,d,w in ws]
    out=[]
    for i,(x0,y0,x1,y1,w) in enumerate(ws):
        if not w.startswith('Fraç'): continue
        # gather nearby words (within 60pt box) to find code/type/area/id
        near=[v for v in ws if abs(v[1]-y0)<40 and abs(v[0]-x0)<90]
        txt=' '.join(v[4] for v in sorted(near,key=lambda v:(round(v[1]/4),v[0])))
        out.append({'x':(x0+x1)/2*K,'y':(y0+y1)/2*K,'txt':txt})
    return out
def parse(t):
    m=re.search(r'([A-C]\d[A-Z])\s*-\s*(T\d)',t); a=re.search(r'A=\s*(\d+,\d+)',t); f=re.search(r'Fra\S*\s*([A-Z]{1,2})\s*-\s*([A-Za-z/]+)',t)
    return (m.group(1) if m else None, m.group(2) if m else None, float(a.group(1).replace(',','.')) if a else None, f.group(1) if f else None, f.group(2) if f else None)
if __name__=='__main__':
    n=sys.argv[1]
    L=labels(n)
    for l in L[:8]: print(round(l['x']),round(l['y']),parse(l['txt']),'|',l['txt'][:120])
