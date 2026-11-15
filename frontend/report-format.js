// Render only escaped text and table elements; model HTML is never executed.
const escapeText=value=>String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
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
export function renderReport(value){return reportBlocks(value).map(block=>block.type==='text'?`<p dir="auto">${escapeText(block.text)}</p>`:`<div class="ai-table-scroll" tabindex="0"><table class="ai-report-table"><thead><tr>${block.headers.map(v=>`<th scope="col" dir="auto">${escapeText(v)}</th>`).join('')}</tr></thead><tbody>${block.rows.map(row=>`<tr>${row.map(v=>`<td dir="auto">${escapeText(v)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`).join('');}
