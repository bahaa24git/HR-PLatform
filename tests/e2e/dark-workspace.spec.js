const {test,expect}=require('@playwright/test');

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
