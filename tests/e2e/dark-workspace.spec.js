const {test,expect}=require('@playwright/test');

test('project risk View dialog has readable detail labels and values',async({page})=>{
 await page.goto('/');await page.locator('#email').fill('owner@demo.local');await page.locator('#login-form button[type=submit]').click();await expect(page.locator('.shell')).toBeVisible();
 const id=123456;
 const record={id,project_id:999,title:'Client handover access',severity:'Low',mitigation:'Verify client access and retain the approved handover checklist.',owner_id:1,status:'Closed'};
 // This test checks presentation only; do not alter the shared report fixture's authorization scope.
 await page.route('**/api/business/project_risks',route=>route.fulfill({json:[record]}));
 await page.route('**/api/business/project_risks/'+id,route=>route.fulfill({json:{record,related:{},history:[],custom_fields:[],attachments:[]}}));
 await page.locator('.sidebar [data-page=project_risks]').click();await page.locator(`button.button[data-action=b-view][data-id="${id}"]`).click();
 await expect(page.locator('.modal .detail-grid')).toContainText('Verify client access');
 const ratios=await page.locator('.modal .detail-item').evaluateAll(cards=>{
  const luminance=color=>{const rgb=color.match(/[\d.]+/g).slice(0,3).map(v=>{v=Number(v)/255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4;});return rgb[0]*.2126+rgb[1]*.7152+rgb[2]*.0722;};
  return cards.flatMap(card=>['dt','dd'].map(selector=>{const foreground=luminance(getComputedStyle(card.querySelector(selector)).color),background=luminance(getComputedStyle(card).backgroundColor);return (Math.max(foreground,background)+.05)/(Math.min(foreground,background)+.05);}));
 });
 expect(ratios.length).toBeGreaterThan(0);for(const ratio of ratios)expect(ratio).toBeGreaterThanOrEqual(4.5);
 await page.screenshot({path:'test-results/dark-project-risk-details.png',animations:'disabled'});
});

test('sidebar sections expand independently and the white frame is removed',async({page})=>{
 await page.goto('/');await page.locator('#login-form button[type=submit]').click();
 await expect(page.locator('.shell')).toBeVisible();
 await expect(page.locator('.shell')).toHaveCSS('border-top-width','0px');
 await expect(page.locator('body')).toHaveCSS('padding-top','0px');
 const group=page.locator('.nav-group[data-section="People & culture"]');
 const link=group.locator('[data-page=employees]');
 await expect(link).toBeVisible();
 await group.locator('summary').click();await expect(link).toBeHidden();
 await expect(page.locator('.nav-scroll [data-page=dashboard]')).toBeVisible();
 await group.locator('summary').click();await expect(link).toBeVisible();
 await link.click();await expect(page.locator('#content h1')).toContainText('People');
 await group.locator('summary').click();await expect(link).toBeHidden();
 await page.locator('[data-action=toggle-sidebar]').click();await expect(link).toBeVisible();
 await page.locator('[data-action=toggle-sidebar]').click();await expect(link).toBeHidden();
 await group.locator('summary').click();await expect(link).toBeVisible();
 await page.screenshot({path:'test-results/dark-expandable-sidebar.png',animations:'disabled'});
});

test('dark workspace preserves readable surfaces, RTL and mobile navigation',async({page})=>{
 await page.goto('/');
 await page.locator('#login-form button[type=submit]').click();
 await expect(page.locator('.shell')).toBeVisible();
 await expect(page.locator('.metric')).not.toHaveCount(0);
 await expect(page.locator('.metric').first()).toHaveCSS('background-color','rgb(35, 35, 38)');
 await expect(page.locator('.sidebar')).toHaveCSS('background-color','rgb(32, 32, 34)');
 await page.screenshot({path:'test-results/dark-workspace-dashboard.png',animations:'disabled'});
 await page.locator('.sidebar [data-page=tasks]').first().click();
 await expect(page.locator('#content table')).toBeVisible();
 await expect(page.locator('#content th').first()).toHaveCSS('background-color','rgb(41, 41, 45)');
 await page.screenshot({path:'test-results/dark-workspace-tasks.png',animations:'disabled'});
 await page.locator('[data-action=language]').first().click();
 await expect(page.locator('html')).toHaveAttribute('dir','rtl');
 await page.screenshot({path:'test-results/dark-workspace-arabic.png',animations:'disabled'});
 await page.setViewportSize({width:390,height:844});
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();
 await page.locator('[data-action=toggle-sidebar]').click();
 await expect(page.locator('.sidebar')).toBeInViewport();
 await expect(page.locator('.sidebar')).toHaveCSS('transform','none');
 await page.screenshot({path:'test-results/dark-workspace-mobile.png',animations:'disabled'});
});
