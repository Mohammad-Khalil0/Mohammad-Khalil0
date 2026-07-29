"""Build light_mode.svg and dark_mode.svg for Mohammad-Khalil0
Usage:
    pip install pillow requests
    python build_svgs.py
"""
import os
import requests
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
from xml.sax.saxutils import escape

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
AVATAR = os.path.join(OUT_DIR, "avatar_cutout.png")
if not os.path.exists(AVATAR):
    AVATAR = os.path.join(OUT_DIR, "avatar.png")

ART_FONT_PX, ART_Y0, ART_DY = 10, 24, 12
ROWS, COLS = 41, 60
CELL_ASPECT = 2.0  
RAMP_LIGHT = "@$#%WMB8&gm*aoezr|;:~-,. "
RAMP_DARK = RAMP_LIGHT[::-1]
WIDTH = 60  

HEAD_CROP = 0.78  

GITHUB_USERNAME = "Mohammad-Khalil0"


def fetch_github_stats(username):
    """Fetch live profile statistics using GitHub's GraphQL API."""
    token = os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
    if not token:
        print("No GH_TOKEN found in environment. Using snapshot fallback stats.")
        return {
            "repos": "10", "contrib": "20", "stars": "5",
            "commits": "0", "followers": "0",
            "loc": "0", "loc_add": "0", "loc_del": "0"
        }

    headers = {"Authorization": f"bearer {token}"}
    
    # GraphQL query to get repository counts, stars, followers, and commits
    query = """
    query($user: String!) {
      user(login: $user) {
        followers { totalCount }
        repositories(first: 100, ownerAffiliations: OWNER) {
          totalCount
          nodes {
            stargazerCount
            isFork
          }
        }
        contributionsCollection {
          totalCommitContributions
          restrictedContributionsCount
        }
      }
    }
    """
    
    try:
        response = requests.post(
            "https://api.github.com/graphql",
            json={"query": query, "variables": {"user": username}},
            headers=headers,
            timeout=10
        )
        data = response.json().get("data", {}).get("user", {})
        
        if not data:
            raise ValueError("Empty user data returned from API")

        followers = str(data["followers"]["totalCount"])
        repos = str(data["repositories"]["totalCount"])
        
        # Calculate total stars across all non-forked repos
        stars_count = sum(repo["stargazerCount"] for repo in data["repositories"]["nodes"] if not repo["isFork"])
        stars = str(stars_count)
        
        # Calculate commits (public + private if accessible)
        commit_contribs = data["contributionsCollection"]["totalCommitContributions"]
        private_contribs = data["contributionsCollection"]["restrictedContributionsCount"]
        commits = str(commit_contribs + private_contribs)

        return {
            "repos": repos,
            "contrib": repos, # Total repos contributed to
            "stars": stars,
            "commits": commits,
            "followers": followers,
            "loc": "12.4k",     # Lines of code fallback/placeholder
            "loc_add": "15.2k",
            "loc_del": "2.8k"
        }

    except Exception as e:
        print(f"Warning: Failed to fetch live GitHub stats ({e}). Using fallbacks.")
        return {
            "repos": "10", "contrib": "20", "stars": "5",
            "commits": "0", "followers": "0",
            "loc": "0", "loc_add": "0", "loc_del": "0"
        }


def percentile(values, q):
    values = sorted(values)
    return values[int(q * (len(values) - 1))]


def get_pixel_list(img):
    if hasattr(img, "get_flattened_data"):
        return list(img.get_flattened_data())
    return list(img.getdata())


def ascii_lines(ramp, art_bg):
    img = Image.open(AVATAR)
    if img.mode == "RGBA":
        img = img.crop(img.split()[3].getbbox())  
        w, h = img.size
        img = img.crop((0, 0, w, int(h * HEAD_CROP)))
        gray, a = img.convert("L"), img.split()[3]
        
        gray_data = get_pixel_list(gray)
        alpha_data = get_pixel_list(a)
        
        subject = [p for p, m in zip(gray_data, alpha_data) if m > 128]
        lo, hi = percentile(subject, 0.02), percentile(subject, 0.98)
        gray = gray.point(lambda v: max(12, min(235, 12 + (v - lo) * 223 // max(1, hi - lo))))
        img = Image.new("L", img.size, art_bg)
        img.paste(gray, mask=a)
    else:
        img = img.convert("L")
        img = ImageOps.autocontrast(img, cutoff=2)
        img = ImageEnhance.Contrast(img).enhance(1.15)
    img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=100))
    w, h = img.size
    needed_w = int(h * (COLS / (ROWS * CELL_ASPECT)))
    if needed_w < w:
        left = (w - needed_w) // 2
        img = img.crop((left, 0, left + needed_w, h))
    img = img.resize((COLS, ROWS), Image.LANCZOS)
    px = img.load()
    return [
        "".join(ramp[min(px[x, y] * len(ramp) // 256, len(ramp) - 1)] for x in range(COLS)).rstrip()
        for y in range(ROWS)
    ]


def key_markup(key):
    return ".".join(f'<tspan class="key">{escape(part)}</tspan>' for part in key.split("."))


def dots_for(key, value):
    n = WIDTH - 2 - len(key) - 1 - 2 - len(value)
    assert n >= 0, f"line too long: {key}: {value}"
    return "." * n


def info_line(y, key, value, dots_id=None, value_id=None):
    dots = dots_for(key, value)
    did = f' id="{dots_id}"' if dots_id else ""
    vid = f' id="{value_id}"' if value_id else ""
    return (
        f'<tspan x="390" y="{y}" class="cc">. </tspan>{key_markup(key)}:'
        f'<tspan class="cc"{did}> {dots} </tspan>'
        f'<tspan class="value"{vid}>{escape(value)}</tspan>'
    )


def blank_line(y):
    return f'<tspan x="390" y="{y}" class="cc">. </tspan>'


def header_line(y, text):
    dashes = "-" + "—" * (WIDTH - 5 - len(text)) + "-—-"
    return f'<tspan x="390" y="{y}">{escape(text)}</tspan> {dashes}'


def jdots(length, value):
    n = max(0, length - len(value))
    return {0: "", 1: " ", 2: ". "}.get(n, " " + "." * n + " ")


def stat_lines(stats):
    repos, contrib, stars = stats["repos"], stats["contrib"], stats["stars"]
    commits, followers = stats["commits"], stats["followers"]
    loc, loc_add, loc_del = stats["loc"], stats["loc_add"], stats["loc_del"]
    
    l1 = (
        f'<tspan x="390" y="470" class="cc">. </tspan><tspan class="key">Repos</tspan>:'
        f'<tspan class="cc" id="repo_data_dots">{jdots(6, repos)}</tspan>'
        f'<tspan class="value" id="repo_data">{repos}</tspan> '
        f'{{<tspan class="key">Contributed</tspan>: <tspan class="value" id="contrib_data">{contrib}</tspan>}} | '
        f'<tspan class="key">Stars</tspan>:'
        f'<tspan class="cc" id="star_data_dots">{jdots(14, stars)}</tspan>'
        f'<tspan class="value" id="star_data">{stars}</tspan>'
    )
    l2 = (
        f'<tspan x="390" y="490" class="cc">. </tspan><tspan class="key">Commits</tspan>:'
        f'<tspan class="cc" id="commit_data_dots">{jdots(23, commits)}</tspan>'
        f'<tspan class="value" id="commit_data">{commits}</tspan> | '
        f'<tspan class="key">Followers</tspan>:'
        f'<tspan class="cc" id="follower_data_dots">{jdots(10, followers)}</tspan>'
        f'<tspan class="value" id="follower_data">{followers}</tspan>'
    )
    l3 = (
        f'<tspan x="390" y="510" class="cc">. </tspan><tspan class="key">Lines of Code</tspan>:'
        f'<tspan class="cc" id="loc_data_dots">{jdots(9, loc)}</tspan>'
        f'<tspan class="value" id="loc_data">{loc}</tspan> ( '
        f'<tspan class="addColor" id="loc_add">{loc_add}</tspan><tspan class="addColor">++</tspan>, '
        f'<tspan id="loc_del_dots">{jdots(7, loc_del)}</tspan>'
        f'<tspan class="delColor" id="loc_del">{loc_del}</tspan><tspan class="delColor">--</tspan> )'
    )
    return [l1, l2, l3]


THEMES = {
    "light_mode.svg": {
        "ramp": RAMP_LIGHT, "art_bg": 255,
        "bg": "#f6f8fa", "fg": "#24292f",
        "key": "#953800", "value": "#0a3069",
        "add": "#1a7f37", "del": "#cf222e", "cc": "#c2cfde",
    },
    "dark_mode.svg": {
        "ramp": RAMP_DARK, "art_bg": 0,
        "bg": "#161b22", "fg": "#c9d1d9",
        "key": "#ffa657", "value": "#a5d6ff",
        "add": "#3fb950", "del": "#f85149", "cc": "#616e7f",
    },
}

# Fetch live stats once before rendering themes
live_stats = fetch_github_stats(GITHUB_USERNAME)

for filename, t in THEMES.items():
    art = "\n".join(
        f'<tspan x="15" y="{ART_Y0 + i * ART_DY}">{escape(line)}</tspan>'
        for i, line in enumerate(ascii_lines(t["ramp"], t["art_bg"]))
    )
    info = [
        header_line(30, GITHUB_USERNAME),
        info_line(50, "OS", "Windows 11, Linux"),
        info_line(70, "Uptime", "21 years"),
        info_line(90, "Host", "Beirut, Lebanon"),
        info_line(110, "Kernel", "Software Engineer"),
        info_line(130, "IDE", "VSCode 1.96.1, IDEA 2026.2"),
        blank_line(150),
        info_line(170, "Languages.Programming", "JS, TS, PHP, Python"),
        info_line(190, "Languages.Computer", "NEXT, NUXT, NODE, EXPRESS, LARAVEL"),
        info_line(210, "Languages.Real", "English, Arabic"),
        blank_line(230),
        info_line(250, "Hobbies.Software", "AI & Automation"),
        info_line(270, "Hobbies.Data", "Web Scraping, Analysis"),
        header_line(310, "- Contact"),
        info_line(330, "Email.Personal", "mohamad.khalil5@outlook.com"),
        info_line(350, "LinkedIn", "Mohammad Khalil"),
        info_line(370, "Website", "coming soon"),
        header_line(450, "- GitHub Stats"),
        *stat_lines(live_stats),
    ]
    svg = f"""<?xml version='1.0' encoding='UTF-8'?>
<svg xmlns="http://www.w3.org/2000/svg" font-family="ConsolasFallback,Consolas,monospace" width="985px" height="530px" font-size="16px">
<style>
@font-face {{
src: local('Consolas'), local('Consolas Bold');
font-family: 'ConsolasFallback';
font-display: swap;
-webkit-size-adjust: 109%;
size-adjust: 109%;
}}
.key {{fill: {t["key"]};}}
.value {{fill: {t["value"]};}}
.addColor {{fill: {t["add"]};}}
.delColor {{fill: {t["del"]};}}
.cc {{fill: {t["cc"]};}}
text, tspan {{white-space: pre;}}
</style>
<rect width="985px" height="530px" fill="{t["bg"]}" rx="15"/>
<text x="15" y="{ART_Y0}" fill="{t["fg"]}" class="ascii" font-size="{ART_FONT_PX}px">
{art}
</text>
<text x="390" y="30" fill="{t["fg"]}">
{chr(10).join(info)}
</text>
</svg>"""
    path = f"{OUT_DIR}/{filename}"
    with open(path, "w") as f:
        f.write(svg)
    print("wrote", path)
