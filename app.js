'use strict';
/* HU continuity signal dashboard. No modeled blackout probability is shown. */
const TZ = 'Europe/Budapest';
const $ = id => document.getElementById(id);
const state = { feeds: {}, errors: {}, generated_at: null, assessment:null, location:'Nyíregyháza, Magyarország' };
const FEEDS = [
  ['weather', 'Open-Meteo', 'Helyi időjárás, 7 nap'],
  ['electricity', 'Energy-Charts', 'Magyar piaci áramár'],
  ['space_weather', 'NOAA SWPC', 'Geomágneses Kp-előrejelzés'],
  ['european_prices','Energy-Charts – európai','Országonkénti villamosenergia-piaci árak'],
  ['europe_weather','Open-Meteo – Európa','Kiválasztott európai városok 72h előrejelzése'],
  ['meteoalarm','Meteoalarm','Európai meteorológiai hírfolyamok'],
  ['ews','Apocalypse EWS','Kísérleti magánrepülőgép-indikátor'],
  ['official_news','Európai Bizottság / GDACS','Hivatalos hírek és események'],
  ['gie_storage','GIE AGSI+','Opcionális magyar gáztárolói adatok'],
  ['entsoe_hu_load','ENTSO-E','Opcionális magyar terhelés-előrejelzés'],
  ['grid_context','Energy-Charts v2','Európai hálózati kontextus (adatfüggő)'],
  ['cap_warnings','Meteoalarm CAP','Aktív, időbélyegzett hivatalos riasztások']
];
function n(x) { if(x===null||x===undefined||x==='')return null; const t=Number(x);return Number.isFinite(t)?t:null; }
function safeUrl(s){return typeof s==='string' && /^https:\/\//.test(s) ? esc(s) : '#';}
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
function fillSources(){
 const core=['weather','electricity','space_weather','european_prices','europe_weather','meteoalarm'];
 const h=state.assessment?.health;
 const sourceStatus=new Map((h?.items||[]).map(row=>[row.key,row.status]));
 const fresh=core.filter(k=>sourceStatus.has(k)?sourceStatus.get(k)==='fresh':
   (state.feeds[k] && ageHours(state.feeds[k].updated_at)<36 && !state.errors[k]));
 $('overall-status').textContent=`${fresh.length}/${core.length} alapforrás friss`;
 $('overall-status').className='pill '+(fresh.length===core.length?'good':'warn');
 $('sources').innerHTML=FEEDS.map(([k,name,detail])=>{
  const f=state.feeds[k],age=f?ageHours(f.updated_at):Infinity;
  const optional=['gie_storage','entsoe_hu_load'].includes(k);
  const err=state.errors[k]||'';
  const notConfigured=optional && /GitHub Secret nincs megadva/i.test(err);
  const failing=Boolean(err) && !notConfigured;
  const label=notConfigured?'Nincs konfigurálva (opcionális)':failing?'Lekérdezési hiba':!f?'Nincs adat':age<36?'Friss adat':age<60?'Régi adat':'Elavult adat';
  const flag=notConfigured?'stale':failing?'missing':!f?'missing':age<36?'':'stale';
  const from=f?fmtDate(f.updated_at):'Nincs sikeres lekérdezés';
  const errHtml=err?`<span class="source-error">${esc(err)}</span>`:'';
  const partial=Array.isArray(f?.partial_errors)&&f.partial_errors.length?
    `<span class="source-error">Részleges hibák: ${esc(f.partial_errors.slice(0,4).map(x=>typeof x==='string'?x:((x.key||'?')+': '+(x.reason||''))).join(' | '))}</span>`:'';
  return `<div class="source"><div class="source-name">${esc(name)}<i class="dot ${flag}" aria-label="${label}"></i></div><div class="source-age">${esc(detail)}<br>${esc(label)} · ${esc(from)}${errHtml}${partial}</div></div>`;
 }).join('');
}
function draw(){
 if(!signalHours().length){$('score').textContent='—';$('risk-label').textContent='Nincs friss előrejelzés';$('peak-day').textContent='—';$('peak-detail').textContent='—';$('peak-reason').textContent='—';$('precip-prob').textContent='—';$('scenarios').innerHTML='<div class="empty">Előbb szükség van friss időjárási adatokra.</div>';}
 graph();fillMarket();fillKp();fillSources();fillCategories();fillEurope();fillNews();fillAlternatives();fillCross();fillWindows();fillGridContext();fillCAP();
 $('last-checked').textContent=state.generated_at?fmtDate(state.generated_at)+' · GitHub Actions':'—';
}
function isoEpoch(s){return new Date(Number(s)*1000).toISOString();}
function mapOpenMeteo(d){const h=d.hourly;if(!h||!Array.isArray(h.time)||h.time.length<24)throw Error('Az időjárási adat hiányos');
 const keys=['temperature_2m','wind_gusts_10m','precipitation_probability','precipitation','snowfall'];if(keys.some(k=>!Array.isArray(h[k])))throw Error('Hiányzó időjárási mező');
 return {updated_at:new Date().toISOString(),hours:h.time.map((t,i)=>({time:String(t),temperature_c:h.temperature_2m[i],gust_kmh:h.wind_gusts_10m[i],rain_probability_pct:h.precipitation_probability[i],precip_mm:h.precipitation[i],snow_cm:h.snowfall[i]}))};}
function mapEnergy(d){if(!Array.isArray(d.unix_seconds)||!Array.isArray(d.price))throw Error('Energiapiaci adatszerkezet hiányos');const prices=d.unix_seconds.map((t,i)=>({time:isoEpoch(t),eur_mwh:n(d.price[i])})).filter(p=>p.eur_mwh!==null);if(!prices.length)throw Error('Nincs villamosenergia-ár');return {updated_at:new Date().toISOString(),prices:prices.slice(-160)};}
function mapSpace(d){
 if(!Array.isArray(d)||!d.length)throw Error('Hiányos NOAA-adat');
 let pairs=[];
 if(d[0] && typeof d[0]==='object' && !Array.isArray(d[0])){
   pairs=d.map(r=>[r.time_tag??r.time,r.kp]);
 }else if(Array.isArray(d[0])){
   const header=d[0].map(v=>String(v).toLowerCase());
   const ti=Math.max(0,header.indexOf('time_tag'));
   const ki=header.indexOf('kp')>=0?header.indexOf('kp'):1;
   pairs=d.slice(1).filter(Array.isArray).map(r=>[r[ti],r[ki]]);
 }else throw Error('Ismeretlen NOAA-adatformátum');
 const kp=pairs.map(([t,v])=>{
   const iso=String(t??'').trim().replace(' ','T');
   const tm=/Z$|[+-]\d{2}:?\d{2}$/.test(iso)?iso:iso+'Z';
   return {time:tm,kp:n(v)};
 }).filter(x=>x.kp!==null&&x.kp>=0&&x.kp<=9&&Number.isFinite(Date.parse(x.time)));
 if(!kp.length)throw Error('Nincs feldolgozható NOAA Kp-adat');
 return {updated_at:new Date().toISOString(),kp:kp.slice(-120)};
}
async function getJSON(url){const c=new AbortController(),t=setTimeout(()=>c.abort(),18000);try{const r=await fetch(url,{signal:c.signal,cache:'no-store'});if(!r.ok)throw Error('HTTP '+r.status);return await r.json();}finally{clearTimeout(t);}}
async function refresh(){const button=$('refresh');button.disabled=true;button.textContent='⟳ Lekérdezés…';for(const key of ['weather','electricity','space_weather'])delete state.errors[key];
 const today=new Date().toISOString().slice(0,10),yesterday=new Date(Date.now()-86400000).toISOString().slice(0,10),after=new Date(Date.now()+2*86400000).toISOString().slice(0,10);
 const queries=[
  ['weather','https://api.open-meteo.com/v1/forecast?latitude=47.9561&longitude=21.7187&hourly=temperature_2m,wind_gusts_10m,precipitation_probability,precipitation,snowfall&timezone=Europe%2FBudapest&forecast_days=7',mapOpenMeteo],
  ['electricity',`https://api.energy-charts.info/price?bzn=HU&start=${yesterday}&end=${after}`,mapEnergy],
  ['space_weather','https://services.swpc.noaa.gov/products/noaa-planetary-k-index-forecast.json',mapSpace]
 ];
 let got=0;await Promise.all(queries.map(async ([key,url,parse])=>{try{state.feeds[key]=parse(await getJSON(url));got++;}catch(e){state.errors[key]=String(e.message||e);} }));
 draw();button.disabled=false;button.textContent='⟳  3 élő forrás frissítése';
 if(!got){$('overall-status').textContent='Élő lekérdezés sikertelen · ellenőrizd a forrásokat';$('overall-status').className='pill warn';}
}
async function main(){
 try{const d=await getJSON('data/latest.json?t='+Date.now());if(d&&d.feeds&&typeof d.feeds==='object'){state.feeds=d.feeds;state.generated_at=d.generated_at;state.errors=d.errors||{};state.assessment=d.assessment||null;draw();}}catch(e){console.info('Nincs mentett naplóállapot',e.message);draw();}
 await refresh();
}
$('refresh').addEventListener('click',refresh);
main();


function fillCategories(){
 const el=$('category-list'), data=state.assessment, fresh=data&&ageHours(data.generated_at)<30;
 if(!fresh){$('category-overall').textContent='N/A';$('category-window').textContent='Nincs friss értékelés';$('category-coverage').textContent='GitHub Actions futtatása szükséges';el.innerHTML='<div class="empty">Nincs friss szerveroldali kategóriaindex. GitHub Actions → Run workflow.</div>';return;}
 $('category-overall').textContent=data.overall.score===null?'N/A':`${data.overall.score}/100`;
 $('category-window').textContent=`${fmtDate(data.generated_at)} – +24 óra`;
 $('category-coverage').textContent=`Lefedettség: ${data.overall.coverage}/${data.overall.total_categories}. Hiányzó kategóriák ≠ 0 pont.`;
 el.innerHTML=(data.categories||[]).map(c=>{
  const score=n(c.score), over=score!==null&&score>=50;
  const scoreText=score===null?'Nem becsülhető':`${score}/100${over?' ⚠':''}`;
  const evidence=(Array.isArray(c.evidence)?c.evidence:[]).slice(0,2).map(e=>`<div class="category-evidence">${esc(e.detail||'')} · <a href="${safeUrl(e.url)}" rel="noopener noreferrer" target="_blank">${esc(e.source||'Forrás')} ↗</a></div>`).join('');
  const note=c.status==='verified_notice'?'Ellenőrzött hivatalos figyelmeztetés':c.status==='official_cap'?'Érvényes hivatalos CAP riasztás (a jelölt térségre)':c.status==='estimated_index'?'Szabályalapú indikátor':'Nincs megbízható 24h modell vagy ellenőrzött riasztás';
  return `<article class="category-row"><div class="category-head"><strong>${esc(c.name)}</strong><span class="category-score ${over?'trigger':score===null?'category-unknown':''}">${esc(scoreText)}</span></div><div class="category-detail">${esc(note)}. ${esc(c.method||'')}${c.peak_time?`<br>Jelzési csúcs: ${esc(fmtDate(c.peak_time))}`:''}</div>${evidence}</article>`;
 }).join('');
}
function fillEurope(){
 const ew=state.feeds.europe_weather,weather=$('europe-weather');
 if(ew && ageHours(ew.updated_at)<36 && Array.isArray(ew.countries)){
  weather.innerHTML=ew.countries.slice().sort((a,b)=>(n(b.peak_index)||0)-(n(a.peak_index)||0)).slice(0,11).map(x=>`<div class="eu-row"><div><strong>${esc(x.name||x.code)}</strong><p>Városi meteorológiai csúcs: ${esc(fmtDate(x.peak_time))}</p></div><span class="value">${n(x.peak_index)??'—'}/100</span></div>`).join('');
 }else weather.innerHTML='<div class="empty">Európai időjárási adat nem érhető el.</div>';
 const ep=state.feeds.european_prices,market=$('europe-prices');
 if(ep&&ageHours(ep.updated_at)<36&&Array.isArray(ep.countries)){
  market.innerHTML=ep.countries.slice().sort((a,b)=>Math.abs(n(b.recent_eur_mwh)||0)-Math.abs(n(a.recent_eur_mwh)||0)).slice(0,12).map(x=>`<div class="eu-row"><div><strong>${esc(x.name)}</strong><p>${esc(fmtDate(x.latest_time))} · legutóbbi elérhető spotár</p></div><span class="value">${n(x.recent_eur_mwh)?.toLocaleString('hu-HU',{maximumFractionDigits:1})||'—'} €</span></div>`).join('');
 }else market.innerHTML='<div class="empty">Nem áll rendelkezésre friss európai piaci adat.</div>';
 const f=state.feeds.meteoalarm,alerts=$('europe-alerts');
 if(f&&ageHours(f.updated_at)<36){
  const ar=Array.isArray(f.recent_entries)?f.recent_entries:[];
  alerts.innerHTML=ar.length?ar.slice(0,11).map(x=>`<div class="eu-row"><div><strong>${esc(x.name||x.country)}</strong><p>${esc(x.title)}</p><a href="${safeUrl(x.url)}" target="_blank" rel="noopener noreferrer">Forrás és figyelmeztetési részletek ↗</a></div><span class="value small-number">${esc(fmtDate(x.published_at))}</span></div>`).join(''):'<div class="empty">A lekért nemzeti hírfolyamokban nincs friss közlés.</div>';
 }else alerts.innerHTML='<div class="empty">Hivatalos figyelmeztetési adat nem érhető el.</div>';
}
function fillNews(){
 const f=state.feeds.official_news,el=$('official-news');
 if(!f||ageHours(f.updated_at)>36||!Array.isArray(f.items)){el.innerHTML='<div class="empty">Hivatalos hírfolyamok még nem érhetők el.</div>';return;}
 el.innerHTML=f.items.length?f.items.slice(0,12).map(x=>`<div class="news-item"><small>${esc(x.source)} · ${x.published_at?esc(fmtDate(x.published_at)):'dátum nélkül'}</small><a href="${safeUrl(x.url)}" target="_blank" rel="noopener noreferrer">${esc(x.title)} ↗</a></div>`).join(''):'<div class="empty">A hírfolyamban nincs feldolgozható közlés.</div>';
}
function fillAlternatives(){
 const el=$('experimental'), f=state.feeds.ews;
 const ews=f&&ageHours(f.updated_at)<36?`<strong>Apocalypse EWS</strong><p>Magánrepülő-forgalmi anomália: ${n(f.level)!==null?'szint '+n(f.level):'aktuális szint nem értelmezhető'}, ${n(f.airborne_count)!==null?'gép '+n(f.airborne_count):'gépszám nincs'}. Nem blackout-bizonyíték.</p>`:'<strong>Apocalypse EWS</strong><p>Nem sikerült ellenőrzött élő értéket kiolvasni.</p>';
 const gie=state.feeds.gie_storage;
 const gas=gie&&ageHours(gie.updated_at)<36?`<strong>Magyar gáztároló</strong><p>${n(gie.hu?.[0]?.full_pct)??'—'}% töltöttség (GIE); nem 24h ellátás-esély.</p>`:'<strong>GIE AGSI+</strong><p>Opcionális, API-kulcs szükséges az automatikus adathoz.</p>';
 const entsoe=state.feeds.entsoe_hu_load;
 const load=entsoe&&ageHours(entsoe.updated_at)<36?`<strong>HU előrejelzett terhelés</strong><p>Max. ${n(entsoe.max_mw)||'—'} MW (ENTSO-E). Nem termelési kapacitás vagy kiesési esély.</p>`:'<strong>ENTSO-E terhelés</strong><p>Opcionális, API-token szükséges az automatikus adathoz.</p>';
 el.innerHTML=`<div class="eu-row"><div>${ews}<a href="https://ews.kylemcdonald.net/" target="_blank" rel="noopener noreferrer">EWS megnyitása ↗</a></div></div><div class="eu-row"><div>${gas}<a href="https://agsi.gie.eu/" target="_blank" rel="noopener noreferrer">GIE ↗</a></div></div><div class="eu-row"><div>${load}<a href="https://transparency.entsoe.eu/" target="_blank" rel="noopener noreferrer">ENTSO-E ↗</a></div></div>`;
}
function fillCross(){
 const items=[];
 const w=state.assessment?.categories?.find(x=>x.key==='local_power');
 if(n(w?.score)!==null)items.push({title:'Időjárás → helyi hálózati kitettség',text:`${w.score}/100. Villamos hálózati kiesést önmagában nem bizonyít. Csúcs: ${fmtDate(w.peak_time)}.`,note:'Közvetlen meteorológiai kitettségi kapcsolat'});
 const eu=state.feeds.european_prices;
 if(eu&&ageHours(eu.updated_at)<36)items.push({title:'Európai energiaárak → piaci stressz',text:`${eu.countries?.length||0} piaci zóna elérhető. Árkiugrás esetén ellenőrizni kell az okát; önmagában nem hálózati hiány.`,note:'Korreláció és piaci kontextus, nem ok-okozati bizonyíték'});
 const f=state.feeds.space_weather;
 if(f&&ageHours(f.updated_at)<36)items.push({title:'Űridőjárás → elektromos infrastruktúra',text:'A magas Kp indokolhat további hivatalos SWPC-ellenőrzést, de a helyi hatás nem következik automatikusan belőle.',note:'Fizikai kockázati csatorna, hálózatfüggő'});
 const nfeed=state.feeds.official_news;
 if(nfeed&&ageHours(nfeed.updated_at)<36)items.push({title:'Hírek → ellenőrzendő események',text:`${nfeed.items?.length||0} hivatalos híresemény lekérve. Címekből nem képezünk terror-, háború- vagy blackout-esélyt.`,note:'Hírek validálása, nincs automatikus előrejelzési súly'});
 $('cross-signals').innerHTML=items.length?items.map(x=>`<div class="cross-item"><div class="signal-title">${esc(x.title)}</div><div class="signal-body">${esc(x.text)}</div><div class="signal-foot">${esc(x.note)}</div></div>`).join(''):'<div class="empty">Az összefüggésekhez friss adat szükséges.</div>';
}

// V4: independent 24/48/72 windows, data quality and independent power context.
function fillWindows(){
 const a=state.assessment, root=$('window-summaries'),h=$('v4-health');
 if(!root || !h)return;
 const fresh=a&&ageHours(a.generated_at)<30;
 if(!fresh){root.innerHTML='<div class="empty">Nincs friss szerveroldali értékelés. GitHub → Actions → Run workflow.</div>';h.textContent='N/A · az utolsó értékelés hiányzik vagy régi';return;}
 const wins=a.windows||{'24':a};
 root.innerHTML=[24,48,72].map(hours=>{
   const b=wins[String(hours)],overall=b?.overall||{},value=n(overall.score);
   const names=(b?.categories||[]).filter(x=>x.score!==null).sort((x,y)=>y.score-x.score);
   const top=names[0];
   return `<div class="v4-window"><div class="v4-window-label">Következő ${hours} óra</div><div class="v4-window-score">${value===null?'N/A':esc(value)+'/100'}</div><div class="smallmuted">${top?esc(top.name):'Nincs becsülhető jel'}${top?.peak_time?' · '+esc(fmtDate(top.peak_time)):''}</div><div class="smallmuted">Lefedettség: ${n(overall.coverage)||0}/${n(overall.total_categories)||13}</div></div>`;
 }).join('');
 const status=a.health;
 if(status){
  h.innerHTML=`<strong>${status.important_fresh}/${status.important_total} fontos adatforrás friss</strong>${status.degraded?' · HIBÁS / HIÁNYOS':' · figyelés aktív'}<br>${status.important_missing?.length?'Hiányzik: '+esc(status.important_missing.join(', ')):'A fontos források adatai frissek.'}<br>GitHub Actions ütemezés késhet; elmaradt futást önmagában nem tud észlelni.`;
 } else h.textContent='Nincs adatminőségi jelentés. V4 szerveroldali futtatás szükséges.';
}
function fillGridContext(){
 const el=$('v4-grid-context');if(!el)return;
 const feed=state.feeds.grid_context;
 if(!feed||ageHours(feed.updated_at)>36){el.innerHTML='<div class="empty">Nincs friss, ellenőrzött EU hálózati adat. Ez nem jelent alacsony kockázatot.</div>';return;}
 const readings=Array.isArray(feed.readings)?feed.readings:[];
 el.innerHTML=readings.length?readings.map(r=>{
  const series=(r.series||[]).slice(0,4).map(s=>`${esc(s.name)}: ${n(s.latest?.value)?.toLocaleString('hu-HU',{maximumFractionDigits:2})??'—'} ${esc(s.unit||'')} (${esc(fmtDate(s.latest?.time))})`).join('<br>');
  return `<div class="eu-row"><div><strong>${esc(r.name)}</strong><p>${series}</p><a href="${safeUrl(r.source_url)}" target="_blank" rel="noopener noreferrer">Adatforrás ↗</a></div></div>`;
 }).join(''):'<div class="empty">A lekért adat formátuma nem volt feldolgozható.</div>';
 if(feed.partial_errors?.length)el.innerHTML+=`<div class="smallmuted">Részleges adathiány: ${esc(feed.partial_errors.map(x=>x.key).join(', '))}</div>`;
}
function fillCAP(){
 const el=$('v4-cap');if(!el)return;
 const f=state.feeds.cap_warnings;
 if(!f||ageHours(f.updated_at)>36){el.innerHTML='<div class="empty">Nincs friss CAP adat; használd a hivatalos Meteoalarm/VÉSZ oldalt.</div>';return;}
 const alerts=(f.alerts||[]).filter(x=>Date.parse(x.expires)>Date.now()).slice(0,12);
 el.innerHTML=alerts.length?alerts.map(a=>`<div class="eu-row"><div><strong>${esc(a.country)} · ${esc(a.title||a.event)}</strong><p>Erősség: ${esc(a.severity)} · ${esc(a.area)}<br>${esc(fmtDate(a.onset))} – ${esc(fmtDate(a.expires))}</p><a href="${safeUrl(a.url)}" target="_blank" rel="noopener noreferrer">Hivatalos CAP ↗</a></div></div>`).join(''):'<div class="empty">Nincs a feldolgozott országokra vonatkozó aktív, időben érvényes CAP-üzenet. Ez nem kizárólagos hatósági riasztási csatorna.</div>';
}
