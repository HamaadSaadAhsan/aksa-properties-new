import pymupdf, re, json, math
K=50.8/72
def units(n):
    p=pymupdf.open(n+'.pdf')[0]
    L=[]
    for b in p.get_text('dict')['blocks']:
        for l in b.get('lines',[]):
            t=''.join(s['text'] for s in l['spans']).strip()
            x0,y0,x1,y1=l['bbox']; L.append((t,(x0+x1)/2,(y0+y1)/2))
    out=[]
    for t,x,y in L:
        m=re.match(r'Fra\S*\s*([A-Z]{1,2})\s*-\s*(\S+)',t)
        if not m: continue
        cand=[(math.hypot(x2-x,y2-y),t2) for t2,x2,y2 in L if re.match(r'[A-C]\d[A-Z]\s*-\s*T\d',t2)]
        code=min(cand)[1] if cand else ''
        acand=[(math.hypot(x2-x,y2-y),t2) for t2,x2,y2 in L if re.match(r'A=\s*\d+,\d+',t2) and math.hypot(x2-x,y2-y)<40]
        area=min(acand)[1] if acand else ''
        cm=re.match(r'([A-C]\d[A-Z])\s*-\s*(T\d)',code); am=re.search(r'(\d+,\d+)',area)
        out.append({'frac':m.group(1),'side':m.group(2),'code':cm.group(1) if cm else None,'type':cm.group(2) if cm else None,
                    'area':float(am.group(1).replace(',','.')) if am else None,'x':round(x*K,1),'y':round(y*K,1)})
    return out
if __name__=='__main__':
    R={}
    for n in ['03_R_Cha_o','04_Piso_1','05_Piso_2_e_3','06_Piso_4','07_Piso_Recuado']:
        u=units(n); R[n]=u
        import collections
        print(n,len(u),collections.Counter(x['type'] for x in u),'no area',sum(1 for x in u if not x['area']))
        print('  ',sorted(set((x['frac'],x['type'],x['area']) for x in u))[:40])
    json.dump(R,open('units.json','w'),indent=0)
