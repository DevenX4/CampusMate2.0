import re, json, collections
SYL='/home/claude/src/syllabus.txt'; CAT='/home/claude/src/catalog.txt'
syl=open(SYL).read().split('\f'); cat=open(CAT).read().split('\f')
ROMAN={'I':1,'II':2,'III':3,'IV':4,'V':5,'VI':6,'VII':7,'VIII':8}
PAGES={'B.TECH-IT':[(10,'I',None),(11,'II',None),(12,'III',None),(13,'IV',None),(14,'V',None),(15,'VI',None),(16,'VII',17),(18,'VIII',None)],
       'M.TECH-IT':[(104,'I',None),(105,'II',106),(107,'III',None),(108,'IV',None)]}
NUM=r'\d+\.\d\d'
ROW=re.compile(r'^\s{0,4}(\d{1,2})\s+(?:([0-9A-Z]{5,12})\s+)?(.+?)\s+('+NUM+r')\s+('+NUM+r')\s+('+NUM+r')\s+('+NUM+r')\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\d+)\s*$')
TOT=re.compile(r'^\s+('+NUM+r')\s+('+NUM+r')\s+('+NUM+r')\s+('+NUM+r')\s+(\d+)\s*$')
def mx(s): return None if s=='-' else int(s.split('/')[1])
def parse_page(pno):
    p=syl[pno-1]; L=p.split('\n')
    hdr={}
    hdr['date']=re.search(r'Date\s*:\s*(\S+)',p).group(1)
    hdr['effective_year']=re.search(r'Effective Year\s*(\S+)',p).group(1)
    for k,pat in [('total_course',r'Total Course\s*:\s*(\d+)'),('total_regular',r'Total Regular Course\s*:\s*(\d+)'),('total_elective',r'Total Elective Course\s*:\s*(\d+)'),('total_open',r'Total Open Course\s*:\s*(\d+)'),('total_audit',r'Total Audit Course\s*:\s*(\d+)')]:
        hdr[k]=int(re.search(pat,p).group(1))
    rows=[];tot=None;section=None;lists=collections.defaultdict(list);grp=None;last=None
    for ln in L:
        if 'List of Elective' in ln: section='elective';continue
        if 'List of Audit' in ln: section='audit';continue
        if 'List of open' in ln or 'List of Open' in ln: section='open';continue
        if 'Examination Grade' in ln: section='grade';continue
        if section is None:
            m=ROW.match(ln)
            if m:
                g=m.groups()
                r=dict(slot_no=int(g[0]),course_code=g[1],title=g[2].strip(),credit_th=float(g[3]),credit_pr=float(g[4]),credit_total=float(g[5]),contact_hours=float(g[6]),
                       exam_raw={'th_internal':g[7],'th_external':g[8],'pr_internal':g[9],'pr_external':g[10]},
                       th_internal_max=mx(g[7]),th_external_max=mx(g[8]),pr_internal_max=mx(g[9]),pr_external_max=mx(g[10]),total_marks=int(g[11]))
                rows.append(r);last=r;continue
            m=TOT.match(ln)
            if m and rows: tot=dict(credit_th=float(m[1]),credit_pr=float(m[2]),credit_total=float(m[3]),contact_hours=float(m[4]),total_marks=int(m[5]));last=None;continue
            s=ln.strip()
            if last and s and re.match(r'^\s{10,}[A-Z&]',ln) and not re.search(r'\d',s) and 'Teaching' not in s:
                last['title']+=' '+s; continue
            if not s: pass
        elif section in('elective','audit','open'):
            m=re.match(r'^\s*(?:([A-Z_]+(?:-[IVX]+)?)\s+)?([0-9A-Z]{5,12})\s+(.+?)\s*$',ln)
            if m and m[3] and not m[2].startswith('Group'):
                if m[1]: grp=m[1]
                if m[2] in ('Course',): continue
                lists[section].append(dict(group=grp,course_code=m[2],title=m[3].strip()))
    return hdr,rows,tot,dict(lists)
out={}
for prog,pages in PAGES.items():
    sems=[]
    for pno,sem,cont in pages:
        hdr,rows,tot,lists=parse_page(pno)
        sems.append(dict(semester=sem,semester_no=ROMAN[sem],source_page=pno,source_pages=[pno]+([cont] if cont else []),header=hdr,rows=rows,totals=tot,lists=lists))
    out[prog]=sems
# verification: sums
for prog,sems in out.items():
    for s in sems:
        rs=s['rows'];t=s['totals']
        sc=round(sum(r['credit_total'] for r in rs),2); sm=sum(r['total_marks'] for r in rs)
        ok = t and abs(sc-t['credit_total'])<0.01 and sm==t['total_marks']
        print(prog,s['semester'],'rows',len(rs),'credits',sc,'/',t and t['credit_total'],'marks',sm,'/',t and t['total_marks'],'OK' if ok else 'MISMATCH', {k:len(v) for k,v in s['lists'].items()})
json.dump(out,open('official_parsed.json','w'),indent=1)
