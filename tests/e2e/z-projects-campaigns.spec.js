const {test,expect}=require('@playwright/test');
const fill=async(page,key,value)=>{const el=page.locator('#field-'+key);if(await el.evaluate(e=>e.tagName==='SELECT'))await el.selectOption(String(value));else await el.fill(String(value));};
const submit=async page=>{await page.locator('button[form="record-form"]').click();await expect(page.locator('.modal')).toHaveCount(0);};
const nav=async(page,entity)=>{await page.locator('.sidebar [data-page="'+entity+'"]').first().click();await expect(page.locator('#content .skeleton')).toHaveCount(0);await expect(page.locator('.error-box')).toHaveCount(0);};
const close=async page=>page.locator('.modal-actions [data-action="close"]').click();
const row=(page,name)=>page.locator('#record-table tbody tr').filter({hasText:name});

test('projects and campaigns support creation, every status, related actions, files and list tools',async({page})=>{
 test.setTimeout(120000);
 const errors=[];page.on('pageerror',error=>errors.push(error.message));
 await page.goto('/');await page.locator('#login-form button[type="submit"]').waitFor();
 await page.locator('#email').fill('owner@demo.local');await page.locator('#login-form button[type="submit"]').click();
 await expect(page.locator('[data-action="profile"]')).toBeVisible();
 const boot=await (await page.request.get('/api/bootstrap')).json();
 const post=async(entity,data)=>{const response=await page.request.post('/api/business/'+entity,{data});expect(response.ok(),await response.text()).toBeTruthy();return (await response.json()).id;};
 const account=await post('accounts',{name:'QA project client',owner_id:boot.user.employee_id,status:'Active client'});
 const contract=await post('client_contracts',{name:'QA approved delivery',account_id:account,owner_id:boot.user.employee_id,value_cents:3000000,currency:'EGP',start:'2026-11-01',end:'2027-02-28',payment_terms:'Fictional test agreement',services:['Content Creation'],status:'Approved',confirmed:true});
 // Refresh the lookups after API fixture creation.
 await page.reload();await expect(page.locator('[data-action="profile"]')).toBeVisible();
 const projects=[];
 for(const [i,name] of ['QA Launch project','QA Content project','QA Video project'].entries()){
  await nav(page,'projects');await page.locator('[data-action="b-new"]').click();
  for(const [key,value] of Object.entries({name,account_id:account,contract_id:contract,manager_id:boot.lookups.employees.find(e=>e.name==='QA Project Manager').id,start:'2026-11-01',deadline:'2027-01-31',budget_cents:500000,estimated_hours:40,status:'Active',priority:'High',notes:'Fictional UI example '+i}))await fill(page,key,value);
  await submit(page);await expect(row(page,name)).toHaveCount(1);
  projects.push((await (await page.request.get('/api/business/projects')).json()).find(p=>p.name===name));
 }
 const project=projects[0];
 for(const status of ['Planning','On hold','Completed','Archived','Active']){
  await row(page,project.name).getByRole('button',{name:'Edit',exact:true}).click();await fill(page,'status',status);await fill(page,'results','Recorded test result');await submit(page);await expect(row(page,project.name)).toContainText(status);
 }
 await row(page,project.name).getByRole('button',{name:'View',exact:true}).click();
 const pdf=await page.locator('.modal a[href^="/api/exports/projects/"]').getAttribute('href');
 const response=await page.request.get(pdf);expect(response.ok()).toBeTruthy();expect((await response.body()).subarray(0,4).toString()).toBe('%PDF');
 await page.getByRole('button',{name:'Assign member',exact:true}).click();await fill(page,'employee_id',boot.lookups.employees.find(e=>e.name==='Nora Khalil').id);await fill(page,'responsibility','QA design');await submit(page);
 for(const [action,data] of [
  ['Add milestone',{title:'QA kickoff',due:'2026-12-01',status:'In progress'}],
  ['Add risk',{title:'QA schedule risk',severity:'High',mitigation:'Confirm dependencies early',owner_id:boot.user.employee_id,status:'Open'}]
 ]){
  await row(page,project.name).getByRole('button',{name:'View',exact:true}).click();await page.getByRole('button',{name:action,exact:true}).click();
  await expect(page.locator('#field-project_id')).toHaveValue(String(project.id));
  for(const [key,value] of Object.entries(data))await fill(page,key,value);await submit(page);
 }
 for(const entity of ['projects','campaigns']){
  if(entity==='campaigns'){
   await nav(page,entity);
   for(const [i,p] of projects.entries()){
    await page.locator('[data-action="b-new"]').click();
    for(const [key,value] of Object.entries({project_id:p.id,name:'QA Campaign '+i,channel:['Social','Email','Search'][i],objective:'Qualified fictional inquiries',start:'2026-11-01',end:'2027-01-31',advertising_budget_cents:200000,advertising_spend_cents:50000,impressions:10000,clicks:500,conversions:20,attributed_revenue_cents:100000,status:'Planning'}))await fill(page,key,value);
    await submit(page);
   }
   for(const status of ['Active','Paused','Completed','Planning']){
    await row(page,'QA Campaign 0').getByRole('button',{name:'Edit',exact:true}).click();await fill(page,'status',status);await submit(page);await expect(row(page,'QA Campaign 0')).toContainText(status);
   }
  }else await nav(page,entity);
  const name=entity==='projects'?project.name:'QA Campaign 0';
  await row(page,name).getByRole('button',{name:'View',exact:true}).click();await expect(page.locator('.timeline')).toContainText('Created');await expect(page.locator('.timeline')).toContainText('Updated');
  if(entity==='projects'){
   await expect(page.getByRole('button',{name:'Add task',exact:true})).toHaveCount(0);
   for(const title of ['QA kickoff','QA schedule risk','Nora Khalil'])await expect(page.locator('.modal-body')).toContainText(title);
  }
  await page.getByRole('button',{name:'Upload file',exact:true}).click();
  await page.locator('#attachment-file').setInputFiles({name:'qa-brief.txt',mimeType:'text/plain',buffer:Buffer.from('Fictional project brief')});await submit(page);
  await row(page,name).getByRole('button',{name:'View',exact:true}).click();const href=await page.locator('.attachment-link').getAttribute('href');expect(await (await page.request.get(href)).text()).toBe('Fictional project brief');await expect(page.locator('.timeline')).toContainText('Attachment uploaded');await close(page);
  const csv=await page.request.get('/api/business/'+entity+'/export');expect(csv.ok()).toBeTruthy();expect(await csv.text()).toContain(name);
  await page.locator('#record-search').fill(name);await expect(page.locator('#record-table tbody tr')).toHaveCount(1);
  await page.locator('[data-action="b-sort"]').first().click();await expect(row(page,name)).toHaveCount(1);
  await page.locator('[data-action="b-save-view"]').click();await fill(page,'name','QA '+entity+' view');await submit(page);
  await page.locator('#record-search').fill('no matching record');await expect(page.locator('#record-table tbody tr')).toHaveCount(0);
  await page.locator('[data-action="b-views"]').click();await page.getByRole('button',{name:'QA '+entity+' view',exact:true}).click();await expect(row(page,name)).toHaveCount(1);
  await page.locator('[data-action="b-columns"]').click();await page.locator('#field-notes').count().then(async n=>{if(n)await page.locator('#field-notes').check();});await submit(page);
  await page.locator('[data-action="b-filters"]').click();await fill(page,'start','2020-01-01');await fill(page,'end','2030-12-31');await submit(page);await expect(row(page,name)).toHaveCount(1);
  await page.locator('#status-filter').selectOption(entity==='projects'?'Completed':'Paused');await expect(page.locator('#record-table tbody tr')).toHaveCount(0);await page.locator('#status-filter').selectOption('');await expect(row(page,name)).toHaveCount(1);
 }
 // An assigned project manager can create tasks from project details.
 await page.locator('.sidebar [data-action="logout"]').click();await page.locator('#email').fill('project.manager@demo.local');await page.locator('#login-form button[type="submit"]').click();await nav(page,'projects');
 await row(page,project.name).getByRole('button',{name:'View',exact:true}).click();await page.getByRole('button',{name:'Add task',exact:true}).click();await expect(page.locator('#field-project_id')).toHaveValue(String(project.id));
 for(const [key,value] of Object.entries({team_id:2,employee_id:6,title:'QA linked task',due:'2026-12-10',priority:'High',complexity:3,estimated_hours:4}))await fill(page,key,value);await submit(page);
 // Related records remain editable and preserve their project link.
 for(const [entity,title,data] of [
  ['milestones','QA kickoff',{status:'Completed'}],
  ['project_risks','QA schedule risk',{status:'Mitigated'}],
  ['project_members','Nora Khalil',{responsibility:'QA design lead'}]
 ]){
  await nav(page,entity);const relatedRow=row(page,title).filter({hasText:project.name});await relatedRow.getByRole('button',{name:'Edit',exact:true}).click();for(const [key,value] of Object.entries(data))await fill(page,key,value);await submit(page);await expect(relatedRow).toContainText(Object.values(data)[0]);
 }
 // Assigned contributors have read access, while unassigned employees do not.
 await page.locator('.sidebar [data-action="logout"]').click();await page.locator('#email').fill('nora@demo.local');await page.locator('#login-form button[type="submit"]').click();await nav(page,'projects');await expect(row(page,project.name)).toHaveCount(1);await expect(page.locator('[data-action="b-new"]')).toHaveCount(0);await expect(row(page,project.name).getByRole('button',{name:'Edit',exact:true})).toHaveCount(0);
 const denied=await page.request.patch('/api/business/projects/'+project.id,{data:{status:'Archived'}});expect(denied.status()).toBe(403);
 await nav(page,'campaigns');await expect(row(page,'QA Campaign 0')).toHaveCount(1);
 await page.locator('.sidebar [data-action="logout"]').click();await page.locator('#email').fill('sara@demo.local');await page.locator('#login-form button[type="submit"]').click();await nav(page,'projects');await expect(row(page,project.name)).toHaveCount(0);expect((await page.request.get('/api/business/projects/'+project.id)).status()).toBe(404);
 expect(errors).toEqual([]);
});
