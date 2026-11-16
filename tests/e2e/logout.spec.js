const {test,expect}=require('@playwright/test');

test('signing out from the profile closes the dialog and unlocks the login screen',async({page})=>{
 await page.goto('/');
 await page.locator('#email').fill('hr@demo.local');
 await page.locator('#password').fill('Demo2026!');
 await page.locator('#login-form button[type="submit"]').click();
 await page.locator('[data-action="profile"]').click();
 await expect(page.getByRole('dialog')).toBeVisible();
 await page.locator('.modal [data-action="logout"]').click();
 await expect(page.locator('#login-form')).toBeVisible();
 await expect(page.locator('#modal-root')).toBeEmpty();
 await expect(page.locator('body')).not.toHaveClass(/modal-open/);
 await page.locator('#email').fill('nora@demo.local');
 await expect(page.locator('#email')).toHaveValue('nora@demo.local');
});
