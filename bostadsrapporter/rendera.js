// Renderar sidor med Chromium och skriver ut PDF-länkar, titel och text: node render.js urls.txt > ut.jsonl
const {chromium}=require('playwright');const fs=require('fs');
(async()=>{const urls=fs.readFileSync(process.argv[2],'utf8').split('\n').filter(Boolean);
const b=await chromium.launch();const ctx=await b.newContext({locale:'sv-SE'});
const kö=[...urls];
async function arb(){const p=await ctx.newPage();while(kö.length){const u=kö.shift();
 try{await p.goto(u,{waitUntil:'networkidle',timeout:45000});
  const r=await p.evaluate(()=>({titel:(document.querySelector('meta[property="og:title"]')||{}).content||document.title,
   h1:(document.querySelector('h1')||{}).innerText||'',
   desc:(document.querySelector('meta[property="og:description"]')||document.querySelector('meta[name="description"]')||{}).content||'',
   pdf:[...document.querySelectorAll('a[href]')].map(a=>({url:a.href,text:a.innerText.trim().slice(0,200)})).filter(a=>/\.pdf($|\?)/i.test(a.url)),
   text:(document.querySelector('main')||document.body).innerText.slice(0,20000)}));
  process.stdout.write(JSON.stringify({url:u,...r})+'\n');
 }catch(e){process.stderr.write('fel '+u+' '+e.message.slice(0,80)+'\n')}}await p.close()}
await Promise.all([arb(),arb(),arb(),arb()]);await b.close()})();
