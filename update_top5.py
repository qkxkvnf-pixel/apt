#!/usr/bin/env python3
"""LG베스트샵 지점별 반경 5km 아파트 매매/전세 TOP5 자동 생성.

- 국토부 아파트 실거래가(매매, 전월세) 최근 3개월 거래 건수 기준
- 카카오 주소검색으로 좌표 변환 (결과는 geocache.json에 저장해 다음 실행부터 재사용)
- 결과: top5/index.html, top5/data.json
필요한 환경변수(GitHub Secrets): DATA_GO_KR_KEY, KAKAO_REST_KEY
"""
import json, math, os, sys, time, datetime, urllib.request, urllib.parse, urllib.error
import xml.etree.ElementTree as ET

RADIUS_KM = 5.0
MONTHS = 3
MAX_NEW_GEOCODE = 4000
ROOT = os.path.dirname(os.path.abspath(__file__))
CACHE_PATH = os.path.join(ROOT, "geocache.json")
OUT_DIR = os.path.join(ROOT, "top5")

BRANCHES = [
    ("고양·파주", "일산본점", "경기 고양시 일산동구 중앙로 1312"),
    ("고양·파주", "운정본점", "경기 파주시 미래로 319"),
    ("고양·파주", "덕양본점", "경기 고양시 덕양구 화중로 48"),
    ("고양·파주", "삼송본점", "경기 고양시 덕양구 고양대로 1982"),
    ("고양·파주", "대화점", "경기 고양시 일산서구 중앙로 1547"),
    ("고양·파주", "백석점", "경기 고양시 일산동구 중앙로 1074"),
    ("고양·파주", "스타필드 운정점", "경기 파주시 와석순환로515번길 70"),
    ("고양·파주", "이케아 고양점", "경기 고양시 덕양구 권율대로 420"),
    ("인천·부천·김포", "부평구청점", "인천 부평구 길주로 520"),
    ("인천·부천·김포", "중동본점", "경기 부천시 원미구 길주로 285"),
    ("인천·부천·김포", "계양본점", "인천 계양구 계양대로 52"),
    ("인천·부천·김포", "검단본점", "인천 서구 원당대로 847"),
    ("인천·부천·김포", "풍무점", "경기 김포시 김포대로 733"),
    ("인천·부천·김포", "김포구래점", "경기 김포시 김포한강4로 507"),
    ("인천·부천·김포", "오정점", "경기 부천시 소사로 693"),
    ("인천·부천·김포", "강화점", "인천 강화군 강화읍 강화대로 284"),
    ("인천·부천·김포", "인천본점", "인천 미추홀구 인주대로 482"),
    ("인천·부천·김포", "송도본점", "인천 연수구 하모니로178번길 22"),
    ("인천·부천·김포", "남동구청점", "인천 남동구 소래로 668"),
    ("인천·부천·김포", "청라점", "인천 서구 국제대로 237"),
    ("인천·부천·김포", "미추홀점", "인천 미추홀구 독배로 255"),
    ("인천·부천·김포", "간석점", "인천 부평구 경원대로 1009"),
    ("인천·부천·김포", "연수점", "인천 연수구 먼우금로 208"),
    ("인천·부천·김포", "가좌석남점", "인천 서구 가정로 185"),
    ("안양·군포·시흥", "평촌본점", "경기 안양시 동안구 흥안대로 427"),
    ("안양·군포·시흥", "의왕점", "경기 의왕시 경수대로391번길 1"),
    ("안양·군포·시흥", "은계점", "경기 시흥시 은행고길 2"),
    ("안양·군포·시흥", "비산점", "경기 안양시 동안구 관악대로 236"),
    ("안양·군포·시흥", "산본점", "경기 군포시 산본천로 56"),
    ("안양·군포·시흥", "시화점", "경기 시흥시 정왕대로 230"),
    ("안양·군포·시흥", "안양점", "경기 안양시 만안구 안양로 242"),
    ("안양·군포·시흥", "시흥아울렛점", "경기 시흥시 서해안로 699"),
]

# 조회할 시군구 (법정동 앞 5자리 -> 주소검색용 이름). 지점 5km 안에 걸치는 인접 지역 포함.
REGIONS = {
    "41281": "경기 고양시 덕양구", "41285": "경기 고양시 일산동구", "41287": "경기 고양시 일산서구",
    "41480": "경기 파주시", "41570": "경기 김포시",
    "41190": "경기 부천시", "41192": "경기 부천시 원미구", "41194": "경기 부천시 소사구", "41196": "경기 부천시 오정구",
    "41390": "경기 시흥시", "41171": "경기 안양시 만안구", "41173": "경기 안양시 동안구",
    "41410": "경기 군포시", "41430": "경기 의왕시", "41210": "경기 광명시", "41290": "경기 과천시",
    "41271": "경기 안산시 상록구", "41273": "경기 안산시 단원구",
    "41111": "경기 수원시 장안구", "41113": "경기 수원시 권선구", "41115": "경기 수원시 팔달구", "41117": "경기 수원시 영통구",
    "11500": "서울 강서구", "11470": "서울 양천구", "11530": "서울 구로구", "11380": "서울 은평구",
    "11440": "서울 마포구", "11545": "서울 금천구", "11620": "서울 관악구", "11560": "서울 영등포구", "11410": "서울 서대문구",
    "28110": "인천 중구", "28140": "인천 동구", "28177": "인천 미추홀구", "28185": "인천 연수구",
    "28200": "인천 남동구", "28237": "인천 부평구", "28245": "인천 계양구", "28260": "인천 서구", "28710": "인천 강화군",
}

TRADE_URL = "https://apis.data.go.kr/1613000/RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev"
RENT_URL = "https://apis.data.go.kr/1613000/RTMSDataSvcAptRent/getRTMSDataSvcAptRent"


def http_get(url, params=None, headers=None, tries=3):
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=headers or {})
            with urllib.request.urlopen(req, timeout=40) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                raise PermissionError("HTTP %d (권한 없음)" % e.code)
            last = e
            time.sleep(1.5 * (i + 1))
        except Exception as e:  # noqa
            last = e
            time.sleep(1.5 * (i + 1))
    raise RuntimeError("요청 실패: %s (%s)" % (url.split("?")[0], last))


def haversine_km(lat1, lon1, lat2, lon2):
    p = math.pi / 180
    a = (math.sin((lat2 - lat1) * p / 2) ** 2
         + math.cos(lat1 * p) * math.cos(lat2 * p) * math.sin((lon2 - lon1) * p / 2) ** 2)
    return 12742 * math.asin(math.sqrt(a))


def recent_months(n):
    kst = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
    y, m = kst.year, kst.month
    out = []
    for _ in range(n):
        out.append("%04d%02d" % (y, m))
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    return out


def parse_items(xml_bytes):
    """공공데이터 XML 응답을 (items, totalCount)로 변환. 오류면 예외."""
    root = ET.fromstring(xml_bytes)
    code = (root.findtext(".//resultCode") or "").strip()
    if code and code not in ("00", "000"):
        raise RuntimeError("API 오류 %s: %s" % (code, root.findtext(".//resultMsg")))
    total = int(root.findtext(".//totalCount") or 0)
    items = []
    for it in root.findall(".//item"):
        items.append({c.tag: (c.text or "").strip() for c in it})
    return items, total


def fetch_all(url, key, lawd, ymd):
    rows, page = [], 1
    while True:
        raw = http_get(url, {"serviceKey": key, "LAWD_CD": lawd, "DEAL_YMD": ymd,
                             "numOfRows": 1000, "pageNo": page})
        items, total = parse_items(raw)
        rows += items
        if page * 1000 >= total or not items:
            return rows
        page += 1


def preflight(key):
    ym = recent_months(2)[-1]
    names = (("sale", TRADE_URL, "국토교통부_아파트 매매 실거래가 상세 자료"),
             ("jeonse", RENT_URL, "국토교통부_아파트 전월세 실거래가 자료"))
    bad = []
    for kind, url, label in names:
        try:
            http_get(url, {"serviceKey": key, "LAWD_CD": "41285", "DEAL_YMD": ym,
                           "numOfRows": 1, "pageNo": 1})
        except PermissionError:
            bad.append(label)
    if bad:
        sys.exit("공공데이터포털에서 아래 API가 아직 승인되지 않았거나 키가 맞지 않습니다: "
                 + " / ".join(bad) + "\n활용신청 승인 후(최대 1~2시간) 다시 실행하세요.")


def collect(key):
    """단지별 매매/전세 거래 건수 집계."""
    cx = {}  # (sgg, umd, apt) -> dict
    months = recent_months(MONTHS)
    for lawd in REGIONS:
        for ymd in months:
            for kind, url in (("sale", TRADE_URL), ("jeonse", RENT_URL)):
                try:
                    rows = fetch_all(url, key, lawd, ymd)
                except Exception as e:
                    print("건너뜀", lawd, ymd, kind, e, file=sys.stderr)
                    continue
                for r in rows:
                    apt = r.get("aptNm", "")
                    if not apt:
                        continue
                    if kind == "sale" and r.get("cdealType", "").upper() == "O":
                        continue  # 해제된 거래
                    if kind == "jeonse" and r.get("monthlyRent", "0") not in ("0", "", "0.0"):
                        continue  # 월세 제외, 전세만
                    sgg = r.get("sggCd") or lawd
                    umd = r.get("umdNm", "")
                    k = (sgg, umd, apt)
                    d = cx.setdefault(k, {"sgg": sgg, "umd": umd, "name": apt,
                                          "jibun": r.get("jibun", ""), "sale": 0, "jeonse": 0})
                    d[kind] += 1
                    if not d["jibun"]:
                        d["jibun"] = r.get("jibun", "")
        print("완료", lawd, REGIONS[lawd], "누적 단지", len(cx))
    return list(cx.values())


def kakao_get(path, kakao_key, query):
    raw = http_get("https://dapi.kakao.com/v2/local/search/" + path,
                   {"query": query}, {"Authorization": "KakaoAK " + kakao_key})
    return json.loads(raw).get("documents", [])


def geocode_address(kakao_key, addr):
    docs = kakao_get("address.json", kakao_key, addr)
    if docs:
        return float(docs[0]["y"]), float(docs[0]["x"])
    docs = kakao_get("keyword.json", kakao_key, addr)
    if docs:
        return float(docs[0]["y"]), float(docs[0]["x"])
    return None


def geocode_complex(kakao_key, c):
    region = REGIONS.get(c["sgg"], "")
    jibun = c["jibun"].replace("산", "산 ") if c["jibun"].startswith("산") else c["jibun"]
    res = None
    if jibun:
        docs = kakao_get("address.json", kakao_key, "%s %s %s" % (region, c["umd"], jibun))
        if docs:
            res = (float(docs[0]["y"]), float(docs[0]["x"]))
    if not res:
        docs = kakao_get("keyword.json", kakao_key, "%s %s %s" % (region, c["umd"], c["name"]))
        if docs:
            res = (float(docs[0]["y"]), float(docs[0]["x"]))
    return res


def load_cache():
    try:
        with open(CACHE_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_cache(cache):
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=0, sort_keys=True)


def attach_coords(complexes, kakao_key, cache):
    new_calls = 0
    for c in complexes:
        ck = "%s|%s|%s|%s" % (c["sgg"], c["umd"], c["jibun"], c["name"])
        if ck in cache:
            v = cache[ck]
        elif new_calls >= MAX_NEW_GEOCODE:
            v = None  # 다음 실행에서 이어서 처리
        else:
            new_calls += 1
            try:
                v = geocode_complex(kakao_key, c)
            except Exception as e:
                print("좌표 실패", c["name"], e, file=sys.stderr)
                continue
            cache[ck] = list(v) if v else []
            v = cache[ck]
        c["pos"] = tuple(v) if v else None
    print("새로 변환한 단지:", new_calls)


def rank(branch_pos, complexes, key):
    near = []
    for c in complexes:
        if not c.get("pos") or c[key] <= 0:
            continue
        d = haversine_km(branch_pos[0], branch_pos[1], c["pos"][0], c["pos"][1])
        if d <= RADIUS_KM:
            near.append((c[key], -d, c))
    near.sort(key=lambda t: (t[0], t[1]), reverse=True)
    return [{"name": c["name"], "dong": c["umd"], "count": n,
             "km": round(-nd, 1)} for n, nd, c in near[:5]]


def build_data(branch_pos_map, complexes):
    kst = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
    months = recent_months(MONTHS)
    out = {"updated": kst.strftime("%Y-%m-%d %H:%M"),
           "period": "%s ~ %s" % (months[-1], months[0]), "branches": []}
    for grp, name, addr in BRANCHES:
        pos = branch_pos_map.get(name)
        b = {"group": grp, "name": name, "addr": addr, "sale": [], "jeonse": [], "ok": bool(pos)}
        if pos:
            b["sale"] = rank(pos, complexes, "sale")
            b["jeonse"] = rank(pos, complexes, "jeonse")
        out["branches"].append(b)
    return out


PAGE = """<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>지점별 아파트 거래 TOP5</title>
<style>
:root{--bg:#f6f5f3;--sf:#fff;--fg:#1f2124;--mu:#6a6e75;--ln:#dfddd8;--ac:#a50034;--af:#fff;--sa:#a50034;--je:#1d5f8a;--so:#f0eeea}
@media(prefers-color-scheme:dark){:root{--bg:#16171a;--sf:#1f2125;--fg:#ececea;--mu:#9a9ea5;--ln:#33363c;--ac:#ff5c85;--af:#16171a;--sa:#ff7a9c;--je:#6ab4e6;--so:#272a2f;color-scheme:dark}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.55 system-ui,-apple-system,"Apple SD Gothic Neo","Malgun Gothic",sans-serif;padding:20px max(16px,env(safe-area-inset-right,0px)) 40px max(16px,env(safe-area-inset-left,0px))}
.w{max-width:1000px;margin:0 auto;display:flex;flex-direction:column;gap:14px}
h1{font-size:20px;margin:0}h2{font-size:15px;margin:0 0 8px}
.mu{color:var(--mu)}select{font:inherit;padding:8px 10px;border:1px solid var(--ln);border-radius:6px;background:var(--sf);color:var(--fg);max-width:100%}
.cols{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}@media(max-width:620px){.cols{grid-template-columns:minmax(0,1fr)}}
.card{background:var(--sf);border:1px solid var(--ln);border-radius:8px;padding:14px 16px;min-width:0}
.sa h2{color:var(--sa)}.je h2{color:var(--je)}
.r{display:grid;grid-template-columns:22px minmax(0,1fr) auto;gap:8px;padding:7px 0;border-top:1px solid var(--ln);align-items:center}.r:first-of-type{border-top:0}
.r b{font-variant-numeric:tabular-nums}.n{font-weight:700;color:var(--mu)}.r:first-of-type .n{color:var(--ac)}
.s{font-size:12px;color:var(--mu)}.t{overflow-x:auto}table{border-collapse:collapse;width:100%;min-width:480px}
th,td{text-align:left;padding:6px 8px;border-top:1px solid var(--ln)}th{font-size:12px;color:var(--mu);font-weight:500;border-top:0}

.tabs{display:flex;gap:6px;margin-bottom:10px}
.tabs button{font:inherit;border:1px solid var(--ln);background:transparent;color:var(--fg);padding:7px 18px;border-radius:6px;cursor:pointer}
.tabs button[aria-selected=true]{background:var(--ac);border-color:var(--ac);color:var(--af);font-weight:700}
.tabs button:focus-visible,select:focus-visible{outline:2px solid var(--ac);outline-offset:2px}
#sumt{min-width:820px}#sumt td{vertical-align:top;background:var(--sf)}
#sumt th:first-child,#sumt tr.br td:first-child{position:sticky;left:0;background:var(--sf);white-space:nowrap;z-index:1}
.nb{display:flex;gap:4px;margin-top:5px}
.nb button{font:inherit;font-size:12px;padding:2px 10px;border:1px solid var(--ln);background:transparent;color:var(--fg);border-radius:6px;cursor:pointer}
.nb button:focus-visible{outline:2px solid var(--ac);outline-offset:2px}
.nb button.sale[aria-pressed=true]{background:var(--sa);border-color:var(--sa);color:var(--af);font-weight:700}
.nb button.jeonse[aria-pressed=true]{background:var(--je);border-color:var(--je);color:var(--af);font-weight:700}
.ch{position:sticky;left:0;width:min(720px,calc(100vw - 92px));padding:6px 0 8px}
.ch .ct{font-weight:700;margin-bottom:6px}
.bl{display:grid;grid-template-columns:minmax(90px,30%) minmax(0,1fr) 44px;gap:10px;align-items:center;padding:4px 0}
.bl small{display:block;font-size:12px;color:var(--mu)}
.bt{background:var(--so);border-radius:4px;height:20px}
.bf{height:100%;border-radius:4px}.bf.sale{background:var(--sa)}.bf.jeonse{background:var(--je)}
.bv{text-align:right;font-weight:700;font-variant-numeric:tabular-nums}
#sumt .c{font-weight:700}#sumt .d{font-size:12px;color:var(--mu)}
</style></head><body><div class="w">
<div><h1>지점별 아파트 거래 TOP5</h1>
<p class="mu" style="margin:2px 0 0">지점 반경 5km 안 아파트 단지, 최근 3개월 실거래 건수 기준 (매물 수가 아닙니다)</p></div>
<div class="card"><h2>전체 요약</h2>
<div class="tabs" role="tablist"><button type="button" role="tab" id="tb-sale" aria-selected="true">매매</button><button type="button" role="tab" id="tb-jeonse" aria-selected="false">전세</button></div>
<div class="t"><table id="sumt"><thead><tr><th>지점</th><th>1위</th><th>2위</th><th>3위</th><th>4위</th><th>5위</th></tr></thead><tbody id="sum"></tbody></table></div>
<p class="mu s" style="margin:8px 0 0">지점 이름 아래의 매매/전세 버튼을 누르면 그 지점의 TOP5 막대그래프가 열립니다. 같은 버튼을 다시 누르면 닫힙니다.</p></div>
<div><select id="sel" aria-label="지점 선택"></select> <span class="mu s" id="upd"></span></div>
<div id="out"></div>
</div>
<script>
var D=__DATA__;
function e(t,c,x){var n=document.createElement(t);if(c)n.className=c;if(x!=null)n.textContent=x;return n}
function card(cls,label,rows){var c=e('section','card '+cls);c.appendChild(e('h2',null,label+' TOP5'));
 if(!rows.length){c.appendChild(e('div','mu','반경 5km 안에서 집계된 거래가 없습니다.'));return c}
 rows.forEach(function(r,i){var d=e('div','r');d.appendChild(e('span','n',i+1));
  var m=e('span');m.appendChild(document.createTextNode(r.name));m.appendChild(e('div','s',r.dong+' · 약 '+r.km+'km'));d.appendChild(m);
  d.appendChild(e('b',null,r.count+'건'));c.appendChild(d)});return c}
function show(i){var b=D.branches[i],o=document.getElementById('out');o.textContent='';
 var h=e('div','card');h.appendChild(e('h2',null,'LG베스트샵 '+b.name));h.appendChild(e('div','mu',b.addr));o.appendChild(h);
 if(!b.ok){o.appendChild(e('div','mu','이 지점 주소의 좌표를 찾지 못했습니다.'));return}
 var g=e('div','cols');g.style.marginTop='14px';g.appendChild(card('sa','매매',b.sale));g.appendChild(card('je','전세',b.jeonse));o.appendChild(g)}
var s=document.getElementById('sel');
D.branches.forEach(function(b,i){var o=e('option',null,b.group+' · '+b.name);o.value=i;s.appendChild(o)});
s.onchange=function(){show(+s.value)};
document.getElementById('upd').textContent='업데이트 '+D.updated+' · 기간 '+D.period;
var sm=document.getElementById('sum'),kind='sale',opened=null;
var KL={sale:'매매',jeonse:'전세'};
function chart(b,k){var c=e('div','ch');c.appendChild(e('div','ct',b.name+' '+KL[k]+' TOP5 (거래 건수)'));
 var rows=b[k];if(!rows.length){c.appendChild(e('div','mu','반경 5km 안에서 집계된 거래가 없습니다.'));return c}
 var mx=rows[0].count||1;
 rows.forEach(function(r,j){var l=e('div','bl');var n=e('span');n.appendChild(document.createTextNode((j+1)+'. '+r.name));n.appendChild(e('small',null,r.dong+' · 약 '+r.km+'km'));l.appendChild(n);
  var t=e('div','bt');var f=e('div','bf '+k);f.style.width=Math.max(2,r.count/mx*100)+'%';t.appendChild(f);l.appendChild(t);
  l.appendChild(e('span','bv',r.count+'건'));c.appendChild(l)});return c}
function sumShow(){sm.textContent='';
 document.getElementById('tb-sale').setAttribute('aria-selected',kind==='sale');
 document.getElementById('tb-jeonse').setAttribute('aria-selected',kind==='jeonse');
 D.branches.forEach(function(b,i){var tr=e('tr','br');var f=e('td');f.appendChild(e('div',null,b.name));
  var nb=e('div','nb');['sale','jeonse'].forEach(function(k){var bt=e('button',k,KL[k]);bt.type='button';
   bt.setAttribute('aria-pressed',!!(opened&&opened.i===i&&opened.k===k));
   bt.onclick=function(){opened=(opened&&opened.i===i&&opened.k===k)?null:{i:i,k:k};sumShow()};nb.appendChild(bt)});
  f.appendChild(nb);tr.appendChild(f);
  var rows=b[kind];
  for(var k=0;k<5;k++){var td=e('td');var r=rows[k];
   if(r){td.appendChild(e('div','c',r.name));td.appendChild(e('div','d',r.count+'건 · '+r.dong))}else{td.className='mu';td.textContent='-'}
   tr.appendChild(td)}
  sm.appendChild(tr);
  if(opened&&opened.i===i){var xr=e('tr','xr');var xd=e('td');xd.colSpan=6;xd.appendChild(chart(b,opened.k));xr.appendChild(xd);sm.appendChild(xr)}})}
document.getElementById('tb-sale').onclick=function(){kind='sale';sumShow()};
document.getElementById('tb-jeonse').onclick=function(){kind='jeonse';sumShow()};
sumShow();show(0);
</script></body></html>
"""


def write_outputs(data):
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "data.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    blob = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    with open(os.path.join(OUT_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(PAGE.replace("__DATA__", blob))


def main():
    key = os.environ.get("DATA_GO_KR_KEY", "")
    kakao = os.environ.get("KAKAO_REST_KEY", "")
    if not key or not kakao:
        sys.exit("DATA_GO_KR_KEY, KAKAO_REST_KEY 비밀값이 설정되지 않았습니다.")
    key = urllib.parse.unquote(key)  # 인코딩된 키를 붙여넣었어도 동작하게 함

    preflight(key)
    cache = load_cache()
    branch_pos = {}
    for _, name, addr in BRANCHES:
        ck = "branch|" + addr
        if ck not in cache or not cache[ck]:
            res = geocode_address(kakao, addr)
            cache[ck] = list(res) if res else []
        branch_pos[name] = tuple(cache[ck]) if cache[ck] else None
        if not branch_pos[name]:
            print("지점 좌표 실패:", name, addr, file=sys.stderr)
    save_cache(cache)

    complexes = collect(key)
    if not complexes:
        sys.exit("실거래 데이터를 하나도 받지 못했습니다. 공공데이터포털 활용신청 승인 상태와 키를 확인하세요.")
    attach_coords(complexes, kakao, cache)
    save_cache(cache)

    write_outputs(build_data(branch_pos, complexes))
    print("완료")


if __name__ == "__main__":
    main()
