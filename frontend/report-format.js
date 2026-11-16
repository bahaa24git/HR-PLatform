// Render only escaped text and table elements; model HTML is never executed.
const escapeText=value=>String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const e=escapeText;
const palette=['#3864bd','#16a6a1','#9276c4','#dca348','#d66c7e','#507c96'];
const names={employee_performance:'Employee performance',workforce:'Workforce & HR analytics',team_leader:'Team leader report',department:'Department performance',projects:'Project & operations',executive:'Executive analysis'};
const number=(value,column={})=>value===null||value===undefined?'—':typeof value==='number'?new Intl.NumberFormat('en',{maximumFractionDigits:2}).format(value)+(column.type==='percentage'?'%':column.unit?' '+column.unit:''):String(value);
function chartSVG(block){
 if(block.labels.length>12)return Array.from({length:Math.ceil(block.labels.length/12)},(_,i)=>chartSVG({...block,_total:block.series[0].values.reduce((n,v)=>n+(v||0),0),_offset:block.series[0].values.slice(0,i*12).reduce((n,v)=>n+(v||0),0),labels:block.labels.slice(i*12,(i+1)*12),series:block.series.map(s=>({...s,values:s.values.slice(i*12,(i+1)*12)}))})).join('');
 const values=block.series.flatMap(s=>s.values).filter(v=>v!==null);
 if(!block.labels.length||!values.length||(block.chart_type==='donut'&&values.reduce((a,b)=>a+b,0)<=0))return '<p class="report-empty">'+(block.language==='ar'?'بيانات غير كافية للرسم البياني.':'Insufficient data for this chart.')+'</p>';
 const width=720,height=310,left=65,bottom=235,plot=620,high=170;
 let drawing='';
 const label=(x,y,text,anchor='start',color='#61728b')=>`<text x="${x}" y="${y}" text-anchor="${anchor}" fill="${color}" font-size="11">${e(text)}</text>`;
 if(block.chart_type==='donut'){
  const total=block._total||values.reduce((a,b)=>a+b,0);let offset=(block._offset||0)/total*534.071;
  drawing+=`<circle cx="155" cy="140" r="85" fill="none" stroke="#e7edf6" stroke-width="36"/>`;
  block.labels.forEach((name,i)=>{const value=block.series[0].values[i]||0,len=value/total*534.071;drawing+=`<circle cx="155" cy="140" r="85" fill="none" stroke="${palette[i%6]}" stroke-width="36" stroke-dasharray="${len} ${534.071-len}" stroke-dashoffset="${-offset}" transform="rotate(-90 155 140)"><title>${e(name)}: ${e(number(value,{unit:block.unit}))}</title></circle>`;offset+=len;});
  drawing+=label(155,145,block.series[0].name,'middle');
 }else{
  const stacked=block.chart_type==='stacked_bar';
  const positive=block.labels.map((_,i)=>block.series.reduce((n,s)=>n+Math.max(0,s.values[i]||0),0));
  const negative=block.labels.map((_,i)=>block.series.reduce((n,s)=>n+Math.min(0,s.values[i]||0),0));
  const max=Math.max(0,...(stacked?positive:values)),min=Math.min(0,...(stacked?negative:values)),span=max-min||1;
  const y=v=>bottom-(v-min)/span*high,step=plot/block.labels.length;
  for(let i=0;i<5;i++){const v=min+span*i/4;drawing+=`<line x1="${left}" x2="${left+plot}" y1="${y(v)}" y2="${y(v)}" stroke="#dbe3ef"/>`+label(left-8,y(v)+4,number(v),'end');}
  block.series.forEach((series,j)=>{let path='';series.values.forEach((value,i)=>{if(value===null){path+=' ';return;}const x=left+(i+.5)*step;
   if(block.chart_type==='line'){const previous=i&&series.values[i-1]!==null;path+=`${previous?'L':'M'}${x},${y(value)} `;drawing+=`<circle cx="${x}" cy="${y(value)}" r="3" fill="${palette[j%6]}"><title>${e(block.labels[i])}: ${e(number(value,{unit:block.unit}))}</title></circle>`;}
   else{const base=stacked?block.series.slice(0,j).reduce((n,s)=>n+((s.values[i]||0)*value>=0?(s.values[i]||0):0),0):0,w=step*.7/(stacked?1:block.series.length),bx=x-step*.35+(stacked?0:j*w);drawing+=`<rect x="${bx}" y="${Math.min(y(base),y(base+value))}" width="${w}" height="${Math.max(.5,Math.abs(y(base+value)-y(base)))}" rx="2" fill="${palette[j%6]}"><title>${e(series.name)} · ${e(block.labels[i])}: ${e(number(value,{unit:block.unit}))}</title></rect>`;}
  });if(path)drawing+=`<path d="${path}" fill="none" stroke="${palette[j%6]}" stroke-width="2"/>`;});
  block.labels.forEach((name,i)=>drawing+=label(left+(i+.5)*step,bottom+19,name.length>14?name.slice(0,12)+'…':name,'middle'));
  drawing+=label(left,30,block.y_label+(block.unit?' ('+block.unit+')':''))+label(left+plot/2,290,block.x_label,'middle');
 }
 return `<svg class="report-chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="${e(block.title)}"><title>${e(block.title)}</title>${drawing}</svg><div class="report-chart-legend">${(block.chart_type==='donut'?block.labels:block.series.map(s=>s.name)).map((name,i)=>`<span><i style="background:${palette[i%6]}"></i>${e(name)}</span>`).join('')}</div>`;
}
function nativeTable(columns,rows,title,empty){return `<div class="ai-table-scroll" tabindex="0" role="region" aria-label="${e(title||'Report table')}"><table class="ai-report-table"><caption>${e(title)}</caption><thead><tr>${columns.map(c=>`<th scope="col" dir="auto" class="${c.type==='string'||c.type==='date'?'':'report-number'}">${e(c.label)}${c.unit&&c.type==='currency'?` <small>(${e(c.unit)})</small>`:''}</th>`).join('')}</tr></thead><tbody>${rows.length?rows.map(row=>`<tr>${columns.map((c,i)=>`<td dir="auto" class="${c.type==='string'||c.type==='date'?'':'report-number'}">${e(number(row[i],c))}</td>`).join('')}</tr>`).join(''):`<tr><td colspan="${columns.length}">${e(empty)}</td></tr>`}</tbody></table></div>`;}
export function renderDocument(report,{charts=true,template=report.report_type,direction=report.direction}={}){
 const ar=direction==='rtl',sources=values=>values?.length?`<p class="report-sources">${ar?'المصادر':'Sources'}: ${values.map(e).join(' · ')}</p>`:'';
 return `<article class="report-document report-template-${e(template)}" dir="${ar?'rtl':'ltr'}" lang="${ar?'ar':'en'}"><header class="report-document-header"><span class="report-eyebrow">NORTHSTAR / ${e(report.company||'')}</span><p class="report-template-label">${e(names[template]||template)}</p><h2>${e(report.title)}</h2>${report.subtitle?`<p>${e(report.subtitle)}</p>`:''}<div class="report-metadata"><span>${e(report.report_id||'')}</span><span>${e(report.period||'')}</span><time>${e(report.generated_at||'')}</time></div></header>${report.methodology?`<aside class="report-methodology"><strong>${ar?'المنهجية':'Methodology'}</strong><p>${e(report.methodology)}</p></aside>`:''}${report.sections.map(block=>{
  if(block.type==='chart'&&!charts)return '';
  let body='';
  if(block.type==='narrative')body=`<p dir="auto">${e(block.text)}</p>`;
  else if(block.type==='list')body=`<ul>${block.items.map(v=>`<li dir="auto">${e(v)}</li>`).join('')}</ul>`;
  else if(block.type==='table')body=nativeTable(block.columns,block.rows,block.title,ar?'لا توجد بيانات':'No data available');
  else if(block.type==='kpi_grid')body=`<div class="report-kpis">${block.items.map(item=>`<div><span>${e(item.label)}</span><strong dir="auto">${e(number(item.value,item))}</strong></div>`).join('')}</div>`;
  else if(block.type==='chart')body=chartSVG({...block,language:ar?'ar':'en'})+`<details class="report-chart-data"><summary>${ar?'بيانات الرسم البياني':'Chart data'}</summary>${nativeTable([{label:block.x_label||'Category',type:'string'},...block.series.map(s=>({label:s.name,type:'number',unit:block.unit}))],block.labels.map((name,i)=>[name,...block.series.map(s=>s.values[i])]),block.title,ar?'لا توجد بيانات':'No data available')}</details>`;
  return `<section class="report-component">${block.title&&block.type!=='table'?`<h3>${e(block.title)}</h3>`:''}${body}${sources(block.sources)}</section>`;
 }).join('')}${report.limitations?.length?`<aside class="report-limitations"><h3>${ar?'القيود':'Limitations'}</h3><ul>${report.limitations.map(v=>`<li>${e(v)}</li>`).join('')}</ul></aside>`:''}<footer class="report-document-footer">${report.origin==='system'?(ar?'\u062a\u0642\u0631\u064a\u0631 \u0627\u0644\u0646\u0638\u0627\u0645 / \u0627\u0644\u0628\u064a\u0627\u0646\u0627\u062a \u0627\u0644\u0645\u0633\u062c\u0644\u0629':'System report / Based on recorded data'):(ar?'\u062a\u062d\u0644\u064a\u0644 \u0628\u0627\u0644\u0630\u0643\u0627\u0621 \u0627\u0644\u0627\u0635\u0637\u0646\u0627\u0639\u064a / \u064a\u062a\u0637\u0644\u0628 \u0645\u0631\u0627\u062c\u0639\u0629 \u0628\u0634\u0631\u064a\u0629':'AI-generated analysis / Human review required')}</footer></article>`;
}
export function reportBlocks(value){
 const lines=[];
 for(const line of String(value).split(/\r?\n/)){
  const match=/\|(?:\s*:?-{3,}:?\s*\|)+/.exec(line);
  if(match&&line.slice(0,match.index).trim()){
   const first=line.indexOf('|');if(line.slice(0,first).trim())lines.push(line.slice(0,first).trim());
   lines.push(line.slice(first,match.index).trim(),match[0],...line.slice(match.index+match[0].length).trim().split(/\|\s+\|/));
  }else lines.push(line);
 }
 const cells=line=>line.trim().replace(/^\||\|$/g,'').split('|').map(v=>v.trim());
 const blocks=[];let i=0;
 while(i<lines.length){
  if(i+1<lines.length&&lines[i].includes('|')&&/^\s*\|?(?:\s*:?-{3,}:?\s*\|)+\s*:?-{3,}:?\s*\|?\s*$/.test(lines[i+1])){
   const headers=cells(lines[i]);i+=2;const rows=[];
   while(i<lines.length&&lines[i].includes('|')){const row=cells(lines[i]);if(row.length!==headers.length)break;rows.push(row);i++;}
   blocks.push({type:'table',headers,rows});
  }else{if(lines[i].trim())blocks.push({type:'text',text:lines[i].trim()});i++;}
 }
 return blocks;
}
export function renderReport(value,document=null){if(document)return renderDocument(document);return reportBlocks(value).map(block=>block.type==='text'?`<p dir="auto">${escapeText(block.text)}</p>`:`<div class="ai-table-scroll" tabindex="0"><table class="ai-report-table"><thead><tr>${block.headers.map(v=>`<th scope="col" dir="auto">${escapeText(v)}</th>`).join('')}</tr></thead><tbody>${block.rows.map(row=>`<tr>${row.map(v=>`<td dir="auto">${escapeText(v)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`).join('');}
