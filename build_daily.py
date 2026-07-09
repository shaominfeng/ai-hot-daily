#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI HOT 每日晨报构建器（V2·体验重设计）
- 拉取当日日报（缺失则回退最近一期）
- 生成三页 HTML：单篇报告(亮/暗/系统主题+锚点导航) / 根着陆页(突出今日+归档搜索) / 当月归档(搜索)
- 推送到 GitHub shaominfeng/ai-hot-daily（按月份文件夹）
- 自动更新月度索引 + 根索引（README.md + index.html）
"""
import json, base64, subprocess, os, datetime, re, sys

GH_HOST = "github.com"
REPO = "shaominfeng/ai-hot-daily"
PAGES = "https://shaominfeng.github.io/ai-hot-daily"
AIHOT_DAILY = "{date}"
WEEK = ["周一","周二","周三","周四","周五","周六","周日"]
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

def wd(s): return WEEK[datetime.date.fromisoformat(s).weekday()]
def month_cn(m): return "%s年%s月" % (m[:4], int(m[5:]))

def fetch_daily(date_str):
    """拉取当日日报，404 则回退最近一期"""
    url = f"https://aihot.virxact.com/api/public/daily/{date_str}"
    r = subprocess.run(["curl","-sH","User-Agent: %s"%UA, url, "-w","HTTP %{http_code}"],
                       capture_output=True, text=True, timeout=30)
    out = r.stdout
    parts = out.rsplit("HTTP ", 1)
    code = parts[1].strip() if len(parts) > 1 else "0"
    body = parts[0].strip()
    if code == "200":
        try:
            return json.loads(body)
        except:
            pass
    # fallback
    r2 = subprocess.run(["curl","-sH","User-Agent: %s"%UA,
                         "https://aihot.virxact.com/api/public/daily"],
                        capture_output=True, text=True, timeout=30)
    return json.loads(r2.stdout.strip()) if r2.stdout.strip() else None

def gh_get(path):
    r = subprocess.run(["gh","api","/repos/%s/contents/%s"%(REPO,path)],
                       capture_output=True, text=True,
                       env={**os.environ,"GH_HOST":GH_HOST})
    if r.returncode == 0:
        try: return json.loads(r.stdout)
        except: pass
    return None

def gh_push(path, content, msg):
    b = base64.b64encode(content.encode("utf-8")).decode()
    existing = gh_get(path)
    sha = existing.get("sha") if existing else None
    cmd = ["gh","api","-X","PUT","/repos/%s/contents/%s"%(REPO,path),
           "-f","message=%s"%msg,"-f","content=%s"%b]
    if sha: cmd += ["-f","sha=%s"%sha]
    r = subprocess.run(cmd, capture_output=True, text=True,
                       env={**os.environ,"GH_HOST":GH_HOST})
    return r.returncode == 0

def gh_list_dir(path):
    r = gh_get(path)
    if isinstance(r, list): return r
    return []

# ============ CSS & JS (redesign) ============

CSS = """
:root{--bg-primary:#f6f7fb;--bg-secondary:#fff;--bg-tertiary:#eef0f5;--text-primary:#1f2430;--text-secondary:#6b7280;--border:#e2e5ee;--brand:#4f46e5;--brand-600:#4338ca;--c0:#6366f1;--c1:#0ea5e9;--c2:#10b981;--c3:#f59e0b;--c4:#ec4899;--shadow:0 1px 2px rgba(16,24,40,.06),0 8px 24px rgba(16,24,40,.06);--shadow-lg:0 12px 32px rgba(16,24,40,.1);--radius:16px;--radius-sm:12px}
[data-theme=dark]{--bg-primary:#0b0d12;--bg-secondary:#151820;--bg-tertiary:#1c1f2a;--text-primary:#f0f2f8;--text-secondary:#9aa3b2;--border:#252a38;--brand:#6366f1;--brand-600:#818cf8;--shadow:0 1px 2px rgba(0,0,0,.4),0 8px 24px rgba(0,0,0,.35);--shadow-lg:0 12px 32px rgba(0,0,0,.45)}
@media(prefers-color-scheme:dark){:root:not([data-theme=light]){--bg-primary:#0b0d12;--bg-secondary:#151820;--bg-tertiary:#1c1f2a;--text-primary:#f0f2f8;--text-secondary:#9aa3b2;--border:#252a38;--brand:#6366f1;--brand-600:#818cf8;--shadow:0 1px 2px rgba(0,0,0,.4),0 8px 24px rgba(0,0,0,.35);--shadow-lg:0 12px 32px rgba(0,0,0,.45)}}
*{box-sizing:border-box}html{scroll-behavior:smooth}
body{margin:0;font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei","Segoe UI",sans-serif;background:var(--bg-primary);color:var(--text-primary);line-height:1.6;transition:background .3s,color .3s}
.wrap{max-width:1120px;margin:0 auto;padding:0 24px}
.topnav{position:sticky;top:0;z-index:50;backdrop-filter:saturate(180%) blur(12px);background:color-mix(in srgb,var(--bg-primary) 86%,transparent);border-bottom:1px solid var(--border)}
.topnav .row{max-width:1120px;margin:0 auto;padding:12px 24px;display:flex;align-items:center;gap:16px}
.brand{font-weight:800;display:flex;align-items:center;gap:8px;white-space:nowrap;flex-shrink:0;font-size:15px;letter-spacing:-.01em}
.brand .dot{width:9px;height:9px;border-radius:50%;background:linear-gradient(135deg,var(--c0),var(--c4));flex-shrink:0}
.brand .txt{white-space:nowrap}
.navlinks{margin-left:auto;display:flex;align-items:center;gap:4px;flex-shrink:0}
.navlinks a{padding:8px 14px;border-radius:10px;text-decoration:none;color:var(--text-secondary);font-size:14px;font-weight:600;transition:.15s}
.navlinks a:hover{background:var(--bg-secondary);color:var(--text-primary)}
.theme-toggle{display:inline-flex;gap:2px;background:var(--bg-secondary);border:1px solid var(--border);border-radius:999px;padding:3px}
.theme-toggle button{padding:6px 10px;border:0;background:transparent;color:var(--text-secondary);border-radius:999px;cursor:pointer;font-size:13px;line-height:1;font-weight:600;transition:.15s}
.theme-toggle button.active{background:var(--brand);color:#fff}
.hero{padding:56px 0 36px}
.kicker{display:inline-flex;align-items:center;gap:6px;font-size:12px;font-weight:800;color:var(--brand);background:var(--bg-tertiary);border:1px solid var(--border);padding:6px 12px;border-radius:999px;text-transform:uppercase;letter-spacing:.02em}
[data-theme=dark] .kicker{background:rgba(99,102,241,.15);border-color:rgba(99,102,241,.25);color:#c7c9ff}
.hero h1{font-size:clamp(36px,6vw,56px);margin:18px 0 10px;line-height:1.1;font-weight:900;letter-spacing:-.03em;word-break:keep-all}
.hero .sub{color:var(--text-secondary);margin:0 0 24px;font-size:16px;line-height:1.55}
.total{display:flex;align-items:baseline;gap:12px;margin:8px 0 26px}
.total b{font-size:56px;font-weight:900;line-height:1;background:linear-gradient(135deg,var(--c0),var(--c1));-webkit-background-clip:text;background-clip:text;color:transparent}
.total span{color:var(--text-secondary);font-size:15px;font-weight:500}
.stats{display:grid;grid-template-columns:repeat(5,1fr);gap:12px}
.stat{background:var(--bg-secondary);border:1px solid var(--border);border-radius:var(--radius-sm);padding:16px;box-shadow:var(--shadow);transition:.15s}
.stat:hover{transform:translateY(-2px);box-shadow:var(--shadow-lg)}
.stat .n{font-size:28px;font-weight:800;line-height:1}
.stat .l{font-size:13px;color:var(--text-secondary);margin-top:6px;font-weight:600}
.stat.c0{border-top:3px solid var(--c0)}.stat.c0 .n{color:var(--c0)}
.stat.c1{border-top:3px solid var(--c1)}.stat.c1 .n{color:var(--c1)}
.stat.c2{border-top:3px solid var(--c2)}.stat.c2 .n{color:var(--c2)}
.stat.c3{border-top:3px solid var(--c3)}.stat.c3 .n{color:var(--c3)}
.stat.c4{border-top:3px solid var(--c4)}.stat.c4 .n{color:var(--c4)}
.anchornav{position:sticky;top:61px;z-index:40;background:var(--bg-primary);border-bottom:1px solid var(--border);padding:12px 0}
.anchornav .wrap{display:flex;gap:8px;flex-wrap:wrap}
.anchornav a{padding:7px 14px;border-radius:999px;background:var(--bg-secondary);border:1px solid var(--border);text-decoration:none;color:var(--text-secondary);font-size:13px;font-weight:600;transition:.15s}
.anchornav a:hover{border-color:var(--brand);color:var(--brand)}
.anchornav a.active{color:#fff;background:var(--brand);border-color:var(--brand)}
section.block{padding:36px 0 10px}
section.block h2{font-size:24px;margin:0 0 18px;display:flex;align-items:center;gap:10px;font-weight:800}
section.block h2 .pill{font-size:12px;font-weight:800;color:#fff;background:var(--brand);border-radius:999px;padding:3px 10px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:18px}
.card{position:relative;background:var(--bg-secondary);border:1px solid var(--border);border-radius:var(--radius);padding:20px;box-shadow:var(--shadow);transition:transform .15s,border-color .15s,box-shadow .15s;display:flex;flex-direction:column;gap:10px}
.card:hover{transform:translateY(-3px);border-color:#cfd3e6;box-shadow:var(--shadow-lg)}
[data-theme=dark] .card:hover{border-color:#3a4150}
.card:focus-within{border-color:var(--brand);box-shadow:0 0 0 3px color-mix(in srgb,var(--brand) 18%,transparent)}
.num{position:absolute;top:-12px;left:18px;width:28px;height:28px;border-radius:50%;background:var(--brand);color:#fff;font-size:13px;font-weight:800;display:flex;align-items:center;justify-content:center;box-shadow:var(--shadow)}
.card h3{font-size:16.5px;margin:6px 0 0;line-height:1.45;font-weight:700}
.chip{display:inline-block;font-size:12px;font-weight:700;color:var(--text-secondary);background:var(--bg-primary);border:1px solid var(--border);border-radius:999px;padding:4px 10px;align-self:flex-start}
.card p{margin:0;font-size:14px;color:var(--text-secondary);line-height:1.65}
.more{margin-top:auto;align-self:flex-start;font-size:13.5px;font-weight:700;color:var(--brand);text-decoration:none;display:inline-flex;align-items:center;gap:4px;padding-top:4px}
.more:hover{text-decoration:underline}
footer{border-top:1px solid var(--border);margin-top:48px;padding:30px 0 56px;color:var(--text-secondary);font-size:13px;text-align:center}
footer a{color:var(--brand);font-weight:600}
@media(max-width:920px){.stats{grid-template-columns:repeat(3,1fr)}.anchornav{top:58px}}
@media(max-width:680px){.wrap{padding:0 18px}.topnav .row{padding:12px 18px}.navlinks a{padding:7px 10px;font-size:13px}.stats{grid-template-columns:repeat(2,1fr)}.hero{padding:40px 0 28px}.hero h1{font-size:clamp(32px,9vw,46px)}}
@media(max-width:480px){.brand{font-size:14px}.navlinks{gap:2px}.navlinks a{padding:6px 8px}.theme-toggle button{padding:5px 8px}.total b{font-size:48px}.stats{gap:10px}.stat{padding:14px}.stat .n{font-size:24px}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}.card,.stat,.cta,.day{transition:none}}
:focus-visible{outline:2px solid var(--brand);outline-offset:2px}
"""
# archive extras
ARCHIVE_EXTRA = """
.hero-landing{display:grid;grid-template-columns:1.1fr .9fr;gap:48px;align-items:center;padding:52px 0 44px}
.hero-landing .left{min-width:0}
.hero-landing .right{display:flex;justify-content:center}
.snapshot{width:100%;max-width:360px;background:var(--bg-secondary);border:1px solid var(--border);border-radius:var(--radius);padding:24px;box-shadow:var(--shadow-lg)}
.snapshot h3{font-size:13px;font-weight:800;color:var(--text-secondary);margin:0 0 16px;text-transform:uppercase;letter-spacing:.05em}
.snapshot .mini-stats{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}
.snapshot .ms{padding:12px;border-radius:var(--radius-sm);background:var(--bg-primary);border:1px solid var(--border)}
.snapshot .ms .n{font-size:22px;font-weight:800;line-height:1}
.snapshot .ms .l{font-size:12px;color:var(--text-secondary);margin-top:4px;font-weight:600}
.cta{display:inline-flex;align-items:center;gap:8px;margin-top:6px;background:var(--brand);color:#fff;font-weight:700;text-decoration:none;padding:14px 24px;border-radius:var(--radius-sm);box-shadow:var(--shadow);transition:transform .15s,background .15s;font-size:15px}
.cta:hover{background:var(--brand-600);transform:translateY(-2px)}
.archive{padding:44px 0 20px;border-top:1px solid var(--border)}
.archive h2{font-size:22px;margin:0 0 18px;font-weight:800}
.search-wrap{position:relative;max-width:420px;margin-bottom:22px}
.search{width:100%;padding:13px 16px 13px 42px;border:1px solid var(--border);border-radius:var(--radius-sm);background:var(--bg-secondary);color:var(--text-primary);font-size:15px;transition:.15s}
.search:focus{outline:none;border-color:var(--brand);box-shadow:0 0 0 3px color-mix(in srgb,var(--brand) 15%,transparent)}
.search-icon{position:absolute;left:15px;top:50%;transform:translateY(-50%);color:var(--text-secondary);font-size:16px;pointer-events:none}
.grid.days{grid-template-columns:repeat(auto-fill,minmax(220px,1fr))}
.day{display:flex;flex-direction:column;gap:6px;background:var(--bg-secondary);border:1px solid var(--border);border-radius:var(--radius-sm);padding:18px;text-decoration:none;color:inherit;box-shadow:var(--shadow);transition:transform .15s,border-color .15s,box-shadow .15s}
.day:hover{transform:translateY(-3px);border-color:#cfd3e6;box-shadow:var(--shadow-lg)}
[data-theme=dark] .day:hover{border-color:#3a4150}
.day .d{font-size:18px;font-weight:800}.day .w{font-size:13px;color:var(--text-secondary);font-weight:500}.day .go{margin-top:8px;font-size:13px;font-weight:700;color:var(--brand)}
.empty{color:var(--text-secondary);padding:20px 0}
@media(max-width:860px){.hero-landing{grid-template-columns:1fr;gap:28px}.hero-landing .right{justify-content:flex-start}.snapshot{max-width:none}}
"""
ARC_CSS = CSS + ARCHIVE_EXTRA

THEME_JS = """\nclass ThemeManager{
  constructor(){this.current=this.stored()||this.system();this.apply(this.current);this.init();}
  system(){return matchMedia("(prefers-color-scheme:dark)").matches?"dark":"light";}
  stored(){return localStorage.getItem("theme");}
  apply(t){if(t==="system"){document.documentElement.removeAttribute("data-theme");localStorage.removeItem("theme");}else{document.documentElement.setAttribute("data-theme",t);localStorage.setItem("theme",t);}this.current=t;this.ui();}
  init(){var t=document.querySelector(".theme-toggle");if(t)t.addEventListener("click",function(e){var b=e.target.closest("button[data-theme]");if(b)this.apply(b.dataset.theme);}.bind(this));}
  ui(){document.querySelectorAll(".theme-toggle button").forEach(function(b){var on=b.dataset.theme===this.current;b.classList.toggle("active",on);b.setAttribute("aria-checked",on);}.bind(this));}
}"""

DAILY_JS = '\n(function(){\n  function esc(s){return String(s==null?"":s).replace(/[&<>"]/g,function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;","\\"":"&quot;"}[c];});}\n  function bj(d,o){return new Intl.DateTimeFormat("zh-CN",Object.assign({timeZone:"Asia/Shanghai"},o)).format(d);}\n  function pUTC(s){try{return s?new Date(s):null;}catch(e){return null;}}\n  var P=JSON.parse(document.getElementById("payload").textContent);\n  document.getElementById("title").textContent="AI 日报 · "+P.date;\n  var g=pUTC(P.generatedAt),ws=pUTC(P.windowStart),we=pUTC(P.windowEnd),sub=[];\n  if(g)sub.push("生成于 "+bj(g,{month:"long",day:"numeric",hour:"2-digit",minute:"2-digit",hour12:false})+"（北京时间）");\n  if(ws&&we)sub.push("数据窗口："+bj(ws,{month:"long",day:"numeric"})+" – "+bj(we,{month:"long",day:"numeric"}));\n  document.getElementById("subtitle").textContent=sub.join(" · ");\n  document.getElementById("totalnum").textContent=P.total;\n  var stats=document.getElementById("stats");\n  P.sections.forEach(function(s,i){var d=document.createElement("div");d.className="stat c"+i;d.innerHTML=\'<div class="n">\'+s.items.length+\'</div><div class="l">\'+esc(s.label)+\'</div>\';stats.appendChild(d);});\n  var toc=document.getElementById("toc");\n  P.sections.forEach(function(s,i){var a=document.createElement("a");a.href="#sec"+i;a.textContent=s.label;toc.appendChild(a);});\n  var main=document.getElementById("main"),n=0;\n  P.sections.forEach(function(s,i){\n    var sec=document.createElement("section");sec.className="block";sec.id="sec"+i;\n    var h=document.createElement("h2");h.innerHTML=esc(s.label)+\' <span class="pill">\'+s.items.length+\'</span>\';sec.appendChild(h);\n    var grid=document.createElement("div");grid.className="grid";\n    s.items.forEach(function(it){n++;var url=it.sourceUrl||it.permalink||"#";\n      var art=document.createElement("article");art.className="card";\n      art.innerHTML=\'<span class="num">\'+n+\'</span><h3>\'+esc(it.title)+\'</h3>\'+(it.sourceName?\'<span class="chip">\'+esc(it.sourceName)+\'</span>\':\'\')+\'<p>\'+esc(it.summary||"")+\'</p><a class="more" href="\'+esc(url)+\'" target="_blank" rel="noopener noreferrer">阅读原文 →</a>\';\n      grid.appendChild(art);});\n    sec.appendChild(grid);main.appendChild(sec);\n  });\n  document.getElementById("footertotal").textContent=P.total;\n  new ThemeManager();\n  var anchors=[].slice.call(toc.querySelectorAll("a"));\n  if("IntersectionObserver" in window){\n    var obs=new IntersectionObserver(function(es){es.forEach(function(e){if(e.isIntersecting)anchors.forEach(function(a){a.classList.toggle("active",a.getAttribute("href")==="#"+e.target.id);});});},{rootMargin:"-30% 0px -60% 0px"});\n    P.sections.forEach(function(s,i){var el=document.getElementById("sec"+i);if(el)obs.observe(el);});\n  }\n})();'

ARCHIVE_JS = '\n(function(){var data=JSON.parse(document.getElementById("daysdata").textContent);\nvar grid=document.getElementById("days");\nfunction render(l){grid.innerHTML="";l.forEach(function(d){var a=document.createElement("a");a.className="day";a.href=d.href;a.innerHTML=\'<span class="d">\'+d.label+\'</span><span class="w">\'+d.wd+\'</span><span class="go">查看报告 →</span>\';grid.appendChild(a);});if(!l.length)grid.innerHTML=\'<p class="empty">没有匹配的日期</p>\';}\nrender(data);\nvar inp=document.getElementById("search");inp.addEventListener("input",function(){var q=inp.value.trim().toLowerCase();if(!q){render(data);return;}render(data.filter(function(d){return(d.date+" "+d.wd+" "+d.label).toLowerCase().indexOf(q)>=0;}));});\nnew ThemeManager();})();'

TOGGLE = '<div class="theme-toggle" role="radiogroup" aria-label="主题"><button data-theme="light" role="radio" aria-checked="false">亮</button><button data-theme="dark" role="radio" aria-checked="false">暗</button><button data-theme="system" role="radio" aria-checked="true">自动</button></div>'

# ============ BUILD ============

def build_all(date=None):
    if date is None:
        date = datetime.date.today().strftime('%Y-%m-%d')

    data = fetch_daily(date)
    if not data:
        print("FATAL: could not fetch daily report")
        sys.exit(1)

    actual_date = data.get("date", date)
    total = sum(len(s["items"]) for s in data["sections"])
    sections = data["sections"]
    attr = data.get("attribution", {})
    canonical = attr.get("canonical", "https://aihot.virxact.com")
    gen = data.get("generatedAt")
    ws = data.get("windowStart")
    we = data.get("windowEnd")

    m = actual_date[:7]
    day_label = "%s月%s日" % (int(actual_date[5:7]), int(actual_date[8:10]))
    date_cn = "%s月%s日 %s" % (int(actual_date[5:7]), int(actual_date[8:10]), wd(actual_date))

    payload = json.dumps({"date":actual_date,"total":total,"sections":sections,
                          "attribution":attr,"generatedAt":gen,"windowStart":ws,"windowEnd":we},
                         ensure_ascii=False).replace("</","<\\/")

    # daily report
    daily = (
        '<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<title>AI 日报 · {actual_date}</title><style>{CSS}</style></head>'
        '<body>'
        '<header class="topnav"><div class="row">'
        '<div class="brand"><span class="dot"></span><span class="txt">AI HOT 晨报</span></div>'
        f'<nav class="navlinks"><a href="../index.html">今日</a><a href="../index.html#archive">归档</a>{TOGGLE}</nav>'
        '</div></header>'
        '<main class="wrap">'
        '<div class="hero"><span class="kicker">AI HOT · 每日晨报</span>'
        '<h1 id="title"></h1><p class="sub" id="subtitle"></p>'
        '<div class="total"><b id="totalnum">0</b><span>条今日精选</span></div>'
        '<div class="stats" id="stats"></div></div>'
        '<nav class="anchornav"><div class="wrap" id="toc"></div></nav><div id="main"></div></main>'
        f'<footer class="wrap">共 <span id="footertotal">0</span> 条 · 数据源 <a href="{canonical}" target="_blank" rel="noopener noreferrer">AI HOT</a> · 基准日期 {actual_date}（北京时间）</footer>'
        f'<script id="payload" type="application/json">{payload}</script>'
        f'<script>{THEME_JS}{DAILY_JS}</script>'
        '</body></html>'
    )

    # landing page (root index.html) — scan ALL months for complete day list
    landing_days = []
    # discover all months first
    root_entries = gh_list_dir("")
    all_months = sorted([e['name'] for e in root_entries if isinstance(e, dict) and re.match(r'^\d{4}-\d{2}$', e.get('name',''))], reverse=True)
    for month_dir in all_months:
        entries = gh_list_dir(month_dir)
        month_dates = sorted(set(
            e['name'][len('ai-hot-daily-'):-len('.html')]
            for e in entries if isinstance(e, dict) and e.get('name','').startswith('ai-hot-daily-') and e.get('name','').endswith('.html')
        ), reverse=True)
        for d in month_dates:
            landing_days.append({
                "date": d, "wd": wd(d),
                "href": f"{month_dir}/ai-hot-daily-{d}.html",
                "label": f"{int(d[5:7])}月{int(d[8:10])}日"
            })
    days_json = json.dumps(landing_days, ensure_ascii=False).replace("</","<\\/")
    snapshot_items = "".join(
        f'<div class="ms"><div class="n">{len(s["items"])}</div><div class="l">{s["label"].replace("/","/")}</div></div>'
        for s in sections[:5]
    )
    search_icon = '<svg class="search-icon" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>'
    landing = (
        '<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>AI HOT 每日晨报</title>'
        f'<style>{ARC_CSS}</style></head>'
        '<body>'
        '<header class="topnav"><div class="row">'
        '<div class="brand"><span class="dot"></span><span class="txt">AI HOT 晨报</span></div>'
        f'<nav class="navlinks"><a href="#top">今日</a><a href="#archive">归档</a>{TOGGLE}</nav>'
        '</div></header>'
        '<main class="wrap">'
        '<section class="hero-landing" id="top">'
        '<div class="left">'
        '<span class="kicker">AI HOT · 每日晨报</span>'
        '<h1>今日 AI 晨报</h1>'
        f'<p class="sub">{date_cn} · 共 {total} 条精选</p>'
        f'<a class="cta" href="{m}/ai-hot-daily-{actual_date}.html">阅读今日晨报 →</a>'
        '</div>'
        '<div class="right">'
        '<div class="snapshot">'
        '<h3>今日概览</h3>'
        f'<div class="mini-stats">{snapshot_items}</div>'
        '</div></div></section>'
        '<section class="archive" id="archive"><h2>历史归档</h2>'
        f'<div class="search-wrap">{search_icon}<input id="search" class="search" placeholder="搜索日期或星期，如 07-08 或 周三" aria-label="搜索归档"></div>'
        '<div class="grid days" id="days"></div></section></main>'
        f'<footer class="wrap">数据源 <a href="{canonical}" target="_blank" rel="noopener noreferrer">AI HOT</a> · 每日自动生成 · 北京时间</footer>'
        f'<script id="daysdata" type="application/json">{days_json}</script>'
        f'<script>{THEME_JS}{ARCHIVE_JS}</script>'
        '</body></html>'
    )

    # month archive — scan all daily files in this month
    entries = gh_list_dir(m)
    month_dates = sorted(set(
        e['name'][len('ai-hot-daily-'):-len('.html')]
        for e in entries if isinstance(e, dict) and e.get('name','').startswith('ai-hot-daily-') and e.get('name','').endswith('.html')
    ), reverse=True)
    month_days = [{"date":d,"wd":wd(d),"href":f"ai-hot-daily-{d}.html","label":f"{int(d[5:7])}月{int(d[8:10])}日"} for d in month_dates]
    mc_total_days = len(month_days)
    days_json_m = json.dumps(month_days, ensure_ascii=False).replace("</","<\\/")
    mc = month_cn(m)
    search_icon = '<svg class="search-icon" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>'
    month_html = (
        '<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<title>AI 晨报 · {mc}</title>'
        f'<style>{ARC_CSS}</style></head>'
        '<body>'
        '<header class="topnav"><div class="row">'
        '<div class="brand"><span class="dot"></span><span class="txt">AI HOT 晨报</span></div>'
        f'<nav class="navlinks"><a href="../index.html">今日</a><a href="../index.html#archive">归档</a>{TOGGLE}</nav>'
        '</div></header>'
        '<main class="wrap">'
        '<section class="hero" id="top"><span class="kicker">AI HOT · 每日晨报</span>'
        f'<h1>AI 晨报 · {mc}</h1>'
        f'<p class="sub">{mc} · 共 {mc_total_days} 篇日报</p>'
        '<a class="cta" href="../index.html">回到今日晨报 →</a></section>'
        '<section class="archive" id="archive"><h2>历史归档</h2>'
        f'<div class="search-wrap">{search_icon}<input id="search" class="search" placeholder="搜索日期或星期，如 07-08 或 周三" aria-label="搜索归档"></div>'
        '<div class="grid days" id="days"></div></section></main>'
        f'<footer class="wrap">数据源 <a href="{canonical}" target="_blank" rel="noopener noreferrer">AI HOT</a> · 每日自动生成 · 北京时间</footer>'
        f'<script id="daysdata" type="application/json">{days_json_m}</script>'
        f'<script>{THEME_JS}{ARCHIVE_JS}</script>'
        '</body></html>'
    )

    # push
    ok = gh_push(f"{m}/ai-hot-daily-{actual_date}.html", daily, f"daily report {actual_date}")
    ok &= gh_push("index.html", landing, "update root landing (V2 redesign)")
    ok &= gh_push(f"{m}/index.html", month_html, f"update month index {m} (V2)")

    # update monthly README — reuse month_dates from above
    all_days = sorted(month_dates) if month_dates else []
    md_days = '\n'.join(f"- [{x} {wd(x)}]({PAGES}/{m}/ai-hot-daily-{x}.html)" for x in all_days)
    month_readme = (f"# AI HOT 晨报 · {m}\n\n本月共 {len(all_days)} 篇。\n\n"
                    f"🌐 在线阅读（GitHub Pages）：{PAGES}/{m}/\n\n"
                    f"## 每日索引\n{md_days}\n\n"
                    "> 本地阅读：直接打开同目录 `ai-hot-daily-YYYY-MM-DD.html` 即可。\n")
    ok &= gh_push(f"{m}/README.md", month_readme, f"update monthly README {m}")

    # update root README
    root_entries = gh_list_dir("")
    months = sorted(e['name'] for e in root_entries if isinstance(e, dict) and re.match(r'^\d{4}-\d{2}$', e.get('name','')))
    root_readme = (
        f"# AI HOT 每日晨报归档\n\n每日自动抓取的 [AI HOT]({canonical}) 日报，渲染为单文件 HTML 仪表盘，按月份分文件夹归档。\n\n"
        f"🌐 **在线阅读（GitHub Pages）**：{PAGES}/\n\n"
        "## 月度索引\n" +
        '\n'.join(f"- [{x}]({x}/) — {int(x[5:])} 月（[在线版]({PAGES}/{x}/)）" for x in months) +
        "\n\n## 目录结构\n```\nai-hot-daily/\n├── README.md\n├── index.html\n├── 2026-07/\n│   ├── README.md\n│   ├── index.html\n│   └── ai-hot-daily-YYYY-MM-DD.html\n└── ...\n```\n\n"
        "## 怎么读\n- **本地**：双击任意 `ai-hot-daily-YYYY-MM-DD.html`。\n- **在线**：用上方 GitHub Pages 链接，HTML 完整渲染。\n"
    )
    ok &= gh_push("README.md", root_readme, "update root README")

    print(f"BUILD DONE: {actual_date} total={total} push_ok={ok}")
    print(f"  live: {PAGES}/")
    print(f"  daily: {PAGES}/{m}/ai-hot-daily-{actual_date}.html")
    return ok

if __name__ == "__main__":
    dt = sys.argv[1] if len(sys.argv) > 1 else datetime.date.today().strftime('%Y-%m-%d')
    build_all(dt)
