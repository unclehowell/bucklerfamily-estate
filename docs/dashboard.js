(function(){
  "use strict";
  var DOCS_URL="https://cedwyn.bucklerfamily.estate/dartboard/docs/";
  var root=new URL("./",document.baseURI);
  var dialog=document.getElementById("docs-dialog");
  var numberFormat=new Intl.NumberFormat("en-GB");
  var palette=["c0","c1","c2","c3","c4","c5","c6","c7"];

  function esc(value){
    return String(value==null?"":value).replace(/[&<>"']/g,function(c){
      return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c];
    });
  }
  function countBy(items,getter){
    var out=Object.create(null);
    items.forEach(function(item){
      var key=String(getter(item)||"unknown");
      out[key]=(out[key]||0)+1;
    });
    return out;
  }
  function fmt(n){return numberFormat.format(Number(n)||0);}
  function getEnglish(value){
    if(value&&typeof value==="object") return value.en||value.cy||value.es||Object.values(value)[0]||"";
    return String(value||"");
  }
  function stamp(value){
    if(!value) return "—";
    var d=new Date(value);
    if(!Number.isFinite(d.getTime())) return String(value);
    return d.toLocaleDateString("en-GB",{day:"2-digit",month:"short",year:"numeric",timeZone:"UTC"}).toUpperCase()
      +" "+d.toISOString().slice(11,16)+"Z";
  }
  function openDocs(){
    if(dialog&&typeof dialog.showModal==="function"){if(!dialog.open)dialog.showModal();}
    else if(dialog)dialog.setAttribute("open","");
  }
  function gauge(label,value,ratio){
    var progress=Number.isFinite(ratio);
    var style=progress?" style=\"--dash-ratio:"+Math.max(0,Math.min(1,ratio))*100+"%\"":"";
    return '<button class="dash-gauge" type="button" data-open-docs="1" aria-label="'+esc(label+" "+value)+'">'+
      '<span class="gauge-dial '+(progress?"":"neutral")+'"'+style+'><span class="gauge-number">'+esc(fmt(value))+'</span></span>'+
      '<span class="gauge-label">'+esc(label)+'</span></button>';
  }
  function renderGauges(data){
    var docs=data.docs,central=data.central,documents=docs.documents||[],collections=docs.collections||[];
    var items=central&&central.items?Object.values(central.items):[];
    var missing=central&&Array.isArray(central.not_in_central)?central.not_in_central.length:0;
    var totalRefs=items.length+missing,coverage=totalRefs?items.length/totalRefs:NaN;
    var languages=Object.create(null),archives=0,pdfs=0;
    documents.forEach(function(d){
      (d.languages||[]).forEach(function(l){languages[l.code||l]=(languages[l.code||l]||0)+1;});
      archives+=(d.archive||[]).length;
      pdfs+=(d.pdf_languages||[]).length;
    });
    var labels=[
      ["DOCUMENTS",documents.length,NaN],
      ["COLLECTIONS",collections.length,NaN],
      ["LANGUAGES",Object.keys(languages).length,NaN],
      ["ARCHIVES",archives,NaN],
      ["LINKED REFS",items.length,coverage],
      ["UNMATCHED",missing,totalRefs?missing/totalRefs:NaN],
      ["CURRENT PDFs",pdfs,NaN]
    ];
    document.getElementById("docs-gauges").innerHTML=labels.map(function(x){return gauge(x[0],x[1],x[2]);}).join("");
  }
  function renderBars(id,title,entries){
    var host=document.getElementById(id);
    if(!entries.length){host.innerHTML="";return;}
    entries=entries.slice().sort(function(a,b){return b.value-a.value||a.label.localeCompare(b.label);});
    var max=Math.max.apply(null,entries.map(function(x){return x.value;}).concat([1]));
    host.innerHTML=entries.map(function(item,i){
      var width=Math.max(0,item.value/max*100);
      return '<button class="dash-bar" type="button" data-open-docs="1" aria-label="'+esc(item.label+" "+item.value)+'">'+
        '<span class="dash-bar-label">'+esc(item.label)+'</span>'+
        '<span class="dash-track"><span class="dash-fill '+palette[i%palette.length]+'" style="width:'+width.toFixed(2)+'%"></span></span>'+
        '<span class="dash-bar-value">'+fmt(item.value)+'</span></button>';
    }).join("");
  }
  function renderScatter(docs,collections){
    var host=document.getElementById("docs-scatter");
    var names=collections.map(function(c){return {id:c.id,label:getEnglish(c.title)};});
    var index=Object.create(null);
    names.forEach(function(c,i){index[c.id]=i;});
    var points=docs.map(function(d,i){
      var time=Date.parse(String(d.updated||d.date||"")+"T00:00:00Z");
      var row=index[d.collection];
      if(!Number.isFinite(time)||row===undefined)return null;
      return {d:d,time:time,row:row,jitter:(i%7)-3};
    }).filter(Boolean);
    if(!points.length){host.innerHTML="";return;}
    var min=Math.min.apply(null,points.map(function(p){return p.time;}));
    var max=Math.max.apply(null,points.map(function(p){return p.time;}));
    if(min===max)max=min+86400000;
    var W=1000,H=Math.max(220,Math.min(470,112+names.length*34));
    var L=174,R=24,T=18,B=38,plotW=W-L-R,plotH=H-T-B,band=plotH/Math.max(1,names.length);
    var parts=['<svg viewBox="0 0 '+W+' '+H+'" role="img" aria-label="Document updates by collection">'];
    names.forEach(function(c,i){
      var y=T+band*(i+.5);
      parts.push('<line class="dash-gridline" x1="'+L+'" y1="'+y.toFixed(1)+'" x2="'+(W-R)+'" y2="'+y.toFixed(1)+'"></line>');
      parts.push('<text class="dash-axis" x="'+(L-12)+'" y="'+(y+3.5).toFixed(1)+'" text-anchor="end">'+esc(c.label.toUpperCase())+'</text>');
    });
    var startYear=new Date(min).getUTCFullYear(),endYear=new Date(max).getUTCFullYear();
    var years=[],yearStep=Math.max(1,Math.ceil((endYear-startYear)/6));
    for(var y=startYear;y<=endYear;y+=yearStep) years.push(y);
    if(years[years.length-1]!==endYear) years.push(endYear);
    years.forEach(function(year){
      var date=Date.UTC(year,0,1),x=L+(date-min)/(max-min)*plotW;
      if(x<L||x>W-R)return;
      parts.push('<line class="dash-gridline" x1="'+x.toFixed(1)+'" y1="'+T+'" x2="'+x.toFixed(1)+'" y2="'+(H-B)+'"></line>');
      parts.push('<text class="dash-tick" x="'+x.toFixed(1)+'" y="'+(H-14)+'" text-anchor="middle">'+year+'</text>');
    });
    points.forEach(function(p,i){
      var x=L+(p.time-min)/(max-min)*plotW;
      var y=T+band*(p.row+.5)+p.jitter;
      var label=String(p.d.id||"")+" · "+String(p.d.updated||p.d.date||"")+" · "+String(p.d.status||"");
      parts.push('<circle class="dash-dot '+palette[p.row%palette.length]+'" cx="'+x.toFixed(1)+'" cy="'+y.toFixed(1)+'" r="3.3" data-open-docs="1" tabindex="0" role="button" aria-label="'+esc(label)+'"></circle>');
    });
    parts.push("</svg>");
    host.innerHTML=parts.join("");
  }
  function render(data){
    var docs=data.docs,central=data.central||{};
    var documents=Array.isArray(docs.documents)?docs.documents:[];
    var collections=Array.isArray(docs.collections)?docs.collections:[];
    var collectionNames=Object.create(null);
    collections.forEach(function(c){collectionNames[c.id]=getEnglish(c.title)||c.id;});
    renderGauges(data);
    var collectionCounts=countBy(documents,function(d){return d.collection;});
    renderBars("docs-by-collection","COLLECTIONS",Object.keys(collectionCounts).map(function(k){return {label:collectionNames[k]||k,value:collectionCounts[k]};}));
    var statuses=countBy(documents,function(d){return d.status;});
    renderBars("docs-by-status","STATUS",Object.keys(statuses).map(function(k){return {label:k,value:statuses[k]};}));
    var languages=Object.create(null);
    documents.forEach(function(d){(d.languages||[]).forEach(function(l){var code=typeof l==="string"?l:l.code;languages[code]=(languages[code]||0)+1;});});
    renderBars("docs-by-language","LANGUAGE BUILDS",Object.keys(languages).map(function(k){return {label:k,value:languages[k]};}));
    var centralItems=central.items&&typeof central.items==="object"?Object.values(central.items):[];
    var kinds=countBy(centralItems,function(x){return x.kind;});
    renderBars("central-by-kind","CATALOGUE KIND",Object.keys(kinds).map(function(k){return {label:k,value:kinds[k]};}));
    var years=Object.create(null);
    documents.forEach(function(d){(d.archive||[]).forEach(function(a){var y=String(a.date||"").slice(0,4);if(y)years[y]=(years[y]||0)+1;});});
    renderBars("archive-by-year","ARCHIVE YEAR",Object.keys(years).map(function(k){return {label:k,value:years[k]};}));
    renderScatter(documents,collections);
    document.getElementById("dash-build").textContent="INDEX "+stamp(docs.generated);
    document.getElementById("dash-central").textContent=central.synced_utc?"CENTRAL "+stamp(central.synced_utc):"CENTRAL —";
    document.getElementById("dash-state").textContent=data.central?"DATA":"INDEX";
  }
  document.addEventListener("click",function(event){
    var target=event.target&&event.target.closest?event.target.closest("[data-open-docs]"):null;
    if(target)openDocs();
  });
  document.addEventListener("keydown",function(event){
    if((event.key==="Enter"||event.key===" ")&&event.target&&event.target.matches&&event.target.matches('circle[data-open-docs]')){
      event.preventDefault();openDocs();
    }
  });
  var close=document.getElementById("docs-close");
  if(close)close.addEventListener("click",function(){if(dialog&&typeof dialog.close==="function")dialog.close();});
  if(dialog)dialog.addEventListener("click",function(event){if(event.target===dialog&&typeof dialog.close==="function")dialog.close();});

  var indexUrl=new URL("docs.json",root),centralUrl=new URL("data/central.json",root);
  Promise.all([
    fetch(indexUrl,{cache:"no-store"}).then(function(r){if(!r.ok)throw new Error("index");return r.json();}),
    fetch(centralUrl,{cache:"no-store"}).then(function(r){if(!r.ok)throw new Error("central");return r.json();}).catch(function(){return null;})
  ]).then(function(values){
    var docs=values[0];
    if(!docs||!Array.isArray(docs.documents)||!Array.isArray(docs.collections))throw new Error("index");
    render({docs:docs,central:values[1]});
  }).catch(function(){
    document.getElementById("dash-state").textContent="OFFLINE";
  });
})();
