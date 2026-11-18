const {test,expect}=require('@playwright/test');
const accounts=[['owner','owner@demo.local'],['admin','system.admin@demo.local'],['hr','hr@demo.local'],['accountant','accounting@demo.local'],['sales_manager','sales.manager@demo.local'],['sales_leader','leader.atlas@demo.local'],['sales','sales.atlas.1@demo.local'],['project_manager','project.manager@demo.local'],['manager','manager@demo.local'],['leader','leader@demo.local'],['designer','nora@demo.local'],['employee','ordinary.employee@demo.local'],['executive','executive@demo.local']];
async function login(page,email){await page.goto('/');await page.locator('#email').fill(email);await page.locator('#password').fill('Demo2026!');await page.locator('#login-form button[type=submit]').click();await expect(page.locator('.shell')).toBeVisible();await expect(page.locator('#content .metrics, #content .panel')).not.toHaveCount(0);}
for(const [role,email] of accounts)test(`audit ${role}: login, dashboard, every visible page, API permissions and logout`,async({page})=>{
 const errors=[];page.on('pageerror',error=>errors.push(error.message));
 await login(page,email);
 const boot=await (await page.request.get('/api/bootstrap')).json();
 const pages=await page.locator('.nav-scroll [data-page]').evaluateAll(nodes=>nodes.map(n=>n.dataset.page));
 for(const key of pages){await page.locator(`.nav-scroll [data-page="${key}"]`).first().click();await expect(page.locator('#content .skeleton')).toHaveCount(0);await expect(page.locator('#content .error-box')).toHaveCount(0);}
 if(['sales','sales_leader','sales_manager','accountant','admin'].includes(role)){
  for(const entity of ['employees','contracts','resignations','payroll']){
   expect(boot.allowed_pages).not.toContain(entity);
   expect((await page.request.get('/api/resources/'+entity)).status()).toBe(403);
  }
 }
 if(!['owner','hr'].includes(role)){expect(boot.allowed_pages).not.toContain('terminations');expect((await page.request.get('/api/terminations')).status()).toBe(403);}
 if(role==='designer'){expect(boot.allowed_pages).not.toContain('campaigns');expect((await page.request.get('/api/business/campaigns')).status()).toBe(403);}
 if(role==='accountant'){expect((await page.request.get('/api/business/payments')).status()).toBe(200);expect((await page.request.get('/api/business/client_contracts')).status()).toBe(200);}
 expect(errors).toEqual([]);await page.locator('.sidebar [data-action=logout]').click();await expect(page.locator('#login-form')).toBeVisible();expect((await page.request.get('/api/bootstrap')).status()).toBe(401);
});

test('accountant creates a contract invoice, allocates a receipt and exports the collection record',async({page})=>{
 await login(page,'owner@demo.local');
 const boot=await (await page.request.get('/api/bootstrap')).json();
 const account=await page.request.post('/api/business/accounts',{data:{name:'Audit Invoice Client',owner_id:boot.user.employee_id,status:'Active client'}});expect(account.ok()).toBeTruthy();const accountId=(await account.json()).id;
 const contract=await page.request.post('/api/business/client_contracts',{data:{name:'Audit approved services',account_id:accountId,owner_id:boot.user.employee_id,value_cents:1000000,currency:'EGP',start:'2026-01-01',end:'2027-12-31',payment_terms:'Half on issue, half on acceptance',services:['Design'],status:'Approved',confirmed:true}});expect(contract.ok()).toBeTruthy();const contractId=(await contract.json()).id;
 await page.locator('.sidebar [data-action=logout]').click();await login(page,'accounting@demo.local');
 const invoice=await page.request.post('/api/business/invoices',{data:{contract_id:contractId,number:'QA-INV-001',issued:'2026-01-02',due:'2026-02-01',amount_cents:100000,status:'Issued',notes:'Isolated audit invoice'}});expect(invoice.ok()).toBeTruthy();const invoiceId=(await invoice.json()).id;
 const receipt=await page.request.post('/api/business/payments',{data:{contract_id:contractId,invoice_id:invoiceId,amount_cents:25000,day:'2026-01-03',reference:'QA-RECEIPT-001'}});expect(receipt.ok()).toBeTruthy();
 const records=await (await page.request.get('/api/business/invoices')).json();expect(records.find(i=>i.id===invoiceId).outstanding_cents).toBe(75000);
 const report=await page.request.get('/api/exports/invoices/'+invoiceId);expect(report.ok()).toBeTruthy();expect((await report.body()).subarray(0,4).toString()).toBe('%PDF');
 await page.reload();await page.locator('.nav-scroll [data-page=invoices]').click();await expect(page.locator('#content')).toContainText('QA-INV-001');
});

test('main dashboard uses a filterable real performance trend and pending evaluations',async({page})=>{
 await login(page,'hr@demo.local');
 await expect(page.locator('#content')).not.toContainText('Performance progress');
 await expect(page.locator('#content')).toContainText('Pending evaluations');
 await expect(page.locator('.performance-trend')).toBeVisible();
 await page.locator('.performance-filters [name=start]').fill('2099-01-01');
 await page.locator('.performance-filters button').click();
 await expect(page.locator('.performance-trend')).toContainText('No approved, dated KPI history yet');
});

test('HR configures holidays and imports an audited timesheet through the UI',async({page})=>{
 await login(page,'hr@demo.local');await page.locator('.nav-scroll [data-page=holidays]').click();
 await page.getByRole('button',{name:'Add new',exact:true}).click();await page.locator('#field-name').fill('Audit holiday');await page.locator('#field-day').fill('2030-01-01');await page.locator('#field-paid').check();await page.locator('button[form=record-form]').click();await expect(page.locator('.modal')).toHaveCount(0);await expect(page.locator('#content')).toContainText('Audit holiday');
 await page.locator('.nav-scroll [data-page=leave_requests]').click();await page.getByRole('button',{name:'Import timesheet CSV',exact:true}).click();
 const day=new Intl.DateTimeFormat('en-CA',{timeZone:'Africa/Cairo',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
 await page.locator('#attendance-csv').setInputFiles({name:'reviewed.csv',mimeType:'text/csv',buffer:Buffer.from(`employee_id,day,check_in,check_out\n6,${day},${day}T09:00,${day}T18:00\n`)});
 await page.locator('#field-reason').fill('HR verified this isolated test timesheet.');await page.locator('button[form=record-form]').click();await expect(page.locator('.modal')).toHaveCount(0);
 const report=await (await page.request.get(`/api/attendance-report?employee_id=6&start=${day}&end=${day}`)).json();expect(report.records[0].classification).toBe('Normal');
});

test('HR resolves a pending absence before final payroll approval',async({page})=>{
 await login(page,'hr@demo.local');
 const day=new Intl.DateTimeFormat('en-CA',{timeZone:'Africa/Cairo',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());const month=day.slice(0,7);
 const imported=await page.request.post('/api/attendance-import',{data:{csv:`employee_id,day,check_in,check_out\n6,${day},${day}T11:30,${day}T18:00\n`,reason:'Verified late check-in in isolated payroll scenario'}});expect(imported.ok()).toBeTruthy();
 const leaves=await (await page.request.get('/api/resources/leave_requests')).json();
 for(const leave of leaves.filter(l=>l.employee_id===6&&l.status==='Pending'))expect((await page.request.post(`/api/leave/${leave.id}/decision`,{data:{decision:'Rejected',reason:'Resolved before isolated payroll finalization'}})).ok()).toBeTruthy();
 expect((await page.request.post('/api/payroll',{data:{action:'process',month}})).ok()).toBeTruthy();
 const payslips=await (await page.request.get('/api/resources/payroll')).json();const payslip=payslips.find(p=>p.employee_id===6&&p.month===month);
 const blocked=await page.request.post('/api/payroll',{data:{action:'approve',id:payslip.id}});expect(blocked.status()).toBe(409);expect((await blocked.json()).error).toContain('Resolve pending');
 const reviews=await (await page.request.get('/api/attendance-reviews')).json();const absence=reviews.find(r=>r.employee_id===6&&r.day===day);
 await page.locator('.nav-scroll [data-page=leave_requests]').click();await page.getByRole('button',{name:'Review absences',exact:true}).click();await page.locator(`[data-action=h-review-absence][data-id="${absence.id}"]`).click();await page.locator('#field-decision').selectOption('Excused');await page.locator('#field-reason').fill('HR verified documented exceptional circumstances.');await page.locator('button[form=record-form]').click();await expect(page.locator('.modal')).toHaveCount(0);
 expect((await page.request.post('/api/payroll',{data:{action:'approve',id:payslip.id}})).ok()).toBeTruthy();
 const final=await (await page.request.get('/api/resources/payroll')).json();expect(final.find(p=>p.id===payslip.id).status).toBe('Approved');
});

test('evaluation-period and leave-type creation execute real validators',async({page})=>{
 await login(page,'hr@demo.local');
 const period=await page.request.post('/api/periods',{data:{name:'Isolated 2031 review',start:'2031-01-01',end:'2031-01-31'}});expect(period.ok()).toBeTruthy();
 const invalid=await page.request.post('/api/periods',{data:{name:'Invalid',start:'2031-02-01',end:'2031-01-01'}});expect(invalid.status()).toBe(400);
 const type=await page.request.post('/api/leave-types',{data:{name:'QA balance-bearing leave',deduct_balance:true,payroll_factor:0,unit:'days'}});expect(type.ok()).toBeTruthy();
});

test('HR-defined career paths appear as advisory skill gaps for the employee',async({page})=>{
 await login(page,'hr@demo.local');const boot=await (await page.request.get('/api/bootstrap')).json();
 const from=boot.lookups.positions.find(p=>p.title==='Graphic Designer').id;const to=boot.lookups.positions.find(p=>p.title==='Team Leader').id;
 const created=await page.request.post('/api/resources/career_paths',{data:{from_position_id:from,to_position_id:to,required_skills:['Figma','Coaching'],minimum_proficiency:80,minimum_months:12,notes:'Discuss a mentored leadership assignment with the supervisor.'}});expect(created.ok()).toBeTruthy();
 await page.locator('.sidebar [data-action=logout]').click();await login(page,'nora@demo.local');await page.locator('.nav-scroll [data-page=learning_plans]').click();await page.getByRole('button',{name:'Career readiness',exact:true}).click();await expect(page.locator('.modal')).toContainText('Team Leader');await expect(page.locator('.modal')).toContainText('Coaching');await expect(page.locator('.modal')).toContainText('authorized human review');
});
