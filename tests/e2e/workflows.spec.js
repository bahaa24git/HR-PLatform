const {test,expect}=require('@playwright/test');
const login=async(page,email='hr@demo.local')=>{await page.goto('/');await page.locator('#email').fill(email);await page.locator('#password').fill('Demo2026!');await page.getByRole('button',{name:'Sign in',exact:true}).click();await expect(page.locator('h1')).toBeVisible();};
const nav=async(page,key)=>{await page.locator('.sidebar [data-action="navigate"][data-page="'+key+'"]').first().click();await expect(page.locator('#content .skeleton')).toHaveCount(0);await expect(page.locator('.error-box')).toHaveCount(0);};
const submit=async page=>{await page.locator('button[form="record-form"]').click();await expect(page.locator('.modal')).toHaveCount(0);};
const fill=async(page,key,value)=>{const el=page.locator('#field-'+key);if(await el.evaluate(e=>e.tagName==='SELECT'))await el.selectOption(String(value));else await el.fill(String(value));};

test('advisor renders saved report tables and escapes model HTML',async({page})=>{
 await login(page,'nora@demo.local');
 await page.route('**/api/ai/history',route=>route.fulfill({json:{conversation_id:'table-test',messages:[{role:'assistant',text:'Findings | Employee | Score | | --- | --- | | Nora | 90 | | <img src=x onerror=alert(1)> | 85 |'}]}}));
 await nav(page,'advisor');
 await expect(page.locator('.ai-report-table th')).toHaveCount(2);
 await expect(page.locator('.ai-report-table tbody tr')).toHaveCount(2);
 await expect(page.locator('.ai-report-table')).toContainText('Nora');
 await expect(page.locator('.ai-report-table img')).toHaveCount(0);
 await expect(page.locator('.ai-report-table')).toContainText('<img src=x onerror=alert(1)>');
});

test('advisor history survives reload and switches securely between accounts',async({page})=>{
 await login(page,'nora@demo.local');await nav(page,'advisor');
 await expect(page.locator('#chat-messages')).toContainText('Nora saved advisor response');
 await expect(page.locator('#chat-messages')).toContainText('Nora saved recommendation');
 await expect(page.locator('#chat-messages')).not.toContainText('HR saved advisor response');
 await page.reload();await nav(page,'advisor');
 await expect(page.locator('#chat-messages')).toContainText('Nora saved advisor response');
 await page.locator('.sidebar [data-action="logout"]').click();
 await login(page,'hr@demo.local');await nav(page,'advisor');
 await expect(page.locator('#chat-messages')).toContainText('HR saved advisor response');
 await expect(page.locator('#chat-messages')).not.toContainText('Nora saved advisor response');
 await page.locator('.sidebar [data-action="logout"]').click();
 await login(page,'nora@demo.local');await nav(page,'advisor');
 await expect(page.locator('#chat-messages')).toContainText('Nora saved advisor response');
 await expect(page.locator('#chat-messages')).not.toContainText('HR saved advisor response');
});
test('HR navigation, structure, forms and owner navigation have no runtime errors',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));await login(page);
 for(const key of ['employees','leave_requests','payroll','kpis','reports','learning_plans','jobs','contracts','checklists','resignations','surveys','recognition','announcements','articles','organization','users','settings','audit','notifications','advisor'])await nav(page,key);
 await nav(page,'employees');await page.getByRole('button',{name:'Add employee',exact:true}).click();await expect(page.locator('#field-seniority_id')).toBeVisible();await page.locator('.modal-actions [data-action="close"]').click();expect(errors).toEqual([]);
});
test('sales lead → deal → won → client contract → approved project',async({page})=>{
 await login(page,'sales.atlas.1@demo.local');await nav(page,'leads');await page.getByRole('button',{name:'Add new',exact:true}).click();
 await fill(page,'name','Browser agency opportunity');await fill(page,'company_name','Browser Fictional Client');await fill(page,'contact_name','Client Coordinator');await fill(page,'email','browser.client@example.test');await page.locator('#field-team_id').selectOption({label:'Sales Atlas'});await fill(page,'expected_cents',1500000);await fill(page,'interested_services','Content Creation, Video Production');await fill(page,'status','New');await fill(page,'priority','High');await fill(page,'qualification','Qualifying');await submit(page);
 const row=page.locator('tbody tr').filter({hasText:'Browser agency opportunity'});await row.getByRole('button',{name:'View',exact:true}).click();await page.getByRole('button',{name:'Convert to deal',exact:true}).click();await fill(page,'expected_close','2026-12-20');await page.locator('#field-confirmed').check();await submit(page);
 await nav(page,'deals');await page.locator('tbody tr').filter({hasText:'Browser agency opportunity'}).getByRole('button',{name:'View',exact:true}).click();await page.getByRole('button',{name:'Move stage',exact:true}).click();await page.locator('#field-stage_id').selectOption({label:'Won'});await page.locator('#field-confirmed').check();await submit(page);
 await page.locator('tbody tr').filter({hasText:'Browser agency opportunity'}).getByRole('button',{name:'View',exact:true}).click();await page.getByRole('button',{name:'Create client contract',exact:true}).click();await fill(page,'end','2027-02-28');await fill(page,'payment_terms','50% on signing; 50% on approved delivery');await page.locator('#field-confirmed').check();await submit(page);
 await page.locator('[data-action="logout"]').click();await login(page,'owner@demo.local');await nav(page,'client_contracts');await page.locator('tbody tr').filter({hasText:'Browser agency opportunity'}).getByRole('button',{name:'Edit',exact:true}).click();await fill(page,'status','Approved');await page.locator('button[form="record-form"]').click();await expect(page.locator('.inline-confirm')).toBeVisible();await page.locator('#confirm-inline').click();await expect(page.locator('.modal')).toHaveCount(0);
 await page.locator('tbody tr').filter({hasText:'Browser agency opportunity'}).getByRole('button',{name:'View',exact:true}).click();await page.getByRole('button',{name:'Create project',exact:true}).click();await fill(page,'name','Browser production launch');await page.locator('#field-manager_id').selectOption({label:'QA Project Manager'});await fill(page,'deadline','2026-12-30');await fill(page,'budget_cents',900000);await fill(page,'estimated_hours',80);await fill(page,'status','Active');await fill(page,'priority','High');await submit(page);
 await nav(page,'projects');await expect(page.locator('tbody')).toContainText('Browser production launch');await nav(page,'insights');await expect(page.locator('.metrics')).toContainText('15,000');
});
test('sales team scopes and manager comparison enforce separate ownership',async({page})=>{
 await login(page,'sales.horizon.1@demo.local');await nav(page,'leads');await expect(page.locator('#record-table')).not.toContainText('Browser agency opportunity');await page.locator('[data-action="logout"]').click();await login(page,'sales.manager@demo.local');await nav(page,'leads');await expect(page.locator('#record-table')).toContainText('Browser agency opportunity');await nav(page,'pipeline');await expect(page.locator('.deal-card')).toContainText('Browser agency opportunity');
});
test('employee permissions, team-first task assignment and KPI change protection',async({page})=>{
 await login(page,'nora@demo.local');await nav(page,'kpis');await expect(page.locator('[data-action="h-edit"]')).toHaveCount(0);await nav(page,'learning_plans');await expect(page.locator('[data-action="h-edit"]')).toHaveCount(0);await page.locator('[data-action="logout"]').click();await login(page,'leader@demo.local');await nav(page,'tasks');await page.getByRole('button',{name:'Add new',exact:true}).click();await expect(page.locator('#field-employee_id')).toBeDisabled();await page.locator('#field-team_id').selectOption({label:'Sales Horizon'});await expect(page.locator('#field-employee_id option')).toHaveCount(2);await expect(page.locator('#field-employee_id')).toContainText('QA Horizon Leader');await expect(page.locator('#field-complexity option')).toHaveCount(6);await page.locator('.modal-actions [data-action="close"]').click();
 await nav(page,'kpis');const row=page.locator('tbody tr').filter({hasText:'Nora Khalil'}).first();await row.getByRole('button',{name:'Edit',exact:true}).click();await fill(page,'target',500);await expect(page.locator('.change-warning')).toContainText('Significant KPI change');await expect(page.locator('#field-justification')).toHaveAttribute('required','');await fill(page,'justification','Fictional documented target scope review.');await page.locator('#field-confirmed').check();await submit(page);
});
test('employee direct URLs and API requests cannot open HR-only records',async({page})=>{
 await login(page,'nora@demo.local');await page.goto('/#jobs');await expect(page.locator('#breadcrumb-page')).toHaveText('Overview');await expect(page.locator('.sidebar [data-page="jobs"]')).toHaveCount(0);
 await expect(page.locator('.sidebar [data-page="campaigns"]')).toHaveCount(0);await page.goto('/#campaigns');await expect(page.locator('#breadcrumb-page')).toHaveText('Overview');
 const people=await page.request.get('/api/resources/employees');expect(people.ok()).toBeTruthy();expect(await people.json()).toHaveLength(1);
 const jobs=await page.request.get('/api/resources/jobs');expect(jobs.status()).toBe(403);
 expect((await page.request.get('/api/business/campaigns')).status()).toBe(403);
});
test('system admin and sales leader navigation matches API permissions',async({page})=>{
 await login(page,'system.admin@demo.local');
 await expect(page.locator('.sidebar [data-page="payroll"]')).toHaveCount(0);
 await expect(page.locator('.sidebar [data-page="employees"]')).toHaveCount(0);
 await expect(page.locator('.sidebar [data-page="projects"]')).toHaveCount(0);
 await page.goto('/#payroll');await expect(page.locator('#breadcrumb-page')).toHaveText('Overview');
 const boot=await page.request.get('/api/bootstrap');expect(boot.ok()).toBeTruthy();const data=await boot.json();expect(data.allowed_pages).toEqual(['dashboard','users']);expect(data.catalog).toEqual({});expect(data.business_catalog).toEqual({});expect(data.lookups.employees).toBeUndefined();
 expect((await page.request.get('/api/resources/employees')).status()).toBe(403);
 expect((await page.request.get('/api/business/projects')).status()).toBe(403);
 expect((await page.request.get('/api/settings')).status()).toBe(403);
 await page.locator('[data-action="logout"]').click();await login(page,'leader.atlas@demo.local');
 await expect(page.locator('.sidebar [data-page="jobs"]')).toHaveCount(0);
 await page.goto('/#jobs');await expect(page.locator('#breadcrumb-page')).toHaveText('Overview');
 expect((await page.request.get('/api/resources/jobs')).status()).toBe(403);
});
test('monthly reports are role-specific and export real PDFs',async({page})=>{
 await login(page,'nora@demo.local');await nav(page,'reports');await page.getByRole('button',{name:'Add new',exact:true}).click();await fill(page,'month','2026-10');await fill(page,'accomplishments','Delivered brand assets and documented the revisions.');await expect(page.locator('#field-answer_0')).toBeVisible();for(const el of await page.locator('[id^="field-answer_"]').all())await el.fill('Fictional design evidence with project context.');await submit(page);await page.locator('tbody tr').filter({hasText:'2026-10'}).getByRole('button',{name:'View',exact:true}).click();const href=await page.locator('.modal a[href^="/api/exports/reports/"]').getAttribute('href');const response=await page.request.get(href);expect(response.status()).toBe(200);expect((await response.body()).subarray(0,4).toString()).toBe('%PDF');await expect(page.locator('.modal-body')).not.toContainText('"role_data"');
});
test('anonymous feedback uses private bookmarks without displaying case references',async({page})=>{
 await login(page,'nora@demo.local');await nav(page,'feedback');await page.getByRole('button',{name:'Share feedback',exact:true}).click();await fill(page,'title','Browser private process concern');await fill(page,'kind','Complaint');await fill(page,'detail','A fictional workload concern without identifying details.');await expect(page.locator('#field-anonymous')).toBeChecked();await submit(page);await expect(page.locator('#content')).not.toContainText('CASE-');await page.locator('[data-action="h-feedback-track"]').first().click();await expect(page.locator('.modal')).not.toContainText('CASE-');await fill(page,'message','Additional private context.');await submit(page);
});
test('owner has contract visibility and no personal employee workflows',async({page})=>{
 await login(page,'owner@demo.local');await expect(page.locator('.sidebar [data-page="leave_requests"]')).toHaveCount(0);await expect(page.locator('.sidebar [data-page="payroll"]')).toHaveCount(0);await expect(page.getByRole('button',{name:'Check in',exact:true})).toHaveCount(0);await nav(page,'contracts');await expect(page.locator('tbody tr')).toHaveCount(12);await nav(page,'surveys');await expect(page.getByRole('button',{name:'Respond',exact:true})).toHaveCount(0);await nav(page,'terminations');await page.getByRole('button',{name:'Propose termination',exact:true}).click();await expect(page.locator('#field-supporting_document')).toBeVisible();
});
test('real AI unavailable state and restricted salary API do not simulate answers',async({page})=>{
 await login(page,'nora@demo.local');await nav(page,'advisor');await expect(page.locator('.ai-disclosure')).toContainText('No simulated responses');await expect(page.locator('#chat-form button')).toBeDisabled();const r=await page.request.post('/api/ai',{data:{message:'Tell me Sara salary'}});expect(r.status()).toBe(403);
});
test('Arabic RTL, mobile overflow, collapse and sidebar scroll preservation',async({page})=>{
 await login(page,'owner@demo.local');await nav(page,'pipeline');await page.screenshot({path:'test-results/company-pipeline.png',fullPage:true});await page.locator('.nav-scroll').evaluate(el=>el.scrollTop=250);await page.locator('.sidebar [data-page=insights]').scrollIntoViewIfNeeded();const before=await page.locator('.nav-scroll').evaluate(el=>el.scrollTop);await nav(page,'insights');const after=await page.locator('.nav-scroll').evaluate(el=>el.scrollTop);expect(Math.abs(after-before)).toBeLessThan(5);await page.locator('[data-action="language"]').click();await expect(page.locator('html')).toHaveAttribute('dir','rtl');await page.screenshot({path:'test-results/company-arabic.png',fullPage:true});await page.setViewportSize({width:390,height:844});await expect(page.locator('.sidebar')).not.toBeInViewport();expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();await page.screenshot({path:'test-results/company-mobile.png',fullPage:true,animations:'disabled'});await page.locator('[data-action="toggle-sidebar"]').click();await expect(page.locator('.sidebar')).toBeInViewport();
});
test('quotation line pricing, version history and branded PDF',async({page})=>{
 await login(page,'owner@demo.local');await nav(page,'quotations');await page.getByRole('button',{name:'Add new',exact:true}).click();await fill(page,'title','Browser content proposal');await page.locator('#field-deal_id').selectOption({label:'Browser agency opportunity'});await fill(page,'kind','Proposal');await fill(page,'expires','2026-12-10');await fill(page,'discount_percent',10);await page.locator('.quote-line [name="description"]').fill('Content production package');await page.locator('.quote-line [name="quantity"]').fill('2');await page.locator('.quote-line [name="price"]').fill('50000');await submit(page);await page.locator('tbody tr').filter({hasText:'Browser content proposal'}).getByRole('button',{name:'View',exact:true}).click();await expect(page.locator('.report-kpis')).toContainText('900');const href=await page.locator('.modal a[href^="/api/exports/quotations/"]').getAttribute('href');const r=await page.request.get(href);expect((await r.body()).subarray(0,4).toString()).toBe('%PDF');
});
test('department deliverable review connects project effort to employee evidence',async({page})=>{
 await login(page,'owner@demo.local');await nav(page,'projects');await page.locator('tbody tr').filter({hasText:'Browser production launch'}).getByRole('button',{name:'View',exact:true}).click();await page.getByRole('button',{name:'Assign member',exact:true}).click();await page.locator('#field-employee_id').selectOption({label:'Nora Khalil'});await fill(page,'responsibility','Design production');await submit(page);
 await page.locator('[data-action="logout"]').click();await login(page,'project.manager@demo.local');await nav(page,'tasks');await page.getByRole('button',{name:'Add new',exact:true}).click();await page.locator('#field-team_id').selectOption({label:'Creative Studio team'});await page.locator('#field-employee_id').selectOption({label:'Nora Khalil'});await page.locator('#field-project_id').selectOption({label:'Browser production launch'});await fill(page,'title','Browser contextual design task');await fill(page,'due','2026-12-15');await fill(page,'priority','High');await fill(page,'complexity',4);await fill(page,'estimated_hours',6);await submit(page);
 await page.locator('[data-action="logout"]').click();await login(page,'nora@demo.local');await nav(page,'deliverables');await page.getByRole('button',{name:'Add new',exact:true}).click();await page.locator('#field-project_id').selectOption({label:'Browser production launch'});await page.locator('#field-task_id').selectOption({label:'Browser contextual design task'});await page.locator('#field-employee_id').selectOption({label:'Nora Khalil'});await fill(page,'title','Browser reviewed design');await fill(page,'kind','Design draft');await fill(page,'brief','Accessible visual hierarchy for the client launch.');for(const el of await page.locator('[id^="delivery-"]').all())await el.fill('Fictional work evidence for this department.');await submit(page);
 await page.locator('[data-action="logout"]').click();await login(page,'project.manager@demo.local');await nav(page,'deliverables');await page.locator('tbody tr').filter({hasText:'Browser reviewed design'}).getByRole('button',{name:'View',exact:true}).click();await expect(page.locator('.modal-body')).toContainText('Design rationale');await page.getByRole('button',{name:'Review deliverable',exact:true}).click();await fill(page,'decision','Approved');await fill(page,'quality_score',92);await fill(page,'comment','Reviewed against the client brief and accessibility requirements.');await submit(page);
 await page.locator('[data-action="logout"]').click();await login(page,'nora@demo.local');await nav(page,'tasks');await page.locator('tbody tr').filter({hasText:'Browser contextual design task'}).getByRole('button',{name:'Update task',exact:true}).click();await fill(page,'status','Completed');await fill(page,'actual_hours',5);await fill(page,'delay_context','The client clarified the brief during review.');await submit(page);await nav(page,'kpis');await page.locator('tbody tr').first().getByRole('button',{name:'View',exact:true}).click();await page.getByRole('button',{name:'Business contribution evidence',exact:true}).click();await expect(page.locator('.modal-body')).toContainText('92');await expect(page.locator('.modal-body')).toContainText('client clarified');
});
test('Owner can respond only after HR explicitly shares a confidential case',async({page})=>{
 await login(page,'owner@demo.local');await nav(page,'feedback');await expect(page.locator('#content')).not.toContainText('Browser private process concern');await page.locator('[data-action="logout"]').click();await login(page);await nav(page,'feedback');await page.locator('.record-card').filter({hasText:'Browser private process concern'}).getByRole('button',{name:'Handle feedback',exact:true}).click();await page.locator('#field-owner_visible').check();await fill(page,'message','Shared with the Owner under the authorized confidentiality policy.');await submit(page);await page.locator('[data-action="logout"]').click();await login(page,'owner@demo.local');await nav(page,'feedback');await page.locator('.record-card').filter({hasText:'Browser private process concern'}).getByRole('button',{name:'Handle feedback',exact:true}).click();await expect(page.locator('.modal-body')).not.toContainText('Nora Khalil');await fill(page,'message','We will review the workload planning process with HR.');await submit(page);
});
