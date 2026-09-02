import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SERVICE_ROLE = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const RESEND_API_KEY = Deno.env.get("RESEND_API_KEY") || "";
const FROM_EMAIL = Deno.env.get("FROM_EMAIL") || "";
const WHATSAPP_TOKEN = Deno.env.get("WHATSAPP_TOKEN") || "";
const WHATSAPP_PHONE_NUMBER_ID = Deno.env.get("WHATSAPP_PHONE_NUMBER_ID") || "";
const WHATSAPP_TEMPLATE_NAME = Deno.env.get("WHATSAPP_TEMPLATE_NAME") || "";
const WHATSAPP_TEMPLATE_LANG = Deno.env.get("WHATSAPP_TEMPLATE_LANG") || "it";
const ENDPOINT = `${SUPABASE_URL}/functions/v1/f1-lead-intake`;
const PRIVACY_URL = "https://f1immobiliare.com/policies/privacy-policy";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
};

function esc(v: unknown) { return String(v ?? "").replace(/[&<>\"']/g, m => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[m]!)); }
function clean(v: unknown, max=200) { return String(v ?? "").replace(/[<>]/g, "").trim().slice(0,max); }
function phone(v: unknown) { return clean(v,40).replace(/[^+\d]/g,""); }
function emailOk(v: string) { return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v); }
function json(status:number, body:unknown) { return new Response(JSON.stringify(body), {status, headers:{...corsHeaders,"Content-Type":"application/json; charset=utf-8","Cache-Control":"no-store"}}); }
function html(body:string) { return new Response(body,{status:200,headers:{...corsHeaders,"Content-Type":"text/html; charset=utf-8","Cache-Control":"no-store"}}); }

function scoreLead(i:any) {
  const t=Math.max(0,Number(i.purchase_timing_days||0)); const b=Math.max(0,Number(i.budget_max||0)); let s=0;
  if(t>0&&t<=30)s+=35; else if(t<=90&&t>0)s+=25; else if(t<=180&&t>0)s+=12;
  if(b>0)s+=15; if(Boolean(i.off_market_interest))s+=15; if(Boolean(i.mortgage_needed))s+=5;
  if(clean(i.desired_area))s+=10; if(clean(i.property_type))s+=10;
  if(emailOk(clean(i.email).toLowerCase())&&phone(i.phone).length>=8)s+=10;
  return {score:Math.min(100,s),temperature:s>=70?"CALDO":s>=40?"TIEPIDO":"FREDDO"};
}

async function chooseMagnet(sb:any,i:any){
  const area=clean(i.desired_area,120); const t=Math.max(0,Number(i.purchase_timing_days||0)); let code="guida-acquisto";
  if(Boolean(i.first_home)||Boolean(i.mortgage_needed))code="checklist-prima-casa";
  if((t>0&&t<=90)||Boolean(i.off_market_interest)){
    let q=sb.from("f1_market_opportunities").select("id",{count:"exact",head:true}).or("stato_annuncio.is.null,stato_annuncio.neq.Chiuso");
    if(area)q=q.ilike("comune",`%${area}%`);
    const {count}=await q; if((count||0)>0)code="lista-riservata";
  }
  const {data}=await sb.from("f1_lead_magnets").select("code,title,audience_stage,asset_url").eq("code",code).eq("active",true).maybeSingle();
  return data||{code:"guida-acquisto",title:"Guida pratica all'acquisto casa",audience_stage:"informativo",asset_url:""};
}

async function sendEmail(to:string,name:string,title:string,url:string){
  if(!RESEND_API_KEY||!FROM_EMAIL||!url)return "unconfigured";
  const r=await fetch("https://api.resend.com/emails",{method:"POST",headers:{Authorization:`Bearer ${RESEND_API_KEY}`,"Content-Type":"application/json"},body:JSON.stringify({from:FROM_EMAIL,to:[to],subject:`Il materiale richiesto: ${title}`,html:`<p>Ciao ${esc(name)},</p><p>qui trovi il materiale richiesto:</p><p><a href="${esc(url)}">Apri ${esc(title)}</a></p><p>F1 Immobiliare</p>`})});
  return r.ok?"sent":`failed:${r.status}`;
}

async function sendWhatsApp(to:string,name:string,title:string,url:string){
  if(!WHATSAPP_TOKEN||!WHATSAPP_PHONE_NUMBER_ID||!WHATSAPP_TEMPLATE_NAME||!url)return "unconfigured";
  const digits=to.replace(/\D/g,""); if(!digits)return "invalid_phone";
  const r=await fetch(`https://graph.facebook.com/v23.0/${WHATSAPP_PHONE_NUMBER_ID}/messages`,{method:"POST",headers:{Authorization:`Bearer ${WHATSAPP_TOKEN}`,"Content-Type":"application/json"},body:JSON.stringify({messaging_product:"whatsapp",to:digits,type:"template",template:{name:WHATSAPP_TEMPLATE_NAME,language:{code:WHATSAPP_TEMPLATE_LANG},components:[{type:"body",parameters:[{type:"text",text:name||"cliente"},{type:"text",text:title},{type:"text",text:url}]}]}})});
  return r.ok?"sent":`failed:${r.status}`;
}

function landingPage(u:URL){
  const campaign=esc(u.searchParams.get("utm_campaign")||u.searchParams.get("campaign")||"");
  return `<!doctype html><html lang="it"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Guida acquirenti | F1 Immobiliare</title><style>
  :root{--navy:#0e2742;--green:#197447;--gold:#c3a15c;--bg:#eef2f6;--line:#d7dee7;--text:#1d2939}*{box-sizing:border-box}body{margin:0;font-family:Arial,sans-serif;background:var(--bg);color:var(--text)}main{max-width:1080px;margin:auto;padding:28px 16px 60px}.hero{background:linear-gradient(135deg,var(--navy),#143657);color:#fff;border-radius:26px;padding:44px;border-bottom:5px solid var(--gold)}.ey{font-size:12px;font-weight:900;letter-spacing:.1em;color:var(--gold)}h1{font-size:clamp(38px,6vw,64px);line-height:1.02;margin:10px 0 16px}.hero p{font-size:18px;line-height:1.55;max-width:760px;color:#d8e1ea}.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-top:18px}.card{background:#fff;border:1px solid var(--line);border-radius:18px;padding:26px;box-shadow:0 10px 30px rgba(14,39,66,.08)}h2{color:var(--navy)}label{display:block;font-weight:800;margin:12px 0 5px}input,select{width:100%;padding:12px;border:1px solid #cbd5df;border-radius:9px;font:inherit}input[type=checkbox]{width:auto}.two{display:grid;grid-template-columns:1fr 1fr;gap:10px}.checks label{font-weight:600}.btn{width:100%;border:0;border-radius:10px;padding:15px;background:var(--green);color:#fff;font-weight:900;font-size:16px;cursor:pointer;margin-top:16px}.muted{color:#667085;font-size:13px;line-height:1.45}.success{display:none;background:#ecfdf3;border:1px solid #b7e7c7;padding:18px;border-radius:14px;margin-top:14px}.success a{display:inline-block;background:var(--navy);color:#fff;text-decoration:none;padding:12px 15px;border-radius:9px;font-weight:800}.error{color:#a52a2a;margin-top:10px}.hp{position:absolute;left:-10000px}@media(max-width:780px){.grid,.two{grid-template-columns:1fr}.hero{padding:28px}}</style></head><body><main>
  <section class="hero"><div class="ey">F1 IMMOBILIARE · ACQUIRENTI</div><h1>Prima di comprare casa, evita gli errori che costano tempo e denaro.</h1><p>Compila il profilo di ricerca. Il sistema sceglie automaticamente il contenuto più utile per te: guida, checklist prima casa oppure una lista riservata di opportunità reali quando disponibili.</p></section>
  <div class="grid"><section class="card"><h2>Cosa ricevi</h2><p><b>Se stai iniziando:</b> guida pratica con 10 errori da evitare.</p><p><b>Se è prima casa o serve mutuo:</b> checklist di controlli, costi e documenti.</p><p><b>Se vuoi acquistare a breve:</b> accesso a opportunità coerenti con la tua ricerca, solo quando esistono davvero nel database.</p><p class="muted">Il contenuto informativo non sostituisce verifiche tecniche, notarili, fiscali o bancarie.</p></section>
  <section class="card"><h2>Ricevilo ora</h2><form id="leadForm"><div class="two"><div><label>Nome</label><input name="first_name" required></div><div><label>Cognome</label><input name="last_name"></div></div><label>Email</label><input name="email" type="email" required><label>Telefono</label><input name="phone" type="tel" placeholder="+39..." required><div class="two"><div><label>Zona desiderata</label><input name="desired_area" placeholder="Es. Avigliana" required></div><div><label>Tipologia</label><input name="property_type" placeholder="Es. trilocale"></div></div><div class="two"><div><label>Budget minimo €</label><input name="budget_min" type="number" min="0" step="1000"></div><div><label>Budget massimo €</label><input name="budget_max" type="number" min="0" step="1000"></div></div><label>Quando vuoi acquistare?</label><select name="purchase_timing_days"><option value="0">Sto iniziando a informarmi</option><option value="365">Entro 12 mesi</option><option value="180">Entro 6 mesi</option><option value="90">Entro 3 mesi</option><option value="30">Entro 30 giorni</option></select><div class="checks"><label><input type="checkbox" name="first_home"> È la mia prima casa</label><label><input type="checkbox" name="mortgage_needed"> Ho bisogno di mutuo</label><label><input type="checkbox" name="off_market_interest"> Mi interessano opportunità riservate/off-market quando disponibili</label><label><input type="checkbox" name="consent_privacy" required> Accetto l'<a href="${PRIVACY_URL}" target="_blank" rel="noopener">informativa privacy</a></label><label><input type="checkbox" name="consent_marketing"> Acconsento a ricevere aggiornamenti immobiliari pertinenti alla mia ricerca</label></div><div class="hp"><label>Website<input name="website" autocomplete="off"></label></div><button class="btn" type="submit">RICEVI IL CONTENUTO</button><div id="err" class="error"></div></form><div id="ok" class="success"><h3 id="okTitle"></h3><p id="okText"></p><a id="download" target="_blank" rel="noopener">APRI ORA</a></div></section></div>
  </main><script>const endpoint=${JSON.stringify(ENDPOINT)};const form=document.getElementById('leadForm'),err=document.getElementById('err'),ok=document.getElementById('ok');form.addEventListener('submit',async e=>{e.preventDefault();err.textContent='';const fd=new FormData(form),q=new URLSearchParams(location.search);const body=Object.fromEntries(fd.entries());for(const k of ['first_home','mortgage_needed','off_market_interest','consent_privacy','consent_marketing'])body[k]=fd.has(k);for(const k of ['budget_min','budget_max','purchase_timing_days'])body[k]=Number(body[k]||0);for(const k of ['utm_source','utm_medium','utm_campaign','utm_content'])body[k]=q.get(k)||'';body.source=q.get('source')||'lead-magnet-landing';body.campaign=q.get('campaign')||q.get('utm_campaign')||${JSON.stringify(campaign)};const btn=form.querySelector('button');btn.disabled=true;btn.textContent='INVIO...';try{const r=await fetch(endpoint,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});const d=await r.json();if(!r.ok||!d.ok)throw new Error(d.message||'Invio non riuscito');document.getElementById('okTitle').textContent=d.magnet.title;document.getElementById('okText').textContent='Profilo registrato. Classe lead: '+d.lead_temperature+'. Il contenuto è disponibile ora.';const a=document.getElementById('download');a.href=d.delivery_url;a.style.display=d.delivery_url?'inline-block':'none';ok.style.display='block';form.style.display='none'}catch(x){err.textContent=x.message||'Errore di invio'}finally{btn.disabled=false;btn.textContent='RICEVI IL CONTENUTO'}});</script></body></html>`;
}

function reservedPage(lead:any,items:any[]){
  const cards=items.length?items.map(x=>`<article><h3>${esc(x.raw_title||x.tipologia||'Immobile')}</h3><p><b>${esc(x.comune||'')}</b> · ${esc(x.indirizzo_zona||'')}</p><p>${x.prezzo?`€ ${Number(x.prezzo).toLocaleString('it-IT')}`:'Prezzo da verificare'} · ${x.mq||'-'} m² · ${x.locali||'-'} locali</p>${x.source_url?`<a href="${esc(x.source_url)}" target="_blank" rel="noopener">Apri scheda</a>`:''}</article>`).join(''):`<div class="empty">Al momento non risultano opportunità coerenti con questi criteri. La ricerca resta registrata nel CRM F1.</div>`;
  return `<!doctype html><html lang="it"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Lista riservata | F1 Immobiliare</title><style>body{margin:0;font-family:Arial,sans-serif;background:#eef2f6;color:#1d2939}main{max-width:1000px;margin:auto;padding:28px 16px}.hero{background:#0e2742;color:#fff;padding:32px;border-radius:22px;border-bottom:5px solid #c3a15c}.hero b{color:#c3a15c}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px;margin-top:18px}article,.empty{background:#fff;padding:20px;border-radius:15px;border:1px solid #d7dee7}a{color:#197447;font-weight:800}</style></head><body><main><section class="hero"><b>F1 IMMOBILIARE · LISTA RISERVATA</b><h1>Opportunità coerenti con la tua ricerca</h1><p>Zona: ${esc(lead.desired_area||'da definire')} · Tipologia: ${esc(lead.property_type||'qualsiasi')} · Budget max: ${lead.budget_max?`€ ${Number(lead.budget_max).toLocaleString('it-IT')}`:'da definire'}</p></section><div class="grid">${cards}</div></main></body></html>`;
}

Deno.serve(async(req:Request)=>{
  if(req.method==='OPTIONS')return new Response('ok',{headers:corsHeaders});
  const sb=createClient(SUPABASE_URL,SERVICE_ROLE,{auth:{persistSession:false}});
  if(req.method==='GET'){
    const u=new URL(req.url); const view=u.searchParams.get('view');
    if(view==='reserved'){
      const id=clean(u.searchParams.get('lead'),80),token=clean(u.searchParams.get('token'),80); if(!id||!token)return json(400,{ok:false,error:'missing_access'});
      const {data:lead}=await sb.from('f1_buyer_leads').select('id,desired_area,property_type,budget_min,budget_max,access_token,magnet_code').eq('id',id).eq('access_token',token).maybeSingle(); if(!lead)return json(404,{ok:false,error:'not_found'}); if(lead.magnet_code!=='lista-riservata')return json(403,{ok:false,error:'not_list_magnet'});
      let q=sb.from('f1_market_opportunities').select('id,comune,indirizzo_zona,prezzo,mq,tipologia,locali,camere,giardino,box,ascensore,source_url,raw_title,last_seen_at').or('stato_annuncio.is.null,stato_annuncio.neq.Chiuso').order('last_seen_at',{ascending:false}).limit(20);
      if(lead.desired_area)q=q.ilike('comune',`%${lead.desired_area}%`); if(Number(lead.budget_max)>0)q=q.lte('prezzo',Number(lead.budget_max)); if(lead.property_type)q=q.ilike('tipologia',`%${lead.property_type}%`);
      const {data:items,error}=await q; if(error)return json(500,{ok:false,error:'query_failed'}); await sb.from('f1_buyer_lead_events').insert({lead_id:lead.id,event_type:'reserved_list_view',details:{count:items?.length||0}}); return html(reservedPage(lead,items||[]));
    }
    return html(landingPage(u));
  }
  if(req.method!=='POST')return json(405,{ok:false,error:'method_not_allowed'});
  let i:any; try{i=await req.json()}catch{return json(400,{ok:false,error:'invalid_json'})} if(clean(i.website,200))return json(200,{ok:true});
  const first=clean(i.first_name,100),last=clean(i.last_name,100),mail=clean(i.email,180).toLowerCase(),tel=phone(i.phone); if(!first||!emailOk(mail)||tel.length<8||!Boolean(i.consent_privacy))return json(422,{ok:false,error:'required_fields',message:'Nome, email valida, telefono e consenso privacy sono obbligatori.'});
  const area=clean(i.desired_area,120),ptype=clean(i.property_type,100),bmin=Math.max(0,Number(i.budget_min||0)),bmax=Math.max(0,Number(i.budget_max||0)),timing=Math.max(0,Math.min(3650,Number(i.purchase_timing_days||0)));
  const s=scoreLead({...i,email:mail,phone:tel,desired_area:area,property_type:ptype,budget_max:bmax,purchase_timing_days:timing}); const magnet=await chooseMagnet(sb,{...i,desired_area:area,purchase_timing_days:timing}); const follow=new Date(Date.now()+(s.temperature==='CALDO'?1:s.temperature==='TIEPIDO'?3:7)*86400000).toISOString();
  const payload={first_name:first,last_name:last,email:mail,phone:tel,desired_area:area,property_type:ptype,budget_min:bmin,budget_max:bmax,purchase_timing_days:timing,mortgage_needed:Boolean(i.mortgage_needed),off_market_interest:Boolean(i.off_market_interest),source:clean(i.source||'landing',100),campaign:clean(i.campaign,150),utm_source:clean(i.utm_source,100),utm_medium:clean(i.utm_medium,100),utm_campaign:clean(i.utm_campaign,150),utm_content:clean(i.utm_content,150),consent_privacy:true,consent_marketing:Boolean(i.consent_marketing),magnet_code:magnet.code,lead_score:s.score,lead_temperature:s.temperature,next_followup_at:follow,raw_payload:i,updated_at:new Date().toISOString()};
  const {data:ex}=await sb.from('f1_buyer_leads').select('id,access_token').eq('email',mail).eq('phone',tel).maybeSingle(); let lead:any;
  if(ex){const {data,error}=await sb.from('f1_buyer_leads').update(payload).eq('id',ex.id).select('id,access_token').single();if(error)return json(500,{ok:false,error:'lead_update_failed'});lead=data}else{const {data,error}=await sb.from('f1_buyer_leads').insert(payload).select('id,access_token').single();if(error)return json(500,{ok:false,error:'lead_insert_failed'});lead=data}
  const reqPayload={target_comune:area,nome:`${first} ${last}`.trim(),telefono:tel,email:mail,budget_min:bmin,budget_max:bmax,tipologia:ptype,tempistica:timing?`Entro ${timing} giorni`:'Da definire',note:`Lead magnet ${magnet.code} | score ${s.score} | ${s.temperature}${Boolean(i.mortgage_needed)?' | mutuo':''}${Boolean(i.off_market_interest)?' | off-market':''}`,fonte:clean(i.source||'Lead Magnet',100),stato:s.temperature==='CALDO'?'Da contattare subito':'Nuova',consenso_privacy:true};
  const {data:reqEx}=await sb.from('f1_house_requests').select('id').eq('email',mail).eq('telefono',tel).maybeSingle(); if(reqEx)await sb.from('f1_house_requests').update(reqPayload).eq('id',reqEx.id);else await sb.from('f1_house_requests').insert(reqPayload);
  const deliveryUrl=magnet.code==='lista-riservata'?`${ENDPOINT}?view=reserved&lead=${encodeURIComponent(lead.id)}&token=${encodeURIComponent(lead.access_token)}`:(magnet.asset_url||''); const es=await sendEmail(mail,first,magnet.title,deliveryUrl),ws=await sendWhatsApp(tel,first,magnet.title,deliveryUrl);
  await sb.from('f1_buyer_leads').update({delivery_email_status:es,delivery_whatsapp_status:ws}).eq('id',lead.id); await sb.from('f1_buyer_lead_events').insert([{lead_id:lead.id,event_type:'lead_captured',details:{magnet:magnet.code,score:s.score,temperature:s.temperature}},{lead_id:lead.id,event_type:'delivery',event_status:es==='sent'||ws==='sent'?'sent':'pending',details:{email:es,whatsapp:ws,delivery_url:deliveryUrl}}]);
  return json(200,{ok:true,lead_id:lead.id,magnet:{code:magnet.code,title:magnet.title},lead_temperature:s.temperature,lead_score:s.score,delivery_url:deliveryUrl,delivery:{email:es,whatsapp:ws},next_followup_at:follow});
});
