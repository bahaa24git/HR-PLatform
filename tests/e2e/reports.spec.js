const {test,expect}=require('@playwright/test');

test('structured reports render native tables, secure previews, charts and downloadable PDFs',async({page})=>{
 const errors=[];page.on('pageerror',error=>errors.push(error.message));
 await page.goto('/');await page.locator('#login-form button[type="submit"]').click();
 await page.locator('.sidebar .nav-button[data-page="advisor"]').click();
 const report=page.locator('.report-document').filter({hasText:'Top 5 Employee Performance'});
 await expect(report.locator('.ai-report-table').first().locator('tbody tr')).toHaveCount(5);
 await expect(report.locator('.ai-report-table').first().locator('thead th')).toHaveCount(3);
 await expect(report.locator('.report-chart')).toHaveCount(1);
 await expect(report).not.toContainText('| ---');
 await report.locator('..').getByRole('button',{name:'Preview report',exact:true}).click();
 await expect(page.locator('#report-preview .report-document h2')).toHaveText('Top 5 Employee Performance');
 await page.locator('#report-orientation').selectOption('landscape');await page.locator('#report-language').selectOption('ar');await page.locator('#report-template').selectOption('department');await page.locator('#report-charts').uncheck();
 await expect(page.locator('#report-preview .report-document')).toHaveAttribute('dir','rtl');
 await expect(page.locator('#report-preview .report-chart')).toHaveCount(0);
 const href=await page.locator('#report-download').getAttribute('href');expect(href).toContain('orientation=landscape');expect(href).toContain('charts=0');
 const pdf=await page.request.get(href);expect(pdf.status()).toBe(200);expect((await pdf.body()).subarray(0,5).toString()).toBe('%PDF-');
 await page.locator('#report-language').selectOption('en');await page.locator('#report-template').selectOption('employee_performance');await page.locator('#report-charts').check();
 await page.screenshot({path:'test-results/report-preview.png',fullPage:true});
 await page.locator('.modal-actions [data-action="close"]').click();
 // Model-supplied labels and cells remain text, including inside chart titles.
 const history=await (await page.request.get('/api/ai/history')).json();
 const message=history.messages.find(m=>m.result?.report);message.result.report.sections[1].rows[0][0]='<img src=x onerror=alert(1)>';
 message.result.report.sections[2].title='<script>alert(1)</script>';
 await page.route('**/api/ai/history',route=>route.fulfill({json:{messages:[message],conversation_id:'security-test'}}));
 await page.reload();await page.locator('.sidebar .nav-button[data-page="advisor"]').click();
 await expect(page.locator('.report-document img,.report-document script')).toHaveCount(0);await expect(page.locator('.report-document')).toContainText('<img src=x onerror=alert(1)>');
 expect(errors).toEqual([]);
});
