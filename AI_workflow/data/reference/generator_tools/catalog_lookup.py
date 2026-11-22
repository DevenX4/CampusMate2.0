import re,json,collections
cat=open('/home/claude/src/catalog.txt').read().split('\f')
d=json.load(open('official_parsed.json'))
codes=set()
for p,ss in d.items():
    for s in ss:
        for r in s['rows']:
            if r['course_code'] in ('AUDIT','ELECTIVE','OPEN'): r['title']=r['course_code']+' '+r['title']; r['course_code']=None
            if r['course_code']: codes.add(r['course_code'])
        for v in s['lists'].values():
            for x in v: codes.add(x['course_code'])
json.dump(d,open('official_parsed.json','w'),indent=1)
occ=collections.defaultdict(list)
for i,p in enumerate(cat):
    y=re.search(r'for (?:the )?year\s*(\d{4}\s*-\s*\d{4})',p); year=y.group(1).replace(' ','') if y else None
    for ln in p.split('\n'):
        for c in codes:
            if re.search(r'(?<![0-9A-Z])'+re.escape(c)+r'(?![0-9A-Z])',ln):
                m=re.match(r'\s*(\d+)\s+(\d{3})\s+(.+?\))\s+(\S+)\s+(.+?)\s*$',ln)
                occ[c].append(dict(academic_year=year,source_page=i+1,sr_no=int(m[1]) if m else None,program_code=m[2] if m else None,program_name=re.sub(r'\s+',' ',m[3]) if m else None,listed_name=m[5].strip() if m else None,raw=ln.strip()[:160]))
missing=sorted(codes-set(occ))
print('codes',len(codes),'found',len(occ),'missing',missing)
for c in ['2CEIT602','2CEIT303','3CEIT307','2CEIT78PE7']: print(c,[(o['academic_year'],o['program_code'],o['source_page']) for o in occ[c]])
bad=[(c,o['raw']) for c in occ for o in occ[c] if not o['program_code']]
print('unparsed',len(bad),bad[:8])
json.dump(occ,open('catalog_occ.json','w'),indent=1)
# programs 202/402 rows
rows=json.load(open('/home/claude/src/catalog_rows.json'))
print([ (r['year'],r['code'],r['name'],r['page']) for r in rows if r['prog_code'] in('202','402')])
