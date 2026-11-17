'use strict';
/* HU continuity signal dashboard. No modeled blackout probability is shown. */
const TZ = 'Europe/Budapest';
const $ = id => document.getElementById(id);
const state = { feeds: {}, errors: {}, generated_at: null, location:'Nyíregyháza, Magyarország' };
const FEEDS = [
  ['weather', 'Open-Meteo', 'Helyi időjárás, 7 nap'],
  ['electricity', 'Energy-Charts', 'Magyar piaci áramár'],
  ['space_weather', 'NOAA SWPC', 'Geomágneses Kp-előrejelzés']
];
function n(x) { if(x===null||x===undefined||x==='')return null; const t=Number(x);return Number.isFinite(t)?t:null; }
function esc(s){return String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function fmtDate(iso){try{return new Intl.DateTimeFormat('hu-HU',{timeZone:TZ,year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit'}).format(new Date(iso));}catch{return '—';}}
function ageHours(iso){const ms=new Date(iso).valueOf();return Number.isFinite(ms)?Math.max(0,(Date.now()-ms)/3600000):Infinity;}
function labelFor(score){if(score<20)return 'Alacsony időjárási kitettség';if(score<45)return 'Mérsékelt időjárási kitettség';if(score<70)return 'Fokozott időjárási kitettség';return 'Magas időjárási kitettség';}
function round(x){return Math.round(x);}
function cap(x){return Math.max(0,Math.min(100,x));}
function gustScore(g){g=n(g)||0;if(g<35)return 0;if(g<50)return (g-35)*1.1;if(g<70)return 17+(g-50)*1.6;if(g<90)return 49+(g-70)*1.55;return Math.min(100,80+(g-90)*0.8);}
function weatherRisk(h){
 const gust=n(h.gust_kmh)||0, snow=n(h.snow_cm)||0, mm=n(h.precip_mm)||0, temp=n(h.temperature_c);
 const wind=gustScore(gust), snowfall=Math.min(80,snow*15), heavyRain=mm>4?Math.min(70,(mm-4)*4):0;
 const frost=(temp!==null && temp < -15)?Math.min(20,(-15-temp)*2):0;
 const compound=(gust>=65 && (snow>0.3 || mm>5))?10:0;
 return round(cap(Math.max(wind,snowfall,heavyRain,frost)+compound));
}
function weatherReason(h){let reason=[];if((n(h.gust_kmh)||0)>=55)reason.push('erős széllökés');if((n(h.snow_cm)||0)>=1)reason.push('havazás');if((n(h.precip_mm)||0)>=8)reason.push('intenzív csapadék');if((n(h.temperature_c)||99)<-15)reason.push('erős fagy');return reason.length?reason.join(' + '):'nincs kiemelkedő meteorológiai tényező';}
function dayCaption(dateString){try{return new Intl.DateTimeFormat('hu-HU',{weekday:'short',month:'short',day:'numeric'}).format(new Date(dateString+'T12:00:00'));}catch{return dateString;}}
function signalHours(){const feed=state.feeds.weather;if(!feed || !Array.isArray(feed.hours) || ageHours(feed.updated_at)>60) return [];
 return feed.hours.filter(h=>typeof h.time==='string' && n(h.gust_kmh)!==null && n(h.precip_mm)!==null && n(h.snow_cm)!==null && h.time >= new Intl.DateTimeFormat('sv-SE',{timeZone:TZ,year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit'}).format(new Date()).replace(' ','T').slice(0,13));
}
function graph(){const hourly=signalHours(), el=$('chart');if(!hourly.length){el.innerHTML='<div class="empty">Nincs friss időjárási előrejelzés.</div>';return;}
 const byDay=new Map();for(const h of hourly){const day=h.time.slice(0,10), r=weatherRisk(h);const val=byDay.get(day);if(!val || r>val.risk)byDay.set(day,{risk:r,peak:h});}
 const entries=[...byDay].slice(0,7);
 el.innerHTML=entries.map(([day,row])=>{
  const c=row.risk>=70?'high':row.risk>=45?'medium':'';
  return `<div class="chart-col" title="${esc(dayCaption(day))}: ${row.risk}/100; ${esc(weatherReason(row.peak))}"><div class="chart-val">${row.risk}</div><div class="chart-bar-wrap"><div class="chart-bar ${c}" style="height:${Math.max(2,row.risk)}%"></div></div><div class="chart-label">${esc(dayCaption(day))}<br><small>${esc(row.peak.time.slice(11,16))}</small></div></div>`;
 }).join('');
 const peak=hourly.reduce((p,h)=>weatherRisk(h)>weatherRisk(p)?h:p,hourly[0]);const max=weatherRisk(peak);
 $('score').textContent=max;$('risk-label').textContent=labelFor(max);$('peak-day').textContent=dayCaption(peak.time.slice(0,10));$('peak-detail').textContent=`${peak.time.slice(11,16)} · index ${max}/100`;$('peak-reason').textContent=weatherReason(peak);
 const maxProb=hourly.reduce((a,h)=>Math.max(a,n(h.rain_probability_pct)||0),0);$('precip-prob').textContent=round(maxProb)+'%';
 const peakTime=esc(dayCaption(peak.time.slice(0,10))+' '+peak.time.slice(11,16));
 const high= max>=70? 'Magas meteorológiai terhelés figyelhető meg a modellben.':max>=45?'Figyelmet érdemlő időjárási terhelés várható.':'Nincs kiemelkedő időjárási terhelési csúcs a modellben.';
 $('scenarios').innerHTML=`
 <div class="scenario"><div><strong>Helyi, időjáráshoz kötődő hálózati zavar</strong><p>${high} A kitettségi csúcs: ${peakTime}. A tényleges áramszünet esélye nem becsülhető ebből.</p></div><span class="st">${max}/100</span></div>
 <div class="scenario"><div><strong>Országos villamosenergia-hiány</strong><p>A jelenlegi adatcsomag nem tartalmaz hiteles, teljes magyar kapacitásmegfelelőségi előrejelzést. Az áramár nem elegendő a kockázat megállapításához.</p></div><span class="st">N/A</span></div>
 <div class="scenario"><div><strong>Rendkívüli űridőjárási esemény</strong><p id="space-scenario">A NOAA-adatok betöltése után ellenőrizhető. Egy magas Kp sem jelent automatikusan áramszünetet.</p></div><span class="st">Kp</span></div>`;
}
function fillMarket(){const feed=state.feeds.electricity,el=$('price');if(!feed || !Array.isArray(feed.prices) || !feed.prices.length || ageHours(feed.updated_at)>60){el.textContent='—';$('price-timestamp').textContent='Friss piaci adat nem áll rendelkezésre';return;}
 const now=Date.now();let candidate=feed.prices.filter(x=>n(x.eur_mwh)!==null && Date.parse(x.time)<=now).pop();if(!candidate)candidate=feed.prices.find(x=>n(x.eur_mwh)!==null);
 if(!candidate){el.textContent='—';return;}el.textContent=Number(candidate.eur_mwh).toLocaleString('hu-HU',{maximumFractionDigits:1});$('price-timestamp').textContent=fmtDate(candidate.time)+' · piaci ár, nem hálózati állapot';
}
function fillKp(){const feed=state.feeds.space_weather;if(!feed||!Array.isArray(feed.kp)||ageHours(feed.updated_at)>60){$('kp').textContent='—';$('kp-detail').textContent='Friss NOAA-előrejelzés nem érhető el';return;}
 const now=Date.now(), limit=now+72*3600000;
 const upcoming=feed.kp.filter(x=>{const t=Date.parse(x.time);return n(x.kp)!==null && t>=now-3600000 && t<=limit;});
 if(!upcoming.length){$('kp').textContent='—';$('kp-detail').textContent='Nincs megfelelő jövőbeli Kp-adat';return;}
 const peak=upcoming.reduce((p,x)=>n(x.kp)>n(p.kp)?x:p,upcoming[0]);
 $('kp').textContent=String(peak.kp);$('kp-detail').textContent=`${fmtDate(peak.time)} · ${peak.kp>=8?'Erős geomágneses vihar lehetséges':peak.kp>=7?'G3 vagy erősebb szint lehetséges':peak.kp>=5?'Geomágneses vihar lehetséges':'Nincs erős geomágneses jelzés'}`;
 const el=$('space-scenario');if(el)el.textContent=`Előrejelzett csúcs Kp ${peak.kp}, ${fmtDate(peak.time)}. Ez nem magyarországi áramszünet-előrejelzés.`;
}
function fillSources(){const valid=FEEDS.filter(([k])=>state.feeds[k] && ageHours(state.feeds[k].updated_at)<36);const hasAny=FEEDS.some(([k])=>state.feeds[k]);
 $('overall-status').textContent=valid.length===3?'3/3 friss adatforrás':valid.length?`${valid.length}/3 friss adatforrás`:hasAny?'Csak régi vagy hiányzó adatok':'Még nincs betöltött adat';
 $('overall-status').className='pill '+(valid.length===3?'good':valid.length?'warn':'');
 $('sources').innerHTML=FEEDS.map(([k,name,detail])=>{
  const f=state.feeds[k],age=f?ageHours(f.updated_at):Infinity;const label=!f?'Nincs adat':age<36?'Friss adat':age<60?'Régi adat':'Elavult adat';const flag=!f?'missing':age<36?'':'stale';
  const from=f?fmtDate(f.updated_at):'Nincs sikeres lekérdezés';
  return `<div class="source"><div class="source-name">${esc(name)}<i class="dot ${flag}" aria-label="${label}"></i></div><div class="source-age">${esc(detail)}<br>${esc(label)} · ${esc(from)}</div></div>`;
 }).join('');
}
function draw(){
 if(!signalHours().length){$('score').textContent='—';$('risk-label').textContent='Nincs friss előrejelzés';$('peak-day').textContent='—';$('peak-detail').textContent='—';$('peak-reason').textContent='—';$('precip-prob').textContent='—';$('scenarios').innerHTML='<div class="empty">Előbb szükség van friss időjárási adatokra.</div>';}
 graph();fillMarket();fillKp();fillSources();
 $('last-checked').textContent=state.generated_at?fmtDate(state.generated_at):'—';
}
function isoEpoch(s){return new Date(Number(s)*1000).toISOString();}
function mapOpenMeteo(d){const h=d.hourly;if(!h||!Array.isArray(h.time)||h.time.length<24)throw Error('Az időjárási adat hiányos');
 const keys=['temperature_2m','wind_gusts_10m','precipitation_probability','precipitation','snowfall'];if(keys.some(k=>!Array.isArray(h[k])))throw Error('Hiányzó időjárási mező');
 return {updated_at:new Date().toISOString(),hours:h.time.map((t,i)=>({time:String(t),temperature_c:h.temperature_2m[i],gust_kmh:h.wind_gusts_10m[i],rain_probability_pct:h.precipitation_probability[i],precip_mm:h.precipitation[i],snow_cm:h.snowfall[i]}))};}
function mapEnergy(d){if(!Array.isArray(d.unix_seconds)||!Array.isArray(d.price))throw Error('Energiapiaci adatszerkezet hiányos');const prices=d.unix_seconds.map((t,i)=>({time:isoEpoch(t),eur_mwh:n(d.price[i])})).filter(p=>p.eur_mwh!==null);if(!prices.length)throw Error('Nincs villamosenergia-ár');return {updated_at:new Date().toISOString(),prices:prices.slice(-160)};}
function mapSpace(d){if(!Array.isArray(d)||d.length<2)throw Error('Hiányos NOAA-adat');const header=d[0].map(v=>String(v).toLowerCase()),ti=header.indexOf('time_tag')>=0?header.indexOf('time_tag'):0,ki=header.findIndex(s=>s==='kp'||s==='kp_index'||s==='kp value'||s.startsWith('kp '));const idx=ki>=0?ki:1;
 const kp=d.slice(1).map(r=>({time:(String(r[ti]).replace(' ','T').endsWith('Z')?String(r[ti]).replace(' ','T'):String(r[ti]).replace(' ','T')+'Z'),kp:n(r[idx])})).filter(x=>x.kp!==null&&Number.isFinite(Date.parse(x.time)));
 if(!kp.length)throw Error('Nincs feldolgozható Kp');return {updated_at:new Date().toISOString(),kp:kp.slice(-120)};
}
async function getJSON(url){const c=new AbortController(),t=setTimeout(()=>c.abort(),18000);try{const r=await fetch(url,{signal:c.signal,cache:'no-store'});if(!r.ok)throw Error('HTTP '+r.status);return await r.json();}finally{clearTimeout(t);}}
async function refresh(){const button=$('refresh');button.disabled=true;button.textContent='⟳ Lekérdezés…';state.errors={};
 const today=new Date().toISOString().slice(0,10),yesterday=new Date(Date.now()-86400000).toISOString().slice(0,10),after=new Date(Date.now()+2*86400000).toISOString().slice(0,10);
 const queries=[
  ['weather','https://api.open-meteo.com/v1/forecast?latitude=47.9561&longitude=21.7187&hourly=temperature_2m,wind_gusts_10m,precipitation_probability,precipitation,snowfall&timezone=Europe%2FBudapest&forecast_days=7',mapOpenMeteo],
  ['electricity',`https://api.energy-charts.info/price?bzn=HU&start=${yesterday}&end=${after}`,mapEnergy],
  ['space_weather','https://services.swpc.noaa.gov/products/noaa-planetary-k-index-forecast.json',mapSpace]
 ];
 let got=0;await Promise.all(queries.map(async ([key,url,parse])=>{try{state.feeds[key]=parse(await getJSON(url));got++;}catch(e){state.errors[key]=String(e.message||e);} }));
 if(got)state.generated_at=new Date().toISOString();draw();button.disabled=false;button.textContent='⟳  Frissítés most';
 if(!got){$('overall-status').textContent='Élő lekérdezés sikertelen · ellenőrizd a forrásokat';$('overall-status').className='pill warn';}
}
async function main(){
 try{const d=await getJSON('data/latest.json');if(d&&d.feeds&&typeof d.feeds==='object'){state.feeds=d.feeds;state.generated_at=d.generated_at;state.errors=d.errors||{};draw();}}catch(e){console.info('Nincs mentett naplóállapot',e.message);draw();}
 await refresh();
}
$('refresh').addEventListener('click',refresh);
main();
