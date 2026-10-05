import json, sys
from playwright.sync_api import sync_playwright
BASE="https://web-green-kappa-79.vercel.app"
OUT=sys.argv[1]
res={}
with sync_playwright() as p:
    b=p.chromium.launch()
    for name,vp,mobile in [("pc",{"width":1440,"height":900},False),("mo",{"width":390,"height":844},True)]:
        ctx=b.new_context(viewport=vp,is_mobile=mobile,has_touch=mobile,device_scale_factor=2 if mobile else 1,locale="ko-KR")
        pg=ctx.new_page()
        pg.goto(BASE,wait_until="networkidle",timeout=60000)
        pg.wait_for_timeout(1500)
        pg.screenshot(path=f"{OUT}/{name}_home_fold.png")
        pg.screenshot(path=f"{OUT}/{name}_home_full.png",full_page=True)
        info=pg.evaluate("""()=>{
          const h=document.documentElement.scrollHeight, vh=innerHeight;
          const feed=[...document.querySelectorAll('h2')].map(e=>({t:e.textContent,y:e.getBoundingClientRect().top+scrollY}));
          const cards=document.querySelectorAll('a[href^="/video/"]').length;
          const firstCard=document.querySelector('a[href^="/video/"]');
          const inp=document.querySelector('input');
          const btns=[...document.querySelectorAll('button')].map(b=>b.textContent.trim().slice(0,30));
          const fonts=[...document.querySelectorAll('*')].filter(e=>e.children.length==0&&e.textContent.trim()).map(e=>parseFloat(getComputedStyle(e).fontSize));
          const small=fonts.filter(f=>f<12).length;
          return {scrollH:h,vh,screens:(h/vh).toFixed(1),h2:feed,cards,firstCardY:firstCard?firstCard.getBoundingClientRect().top+scrollY:null,inputY:inp?inp.getBoundingClientRect().top+scrollY:null,buttons:btns,textNodes:fonts.length,under12px:small,hscroll:document.documentElement.scrollWidth>innerWidth}
        }""")
        res[name+"_home"]=info
        # first video link
        href=pg.eval_on_selector('a[href^="/video/"]','e=>e.getAttribute("href")')
        res[name+"_firstvideo"]=href
        # infinite scroll depth: scroll 3 times
        for i in range(3):
            pg.mouse.wheel(0,20000); pg.wait_for_timeout(2500)
        res[name+"_after_scroll_cards"]=pg.evaluate('document.querySelectorAll(\'a[href^="/video/"]\').length')
        # search
        pg.goto(BASE,wait_until="networkidle"); pg.fill("input","엔비디아"); pg.wait_for_timeout(4000)
        pg.screenshot(path=f"{OUT}/{name}_search.png")
        res[name+"_search_cards"]=pg.evaluate('document.querySelectorAll(\'a[href^="/video/"]\').length')
        # video detail
        pg.goto(BASE+href,wait_until="networkidle"); pg.wait_for_timeout(1500)
        pg.screenshot(path=f"{OUT}/{name}_video_fold.png")
        pg.screenshot(path=f"{OUT}/{name}_video_full.png",full_page=True)
        res[name+"_video"]=pg.evaluate("""()=>({scrollH:document.documentElement.scrollHeight,screens:(document.documentElement.scrollHeight/innerHeight).toFixed(1),h:[...document.querySelectorAll('h1,h2,h3')].map(e=>e.tagName+':'+e.textContent.trim().slice(0,40)),quotes:document.querySelectorAll('blockquote, a[href*="youtube.com/watch"]').length,hscroll:document.documentElement.scrollWidth>innerWidth})""")
        # channel page
        pg.goto(BASE,wait_until="networkidle")
        ch=pg.eval_on_selector('a[href^="/channel/"]','e=>e.getAttribute("href")')
        pg.goto(BASE+ch,wait_until="networkidle"); pg.wait_for_timeout(1500)
        pg.screenshot(path=f"{OUT}/{name}_channel_fold.png")
        res[name+"_channel"]={"href":ch,"scrollH":pg.evaluate("document.documentElement.scrollHeight"),"buttons":pg.evaluate("[...document.querySelectorAll('button')].map(b=>b.textContent.trim().slice(0,30))")}
        ctx.close()
    b.close()
print(json.dumps(res,ensure_ascii=False,indent=1))
