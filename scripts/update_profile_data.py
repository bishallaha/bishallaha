#!/usr/bin/env python3
# Refresh GitHub profile stat and language SVG cards from the public REST API.
import json, os, urllib.request, urllib.error
from datetime import datetime, timedelta, timezone
from pathlib import Path
from html import escape

OWNER = "bishallaha"
ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
BG = "#0A1017"; BORDER = "#1B2A39"; TEXT = "#F3EFE7"; MUTED = "#95A4B5"; MUTED2 = "#67788B"
ORANGE = "#F38B4B"; GREEN = "#32C7A1"
TOKEN = os.getenv("GITHUB_TOKEN", "")
HEADERS = {"Accept":"application/vnd.github+json", "X-GitHub-Api-Version":"2022-11-28", "User-Agent":"bishallaha-profile-readme"}
if TOKEN: HEADERS["Authorization"] = f"Bearer {TOKEN}"

def get_json(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=25) as res:
        return json.load(res)

def esc(s): return escape(str(s))
def text(x,y,s,size=14,fill=TEXT,weight=400,anchor=None):
    a = f' text-anchor="{anchor}"' if anchor else ''
    return f'<text x="{x}" y="{y}" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" font-size="{size}" fill="{fill}" font-weight="{weight}"{a}>{esc(s)}</text>'
def line(x1,y1,x2,y2,color=BORDER,width=1):
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{width}"/>'
def roundrect(x,y,w,h,fill,stroke=BORDER,rx=3):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="0.6"/>'
def frame(w,h,body,title):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}"><title>{esc(title)}</title><rect x="1.5" y="1.5" width="{w-3}" height="{h-3}" rx="23" fill="{BG}" stroke="{BORDER}" stroke-width="2"/>{body}</svg>'''

def stats_svg(user, repos, events):
    starred = get_json(f"https://api.github.com/users/{OWNER}/starred?per_page=100")
    values = [(str(user.get("public_repos", len(repos))), "PUBLIC REPOS"), (str(len(starred)), "STARRED"), (str(user.get("followers",0)), "FOLLOWERS"), (str(user.get("following",0)), "FOLLOWING")]
    b = [f'<circle cx="40" cy="42" r="21" fill="#151E28"/>', text(40,49,"G",20,TEXT,700,"middle"), text(92,49,"GitHub Stats",21,TEXT,600), text(480,49,"VIEW PROFILE  >",12,ORANGE,600,"end")]
    for i,(num,label) in enumerate(values):
        x=31+i*118
        b.append(text(x,104,num,28,TEXT,600))
        b.append(text(x,130,label,9,MUTED,600))
        if i<3: b.append(line(x+98,84,x+98,139,BORDER,1))
    b.append(line(28,154,482,154,BORDER,1))
    b.append(text(30,178,"PUBLIC ACTIVITY · LAST 90 DAYS",11,MUTED2,600))
    today = datetime.now(timezone.utc).date()
    start = today - timedelta(days=90)
    counts = {}
    for ev in events:
        try:
            day = datetime.fromisoformat(ev["created_at"].replace("Z","+00:00")).date()
            if start <= day <= today: counts[day] = counts.get(day,0)+1
        except Exception: pass
    peak = max(counts.values()) if counts else 0
    palette = ["#10241F","#15372D","#1B5239","#26744A","#39A45E"]
    for i in range(91):
        day = start + timedelta(days=i); count = counts.get(day,0)
        level = 0 if count == 0 or peak == 0 else min(4, 1 + int((count/peak)*3.8))
        row, col = divmod(i,13)
        x=35+col*34; y=190+row*10
        b.append(roundrect(x,y,23,7,palette[level],palette[level],2))
    b.append(text(30,255,"Based on public GitHub events · updates daily",10,MUTED2))
    return frame(510,270,''.join(b),"Live GitHub profile stats")

def language_svg(lang_total):
    items = sorted(lang_total.items(), key=lambda kv: kv[1], reverse=True)[:5]
    total = sum(lang_total.values())
    body = [f'<circle cx="40" cy="42" r="21" fill="#151E28"/>', text(40,49,"L",20,"#2DB7E5",700,"middle"), text(92,49,"Most-used Languages",21,TEXT,600)]
    if not items or total == 0:
        body.append(text(30,98,"Language data unavailable; rerun workflow.",13,MUTED))
    else:
        colors = ["#32C7A1","#2DB7E5","#F4B94B","#B06BF2","#E8799B"]
        y=79
        for i,(name,val) in enumerate(items):
            pct = 100*val/total
            body.append(text(30,y,name,11,TEXT,500))
            body.append(text(450,y,f"{pct:.1f}%",10,MUTED,500,"end"))
            body.append(roundrect(30,y+4,420,5,"#111A24","#111A24",3))
            body.append(roundrect(30,y+4,max(8,420*pct/100),5,colors[i],colors[i],3))
            y += 24
        body.append(text(30,203,"Calculated from public repositories · updates daily",8,MUTED2))
    return frame(480,210,''.join(body),"Languages used across public repositories")

def main():
    try:
        user = get_json(f"https://api.github.com/users/{OWNER}")
        repos = get_json(f"https://api.github.com/users/{OWNER}/repos?per_page=100&type=owner&sort=updated")
        if not isinstance(repos,list): raise RuntimeError("Unexpected repository response")
    except Exception as exc:
        raise SystemExit(f"GitHub API request failed: {exc}")
    try:
        events = get_json(f"https://api.github.com/users/{OWNER}/events/public?per_page=100")
        if not isinstance(events,list): events=[]
    except Exception: events=[]
    languages={}
    for repo in repos:
        if repo.get("fork") or repo.get("private"): continue
        try:
            data=get_json(repo.get("languages_url", ""))
            for lang, n in data.items(): languages[lang]=languages.get(lang,0)+int(n)
        except Exception: continue
    (ASSETS/"github-stats.svg").write_text(stats_svg(user,repos,events),encoding="utf-8")
    if languages:
        (ASSETS/"languages-card.svg").write_text(language_svg(languages),encoding="utf-8")
    print(f"Updated profile metrics for {OWNER}; {len(repos)} repos, {len(languages)} language buckets.")
if __name__ == "__main__": main()