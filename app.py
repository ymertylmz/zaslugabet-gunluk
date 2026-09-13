import os
# -*- coding: utf-8 -*-
import re, html, time, sqlite3
from datetime import date, datetime
from zoneinfo import ZoneInfo
import requests
import cloudscraper
from bs4 import BeautifulSoup
import streamlit as st

st.set_page_config(page_title='ZaslugaBet Günlük Sinyal', page_icon='⚽', layout='wide', initial_sidebar_state='collapsed')
DB='zaslugabet_40_LIG_TEMIZ.db'
BASE='https://www.mackolik.com'
DAILY=BASE+'/perform/p0/ajax/components/competition/livescores/json'
EXACT={
 ('İspanya','LaLiga'):('Spain','La Liga'),('İspanya','LaLiga 2'):('Spain','Segunda División'),('İngiltere','Premier Lig'):('England','Premier League'),('İngiltere','Championship'):('England','Championship'),('İngiltere','1. Lig'):('England','League One'),('İngiltere','2. Lig'):('England','League Two'),('İngiltere','Ulusal Lig'):('England','National League'),('İtalya','Serie A'):('Italy','Serie A'),('Fransa','Ligue 1'):('France','Ligue 1'),('Fransa','Ligue 2'):('France','Ligue 2'),('Fransa','Ligue 3'):('France','National'),('Almanya','Bundesliga'):('Germany','Bundesliga'),('Almanya','2. Bundesliga'):('Germany','2. Bundesliga'),('Almanya','3. Lig'):('Germany','3. Liga'),('Portekiz','Premier Lig'):('Portugal','Primeira Liga'),('Türkiye','Trendyol Süper Lig'):('Turkey','Süper Lig'),('Finlandiya','Veikkausliiga'):('Finland','Veikkausliiga'),('Avusturya','2. Lig'):('Austria','2. Liga'),('Avusturya','Bundesliga'):('Austria','Bundesliga'),('Danimarka','Süper Lig'):('Denmark','Superliga'),('Danimarka','1. Lig'):('Denmark','1. Division'),('İsveç','Superettan'):('Sweden','Superettan'),('İsveç','Allsvenskan'):('Sweden','Allsvenskan'),('Norveç','Eliteserien'):('Norway','Eliteserien'),('Hollanda','Eredivisie'):('Netherlands','Eredivisie'),('Hollanda','Eerste Divisie'):('Netherlands','Eerste Divisie'),('İskoçya','Championship'):('Scotland','Championship'),('İskoçya','Championship Play-out'):('Scotland','Championship'),('İskoçya','Premiership'):('Scotland','Premiership'),('İskoçya','Premiership Play-out'):('Scotland','Premiership'),('Polonya','Ekstraklasa'):('Poland','Ekstraklasa'),('Belçika','Pro Lig'):('Belgium','Pro League'),('İrlanda Cumhuriyeti','Premier Lig'):('Ireland','Premier Division'),('Kuzey İrlanda','Premiership'):('Northern Ireland','Premiership'),('Kuzey İrlanda','Premiership Play-off'):('Northern Ireland','Premiership'),('Rusya','Premier Lig'):('Russia','Premier League'),('İsviçre','Süper Lig'):('Switzerland','Super League'),('Yunanistan','Süper Lig'):('Greece','Super League 1'),('Çin','Süper Lig'):('China','Super League'),('ABD','MLS'):('USA','MLS'),('Avrupa','Şampiyonlar Ligi'):('Europe','Şampiyonlar Ligi'),('Avrupa','Avrupa Ligi'):('Europe','Avrupa Ligi'),('Avrupa','Konferans Ligi'):('Europe','Konferans Ligi')}

HEAD={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36','Accept-Language':'tr-TR,tr;q=0.9,en;q=0.8','Referer':BASE+'/'}
SCRAPER=cloudscraper.create_scraper(browser={'browser':'chrome','platform':'windows','mobile':False})
def norm(s):
 s=str(s or '').lower()
 for a,b in {'ı':'i','ş':'s','ğ':'g','ü':'u','ö':'o','ç':'c','İ':'i'}.items(): s=s.replace(a,b)
 return re.sub(r'[^a-z0-9]+',' ',s).strip()
def odd(v):
 try:
  x=float(str(v).replace(',','.')); return x if 1.01<=x<=500 else None
 except:return None
def get(url,params=None,n=4):
 for i in range(n):
  try:
   r=requests.get(url,params=params,headers=HEAD,timeout=25)
   if r.status_code==200:return r
  except: pass
  time.sleep(.7+i*.5)
 return None
def home_away(m):
 name=str(m.get('matchName') or '')
 for sep in [' vs ',' - ',' v ']:
  p=name.split(sep,1)
  if len(p)==2:return p[0].strip(),p[1].strip()
 return str(m.get('homeTeamName') or ''),str(m.get('awayTeamName') or '')
def mtime(m):
 try:
  ts=float(m.get('mstUtc')); ts=ts/1000 if ts>1e10 else ts
  return datetime.fromtimestamp(ts,tz=ZoneInfo('UTC')).astimezone(ZoneInfo('Europe/Istanbul')).strftime('%H:%M')
 except:return ''
def slug(s): return re.sub(r'-+','-',re.sub(r'[^a-z0-9]+','-',norm(s))).strip('-') or 'x'
def parse_pair(html):
 if not html:
  return None,None,'SAYFA AÇILMADI'

 soup=BeautifulSoup(html,'lxml')
 text=' '.join(soup.stripped_strings)

 # 1) Görünen metin: "İlk Yarı/Maç Sonucu" başlığından sonraki ilk 2/1 ve 1/2
 variants=['ilk yari/mac sonucu','ilk yari mac sonucu','ilk yarı/maç sonucu','ilk yarı maç sonucu']
 nt=norm(text)
 positions=[nt.find(v) for v in variants if nt.find(v)>=0]
 if positions:
  pos=min(positions)
  chunk=nt[pos:pos+1800]
  m21=re.search(r'(?<!\d)2\s*/\s*1(?:\s|:|-)+(\d+(?:[.,]\d+)?)',chunk)
  m12=re.search(r'(?<!\d)1\s*/\s*2(?:\s|:|-)+(\d+(?:[.,]\d+)?)',chunk)
  if m21 and m12:
   return float(m21.group(1).replace(',','.')),float(m12.group(1).replace(',','.')),'İY/MS VAR'

 # 2) Market blokları
 for node in soup.find_all(['section','article','div','ul','li']):
  bt=' '.join(node.stripped_strings)
  nbt=norm(bt)
  if ('ilk yari/mac sonucu' in nbt or 'ilk yari mac sonucu' in nbt):
   m21=re.search(r'(?<!\d)2\s*/\s*1(?:\s|:|-)+(\d+(?:[.,]\d+)?)',nbt)
   m12=re.search(r'(?<!\d)1\s*/\s*2(?:\s|:|-)+(\d+(?:[.,]\d+)?)',nbt)
   if m21 and m12:
    return float(m21.group(1).replace(',','.')),float(m12.group(1).replace(',','.')),'İY/MS BLOK'

 # 3) Script/JSON içinde escaped market adı + oranlar
 raw=html.replace('\\u0130','İ').replace('\\u0131','ı').replace('\\/','/')
 nraw=norm(raw)
 for key in ['ilk yari/mac sonucu','ilk yari mac sonucu']:
  pos=nraw.find(key)
  if pos>=0:
   chunk=nraw[pos:pos+6000]
   # JSON biçimleri: "2/1":"21.30", label/value veya düz metin
   patterns21=[
    r'["\']?2/1["\']?\s*[:=]\s*["\']?(\d+(?:[.,]\d+)?)',
    r'["\']?(?:name|label|outcome)["\']?\s*:\s*["\']?2/1["\']?.{0,160}?["\']?(?:value|odd|odds|price)["\']?\s*:\s*["\']?(\d+(?:[.,]\d+)?)',
    r'2/1.{0,80}?(\d{1,3}(?:[.,]\d+)?)'
   ]
   patterns12=[
    r'["\']?1/2["\']?\s*[:=]\s*["\']?(\d+(?:[.,]\d+)?)',
    r'["\']?(?:name|label|outcome)["\']?\s*:\s*["\']?1/2["\']?.{0,160}?["\']?(?:value|odd|odds|price)["\']?\s*:\s*["\']?(\d+(?:[.,]\d+)?)',
    r'1/2.{0,80}?(\d{1,3}(?:[.,]\d+)?)'
   ]
   v21=v12=None
   for pat in patterns21:
    m=re.search(pat,chunk,re.S)
    if m: v21=float(m.group(1).replace(',','.')); break
   for pat in patterns12:
    m=re.search(pat,chunk,re.S)
    if m: v12=float(m.group(1).replace(',','.')); break
   if v21 is not None and v12 is not None:
    return v21,v12,'İY/MS JSON'

 return None,None,'İY/MS MARKET YOK'

def odds_page(mid,h,a):
 sl=f'{slug(h)}-vs-{slug(a)}'
 routes=[
  ('MACKOLIK-KARSILASTIRMA',f'https://www.mackolik.com/mac/{sl}/karsilastirma/{mid}'),
  ('MACKOLIK-MAC',f'https://www.mackolik.com/mac/{sl}/{mid}'),
  ('MACKOLIK-IDDAA',f'https://www.mackolik.com/mac/{sl}/iddaa/{mid}'),
  ('MACKOLIK-INDEX-IDDAA',f'https://www.mackolik.com/index.php/mac/{sl}/iddaa/{mid}'),
  ('SAHADAN-IDDAA-1',f'https://www.sahadan.com/mac/{sl}/{mid}/iddaa'),
  ('SAHADAN-IDDAA-2',f'https://www.sahadan.com/mac/{sl}/iddaa/{mid}'),
 ]
 last='ORAN ALINAMADI'
 for name,url in routes:
  try:
   r=SCRAPER.get(url,headers=HEAD,timeout=18,allow_redirects=True)
   if r.status_code!=200:
    last=f'{name} HTTP {r.status_code}'
    continue
   a21,a12,status=parse_pair(r.text)
   if a21 is not None and a12 is not None:
    return a21,a12,f'BULUNDU • {name}'
   last=f'{name} • {status} • {len(r.text):,}B'
  except Exception as e:
   last=f'{name} • {type(e).__name__}'
 return None,None,last


def bulletin_fetch(day):
 url='https://arsiv.mackolik.com/AjaxHandlers/ProgramDataHandler.ashx'
 params={
  'type':'6',
  'sortValue':'DATE',
  'day':day.strftime('%d.%m.%Y'),
  'sort':'-1',
  'sortDir':'-1',
  'groupId':'-1',
  'np':'1',
  'sport':'1'
 }
 try:
  r=SCRAPER.get(url,params=params,headers=HEAD,timeout=25,allow_redirects=True)
  return r.status_code,r.url,r.text or ''
 except Exception as e:
  return 0,'',f'ERROR: {type(e).__name__}: {e}'

def extract_bulletin_pair(html, home, away):
 if not html or html.startswith('ERROR:'):
  return None,None,'BÜLTEN YOK'
 soup=BeautifulSoup(html,'lxml')
 plain=' '.join(soup.stripped_strings)
 nplain=norm(plain)
 nh=norm(home); na=norm(away)

 # Önce takım isimlerinin yakınındaki alanı bul.
 positions=[]
 for key in [nh,na]:
  p=nplain.find(key)
  if p>=0: positions.append(p)
 if not positions:
  return None,None,'MAÇ BÜLTENDE BULUNAMADI'

 start=max(0,min(positions)-1200)
 end=min(len(nplain),max(positions)+6000)
 chunk=nplain[start:end]

 # Eğer İY/MS başlığı varsa onun çevresini tercih et.
 for mk in ['ilk yari/mac sonucu','ilk yari mac sonucu','iy/ms']:
  p=chunk.find(mk)
  if p>=0:
   chunk=chunk[p:p+2500]
   break

 pats21=[
  r'(?<!\d)2\s*/\s*1(?:\s|:|-)+(\d+(?:[.,]\d+)?)',
  r'["\']?2/1["\']?\s*[:=]\s*["\']?(\d+(?:[.,]\d+)?)'
 ]
 pats12=[
  r'(?<!\d)1\s*/\s*2(?:\s|:|-)+(\d+(?:[.,]\d+)?)',
  r'["\']?1/2["\']?\s*[:=]\s*["\']?(\d+(?:[.,]\d+)?)'
 ]
 v21=v12=None
 for p in pats21:
  m=re.search(p,chunk,re.S)
  if m:
   v21=float(m.group(1).replace(',','.')); break
 for p in pats12:
  m=re.search(p,chunk,re.S)
  if m:
   v12=float(m.group(1).replace(',','.')); break

 if v21 is not None and v12 is not None:
  return v21,v12,'BÜLTENDEN BULUNDU'
 return None,None,'MAÇ VAR • İY/MS ÇÖZÜLEMEDİ'

def bulletin_diag(day):
 code,url,html=bulletin_fetch(day)
 soup=BeautifulSoup(html,'lxml') if html else None
 plain=' '.join(soup.stripped_strings) if soup else ''
 nplain=norm(plain)
 return {
  'HTTP':code,
  'Boyut':len(html),
  'Son URL':url,
  'Galatasaray var mı':'EVET' if 'galatasaray' in nplain else 'HAYIR',
  'Kocaelispor var mı':'EVET' if 'kocaelispor' in nplain else 'HAYIR',
  'İY/MS metni':'EVET' if any(x in nplain for x in ['ilk yari/mac sonucu','ilk yari mac sonucu','iy/ms']) else 'HAYIR',
  '2/1 metni':'EVET' if re.search(r'(?<!\d)2\s*/\s*1(?!\d)',plain) else 'HAYIR',
  '1/2 metni':'EVET' if re.search(r'(?<!\d)1\s*/\s*2(?!\d)',plain) else 'HAYIR',
  'İlk 350 karakter':plain[:350]
 }


def raw_match_probe(html, team='Galatasaray'):
 raw=html or ''
 low=raw.lower()
 pos=low.find(team.lower())
 if pos<0:
  return {'Bulundu':'HAYIR','Alan adları':'','Ham parça':'Takım adı ham cevapta bulunamadı.'}
 lo=max(0,pos-1800); hi=min(len(raw),pos+3500)
 chunk=raw[lo:hi]
 fields=[]
 for x in re.findall(r'(?<![\w])([A-Za-z_][A-Za-z0-9_]{0,30})\s*:',chunk):
  if x not in fields: fields.append(x)
 return {
  'Bulundu':'EVET',
  'Pozisyon':pos,
  'Alan adları':', '.join(fields[:80]),
  'Ham parça':chunk
 }


def parse_program_rows(raw):
 rows=[]
 if not raw: return rows
 # Mackolik response: {m:[[...],[...]],...}
 # Extract bracketed match arrays conservatively.
 for m in re.finditer(r"\[(\d+),'([^']*)',(\d+),'([^']*)','([^']*)',", raw):
  start=m.start()
  depth=0; inq=False; esc=False; end=None
  for i,ch in enumerate(raw[start:],start):
   if inq:
    if esc: esc=False
    elif ch=='\\': esc=True
    elif ch=="'": inq=False
    continue
   if ch=="'": inq=True
   elif ch=='[': depth+=1
   elif ch==']':
    depth-=1
    if depth==0:
     end=i+1; break
  if end:
   txt=raw[start:end]
   # convert JS-ish single quotes to python literal safely
   import ast
   try:
    row=ast.literal_eval(txt.replace('{}',"'{}'"))
    rows.append(row)
   except Exception:
    pass
 return rows

def find_program_match(raw, home, away):
 for row in parse_program_rows(raw):
  try:
   if norm(str(row[1]))==norm(home) and norm(str(row[3]))==norm(away):
    return row
  except Exception:
   pass
 return None

def archive_htft_from_program(day, home, away):
 code,url,raw=bulletin_fetch(day)
 row=find_program_match(raw,home,away)
 if not row:
  return None,None,'BÜLTENDE MAÇ YOK',None,None
 # observed current program format: index 50 is archive Mackolik match id
 archive_id = row[50] if len(row)>50 else None
 if not archive_id:
  return None,None,'ARŞİV ID YOK',None,row
 archive_url=f'https://arsiv.mackolik.com/Match/Default.aspx?id={archive_id}'
 try:
  r=SCRAPER.get(archive_url,headers={
   **HEAD,
   'Referer':'https://arsiv.mackolik.com/Genis-Iddaa-Programi',
  },timeout=25,allow_redirects=True)
  html=r.text or ''
  soup=BeautifulSoup(html,'lxml')
  # Historical parser used iddaa-ms-h tables and "İlk Yarı / Maç Sonucu".
  for table in soup.find_all('table',class_=lambda x: x and 'iddaa-ms-h' in x):
   rows=table.find_all('tr')
   block=[]
   for tr in rows:
    vals=[td.get_text(" ",strip=True) for td in tr.find_all('td')]
    if vals: block.append(vals)
   if not block: continue
   title=' '.join(block[0])
   if 'İlk Yarı / Maç Sonucu' in title or 'İlk Yarı/Maç Sonucu' in title:
    vals=[]
    for rr in block[1:]:
     vals.extend(rr)
    clean=[]
    for v in vals:
     vv=v.replace(',','.')
     if re.fullmatch(r'\d+(?:\.\d+)?',vv):
      clean.append(float(vv))
    # Canonical 3x3 order: 1/1,1/X,1/2, X/1,X/X,X/2, 2/1,2/X,2/2
    if len(clean)>=9:
     return clean[6],clean[2],f'ARŞİV SAYFASI • ID {archive_id}',archive_url,row
  # text fallback
  txt=' '.join(soup.stripped_strings)
  nt=norm(txt)
  p=nt.find('ilk yari / mac sonucu')
  if p<0: p=nt.find('ilk yari/mac sonucu')
  if p>=0:
   chunk=txt[p:p+1800]
   nums=[float(x.replace(',','.')) for x in re.findall(r'(?<!\d)(\d{1,3}[.,]\d{1,2})(?!\d)',chunk)]
   if len(nums)>=9:
    return nums[6],nums[2],f'ARŞİV TEXT • ID {archive_id}',archive_url,row
  return None,None,f'ARŞİV AÇILDI AMA İY/MS YOK • HTTP {r.status_code} • {len(html):,}B',archive_url,row
 except Exception as e:
  return None,None,f'ARŞİV HATA • {type(e).__name__}: {e}',archive_url,row


def nesine_parse_htft(html):
 if not html:
  return None,None,'BOŞ CEVAP'
 soup=BeautifulSoup(html,'lxml')
 txt=' '.join(soup.stripped_strings)
 nt=norm(txt)

 # Nesine maç merkezi tablosu: İlk Yarı / Maç Sonucu
 pos=nt.find('ilk yari / mac sonucu')
 if pos<0: pos=nt.find('ilk yari/mac sonucu')
 if pos<0:
  return None,None,'İY/MS BAŞLIĞI YOK'

 chunk=txt[pos:pos+3500]
 # Direkt etiketlerden yakala.
 m21=re.search(r'(?<!\d)2\s*/\s*1\s+(\d+(?:[.,]\d+)?)',chunk,re.I)
 m12=re.search(r'(?<!\d)1\s*/\s*2\s+(\d+(?:[.,]\d+)?)',chunk,re.I)
 if m21 and m12:
  return float(m21.group(1).replace(',','.')),float(m12.group(1).replace(',','.')),'NESİNE İY/MS'

 # Tablo sırası fallback:
 # 1/1, X/1, 2/1, 1/X, X/X, 2/X, 1/2, X/2, 2/2
 labels=['1/1','X/1','2/1','1/X','X/X','2/X','1/2','X/2','2/2']
 vals={}
 for lab in labels:
  mm=re.search(re.escape(lab)+r'\s+(\d+(?:[.,]\d+)?)',chunk,re.I)
  if mm:
   vals[lab]=float(mm.group(1).replace(',','.'))
 if '2/1' in vals and '1/2' in vals:
  return vals['2/1'],vals['1/2'],'NESİNE TABLO'

 return None,None,'İY/MS VAR AMA ORAN AYRIŞMADI'

def nesine_probe(day, program_id, known_event_id=None):
 ymd=day.strftime('%Y%m%d')
 urls=[
  f'https://www.nesine.com/Iddaa/Mac-Merkezi/{ymd}/{program_id}',
  f'https://www.nesine.com/Iddaa/Mac-Merkezi/{ymd}/{program_id}/1',
 ]
 if known_event_id:
  urls.append(f'https://www.nesine.com/Iddaa/Mac-Merkezi/{ymd}/{program_id}/1/{known_event_id}')

 results=[]
 for url in urls:
  try:
   r=SCRAPER.get(url,headers={
    **HEAD,
    'Referer':'https://www.nesine.com/iddaa',
    'Accept-Language':'tr-TR,tr;q=0.9,en;q=0.8'
   },timeout=25,allow_redirects=True)
   a21,a12,st=nesine_parse_htft(r.text or '')
   results.append({
    'İstek URL':url,
    'HTTP':r.status_code,
    'Boyut':len(r.text or ''),
    'Son URL':r.url,
    '2/1':a21,
    '1/2':a12,
    'Durum':st
   })
   if a21 is not None and a12 is not None:
    return a21,a12,results
  except Exception as e:
   results.append({
    'İstek URL':url,'HTTP':'HATA','Boyut':0,'Son URL':'',
    '2/1':None,'1/2':None,'Durum':f'{type(e).__name__}: {e}'
   })
 return None,None,results

def tag(n,fp):
 if n>=20 and fp>=9:return '🟢 GÜÇLÜ'
 if n>=8 and fp>=7:return '🟡 TAKİP'
 return '⚪ ZAYIF'
def stats(con,o21,o12,country,league):
 if o21 is None or o12 is None:return None
 rows=con.execute('select match_date,country,league,home,away,ht_home,ht_away,ft_home,ft_away,htft,is_flip,mackolik_id from matches where odd_21=? and odd_12=? order by match_date desc',(o21,o12)).fetchall()
 n=len(rows); n21=sum(r[9]=='2/1' for r in rows); n12=sum(r[9]=='1/2' for r in rows); flips=sum(r[10]==1 for r in rows)
 same=[r for r in rows if r[1]==country and r[2]==league]; sameflip=sum(r[10]==1 for r in same)
 fp=100*flips/n if n else 0
 return {'n':n,'n21':n21,'n12':n12,'flips':flips,'fp':fp,'p21':100*n21/flips if flips else 0,'p12':100*n12/flips if flips else 0,'same':len(same),'sameflip':sameflip,'rows':rows}

st.markdown('''<style>.block-container{padding-top:1rem;max-width:1050px}.hero{background:#0b1220;padding:18px;border-radius:18px;color:white}.card{border:1px solid #263246;border-radius:16px;padding:14px;margin:9px 0}.muted{opacity:.7;font-size:.85rem}</style>''',unsafe_allow_html=True)
st.markdown('<div class="hero"><h2>⚽ ZaslugaBet Günlük Sinyal</h2><div>40 lig • Exact 2/1 + 1/2 eşleşmesi • Temiz tarihsel arşiv</div></div>',unsafe_allow_html=True)
DB_OK=False
DB_ERROR=''
DB_SIZE=0
DB_HEADER=''
DB_TABLES=[]
total=0
pairs=0
try:
 if not os.path.exists(DB):
  raise FileNotFoundError(f'DB bulunamadı: {DB}')
 DB_SIZE=os.path.getsize(DB)
 with open(DB,'rb') as _f:
  DB_HEADER=_f.read(16).decode('latin1',errors='replace')
 with sqlite3.connect(DB) as c:
  DB_TABLES=[x[0] for x in c.execute("select name from sqlite_master where type='table'").fetchall()]
  if 'matches' not in DB_TABLES:
   raise RuntimeError(f'matches tablosu yok. Tablolar: {DB_TABLES}')
  total=c.execute('select count(*) from matches').fetchone()[0]
  pairs=c.execute('select count(*) from matches where odd_21 is not null and odd_12 is not null').fetchone()[0]
 DB_OK=True
except Exception as e:
 DB_ERROR=f'{type(e).__name__}: {e}'

if DB_OK:
 c1,c2=st.columns(2)
 c1.metric('Arşiv',f'{total:,}'.replace(',','.'))
 c2.metric('Exact oranlı maç',f'{pairs:,}'.replace(',','.'))
 st.success(f'✅ DB SAĞLAM • {total:,} maç • {pairs:,} exact-pair oranlı maç')
else:
 st.error('🧱 VERİTABANI AÇILAMADI')
 st.code(
  f'Dosya: {DB}\n'
  f'Var mı: {os.path.exists(DB)}\n'
  f'Boyut: {DB_SIZE:,} byte\n'
  f'SQLite header: {DB_HEADER!r}\n'
  f'Tablolar: {DB_TABLES}\n'
  f'Hata: {DB_ERROR}'
 )
 st.info('Beklenen sağlam DB: 56.513 maç ve 46.200 adet 2/1+1/2 oranlı maç.')
 st.stop()





st.markdown("### 🚀 V13 Nesine Türkiye İddaa Testi")
st.caption("Mackolik arşiv sayfasını bırakıyoruz. Aynı program ID'siyle Nesine'nin yasal İddaa maç merkezinden 2/1 ve 1/2'yi doğrudan okumayı deniyoruz.")
if st.button("🚀 GALATASARAY-KOCAELİ NESİNE'DEN ÇEK",use_container_width=True):
 from datetime import date as _date
 with st.spinner("Nesine maç merkezi deneniyor..."):
  _n21,_n12,_nrows=nesine_probe(_date(2026,9,13),3126016,2259971)
 st.dataframe(_nrows,use_container_width=True,hide_index=True)
 if _n21 is not None:
  st.success(f"🔥 NESİNE ÇALIŞTI • 2/1 = {_n21:.2f} • 1/2 = {_n12:.2f}")
 else:
  st.error("Nesine sayfasından İY/MS çifti alınamadı.")

st.markdown("### 🧨 V12 Arşiv-ID Testi")
st.caption("Bültendeki maç kaydından Mackolik arşiv maç ID'sini alıp eski maç sayfasındaki 3×3 İlk Yarı/Maç Sonucu tablosunu doğrudan okur.")
if st.button("🧨 GALATASARAY-KOCAELİ 2/1 + 1/2 ÇEK",use_container_width=True):
 from datetime import date as _date
 with st.spinner("Bülten → arşiv maç ID → İY/MS tablosu..."):
  _x21,_x12,_xs,_xu,_xr=archive_htft_from_program(_date(2026,9,13),'Galatasaray','Kocaelispor')
 if _xr:
  st.write(f"Program kaydı bulundu • archive_id(index 50): {_xr[50] if len(_xr)>50 else 'YOK'}")
 if _xu:
  st.caption(_xu)
 if _x21 is not None:
  st.success(f"🔥 BULDUK • 2/1 = {_x21:.2f} • 1/2 = {_x12:.2f} • {_xs}")
 else:
  st.error(f"Bulunamadı • {_xs}")

st.markdown("### 🔬 V11 Bülten İç Yapı Testi")
st.caption("Bülten geliyor. Şimdi Galatasaray kaydının ham alanlarını okuyup 2/1 ve 1/2'nin kodlu alan olarak bulunup bulunmadığını kontrol ediyoruz.")
if st.button("🔬 GALATASARAY HAM KAYDINI AÇ",use_container_width=True):
 from datetime import date as _date
 with st.spinner("Ham bülten kaydı inceleniyor..."):
  _code,_url,_html=bulletin_fetch(_date(2026,9,13))
  _probe=raw_match_probe(_html,'Galatasaray')
 st.write(f"HTTP: {_code} • Bülten boyutu: {len(_html):,} byte • Galatasaray: {_probe.get('Bulundu')}")
 st.markdown("**Kayıtta görülen alan adları:**")
 st.code(_probe.get('Alan adları','') or 'Alan adı yakalanamadı')
 st.markdown("**Galatasaray çevresindeki ham veri:**")
 st.code(_probe.get('Ham parça','')[:5300],language=None)
 st.download_button("⬇️ HAM BÜLTENİ İNDİR",data=_html,file_name="mackolik_bulten_13-09-2026.txt",mime="text/plain",use_container_width=True)

st.markdown("### ⚡ V10 Tek İstek Bülten Testi")
st.caption("Amaç: 88 ayrı maç sayfası yerine Mackolik İddaa bültenini tek istekte çekmek.")
if st.button("⚡ 13.09.2026 BÜLTENİNİ TEST ET", use_container_width=True):
 from datetime import date as _date
 _d=_date(2026,9,13)
 with st.spinner("Mackolik bülteni tek istekte çekiliyor..."):
  _diag=bulletin_diag(_d)
  _code,_url,_html=bulletin_fetch(_d)
  _b21,_b12,_bst=extract_bulletin_pair(_html,'Galatasaray','Kocaelispor')
 st.dataframe([_diag],use_container_width=True,hide_index=True)
 if _b21 is not None:
  st.success(f"🔥 BÜLTEN ÇALIŞTI • Galatasaray-Kocaelispor • 2/1 = {_b21:.2f} • 1/2 = {_b12:.2f}")
 else:
  st.warning(f"Bülten geldi ama oran çifti henüz ayrışmadı • {_bst}")

st.markdown("### 🎯 V9 Oran Motoru Testi")
if st.button("🎯 GALATASARAY-KOCAELİ ORANINI ÇEK", use_container_width=True):
 with st.spinner("Mackolik sayfaları deneniyor..."):
  _a21,_a12,_st=odds_page('cgs5dbd8o9pkw8za412koiyac','Galatasaray','Kocaelispor')
 if _a21 is not None:
  st.success(f"2/1 = {_a21:.2f} • 1/2 = {_a12:.2f} • {_st}")
 else:
  st.error(f"Oran bulunamadı • {_st}")

chosen=st.date_input('Tarih',date.today(),format='DD.MM.YYYY')

st.markdown("### 🧪 Tek Maç Bağlantı Testi")
st.caption("88 maçı tekrar taramadan Galatasaray - Kocaelispor kontrol maçında Mackolik/Sahadan erişimini teşhis eder.")
if st.button("🧪 KONTROL MAÇINI TEST ET", use_container_width=True):
 with st.spinner("4 veri yolu tek tek deneniyor..."):
  rows=diagnostic_rows()
 st.dataframe(rows,use_container_width=True,hide_index=True)
 good=[x for x in rows if x.get('İY/MS var mı')=='EVET']
 if good:
  st.success("İY/MS marketi en az bir rotada göründü. Bu rotayı ana taramaya bağlayabiliriz.")
 else:
  st.error("Hiçbir rotada İY/MS marketi görünmedi. Bu, Streamlit sunucusuna sade/engelli HTML döndüğünü gösterir.")

if st.button('🔎 BUGÜNÜ TARA',type='primary',use_container_width=True):
 ds=chosen.isoformat(); r=get(DAILY,{'sports[]':'Soccer','matchDate':ds},5)
 if not r: st.error('Mackolik günlük listesine ulaşılamadı. Biraz sonra tekrar dene.'); st.stop()
 data=r.json().get('data',{}); matches=data.get('matches',{}) or {}; comps=data.get('competitions',{}) or {}
 selected=[]
 for mid,m in matches.items():
  comp=comps.get(m.get('competitionId'),{}) or {}; cc=comp.get('country') or {}; rc=cc.get('name') if isinstance(cc,dict) else cc; rl=comp.get('name') or ''
  canon=EXACT.get((str(rc or ''),str(rl or '')))
  if canon:
   h,a=home_away(m)
   if h and a:selected.append((str(mid),m,canon[0],canon[1],h,a))
 if not selected: st.warning('Bu tarihte 40 hedef lig içinde maç bulunamadı.'); st.stop()
 bar=st.progress(0,text=f'{len(selected)} maç bulundu, oranlar taranıyor...'); out=[]; all_today=[]
 con=sqlite3.connect(DB)
 for i,(mid,m,country,league,h,a) in enumerate(selected,1):
  page,source=odds_page(mid,h,a)
  if page:
   o21,o12,status=parse_pair(page)
   if o21 and o12: status=f'BULUNDU • {source}'
  else:
   o21,o12,status=None,None,source
  s=stats(con,o21,o12,country,league)
  all_today.append({'Saat':mtime(m),'Ülke':country,'Lig':league,'Maç':f'{h} - {a}',
                    '2/1':o21,'1/2':o12,'Oran Durumu':status,'ID':mid,
                    'Geçmiş':s['n'] if s else 0,'Flip':s['flips'] if s else 0,
                    'Flip %':round(s['fp'],2) if s else 0})
  if s and s['n']:
   out.append({'Saat':mtime(m),'Lig':league,'Maç':f'{h} - {a}','2/1':o21,'1/2':o12,'Geçmiş':s['n'],'Flip':s['flips'],'Flip %':round(s['fp'],2),'2/1 Biten':s['n21'],'1/2 Biten':s['n12'],'2/1 Payı %':round(s['p21'],1),'1/2 Payı %':round(s['p12'],1),'Aynı Lig':s['same'],'Aynı Lig Flip':s['sameflip'],'Etiket':tag(s['n'],s['fp']),'ID':mid,'rows':s['rows']})
  bar.progress(i/len(selected),text=f'{i}/{len(selected)} • {h} - {a}')
 con.close(); bar.empty()
 st.session_state['signals']=out; st.session_state['all_today']=all_today
 st.session_state['scanned']=len(selected); st.session_state['date']=ds

if 'signals' in st.session_state:
 out=st.session_state['signals']; all_today=st.session_state.get('all_today',[])
 odds_ok=sum(1 for x in all_today if x['2/1'] is not None and x['1/2'] is not None)
 odds_fail=len(all_today)-odds_ok
 st.success(f"{st.session_state['scanned']} maç tarandı • {odds_ok} maçta 2/1 + 1/2 oranı bulundu • {odds_fail} maçta oran alınamadı • {len(out)} exact geçmiş eşleşmeli sinyal")
 tab1,tab2=st.tabs(['🔥 BUGÜNÜN SİNYALLERİ','📋 BUGÜN TÜM MAÇLAR'])
 with tab2:
  st.subheader('Bugün Tüm Maçlar')
  st.caption('Burada taranan her maçın Mackolik’ten çekilen güncel 2/1 ve 1/2 oranını görebilirsin. Böylece 0 sinyalin gerçek mi, veri çekme sorunu mu olduğunu kontrol ederiz.')
  st.dataframe(all_today,use_container_width=True,hide_index=True)
 with tab1:
  if not out: st.info('Exact geçmiş oran çifti bulunan sinyal yok.')
  for x in sorted(out,key=lambda z:(-z['Flip %'],-z['Geçmiş'])):
   with st.expander(f"{x['Etiket']}  •  {x['Saat']}  •  {x['Maç']}"):
    st.markdown(f"**{x['Lig']}**  |  Güncel oran: **2/1 {x['2/1']:.2f} • 1/2 {x['1/2']:.2f}**")
    a,b,c,d=st.columns(4); a.metric('Geçmiş',x['Geçmiş']); b.metric('Flip',x['Flip']); c.metric('Flip %',f"%{x['Flip %']:.2f}"); d.metric('Aynı Lig',x['Aynı Lig'])
    st.write(f"2/1 biten: **{x['2/1 Biten']}** (%{x['2/1 Payı %']})  •  1/2 biten: **{x['1/2 Biten']}** (%{x['1/2 Payı %']})  •  Aynı lig flip: **{x['Aynı Lig Flip']}**")
    st.caption('KANIT • Aşağıda aynı exact 2/1 + 1/2 kapanış oranına sahip geçmiş maçlar var.')
    rows=[{'Tarih':r[0],'Lig':r[2],'Maç':f'{r[3]} - {r[4]}','İY':f'{r[5]}-{r[6]}','MS':f'{r[7]}-{r[8]}','İY/MS':r[9],'Flip':'✅' if r[10] else ''} for r in x['rows']]
    st.dataframe(rows,use_container_width=True,hide_index=True)
st.caption('⚠️ Bugünkü oranlar tarama anındaki GÜNCEL oranlardır. Tarihsel arşivdeki oranlar KAPANIŞ oranlarıdır. Exact eşleşme, bugünkü oranın kapanışa kadar değişmeyeceği anlamına gelmez.')
