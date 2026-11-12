const {defineConfig}=require('@playwright/test');
module.exports=defineConfig({
  testDir:'./tests/e2e',fullyParallel:false,workers:1,timeout:30000,
  reporter:[['list'],['json',{outputFile:'test-results/browser-results.json'}]],
  use:{baseURL:'http://127.0.0.1:8011',channel:process.env.HR_BROWSER_CHANNEL||'chrome',headless:true,viewport:{width:1440,height:1100},screenshot:'only-on-failure',trace:'retain-on-failure'},
  webServer:process.env.HR_E2E_EXTERNAL==='1'?undefined:{command:'python -m backend.server --port 8011',url:'http://127.0.0.1:8011/api/health',reuseExistingServer:false,env:{HR_DATABASE:'data/e2e-'+Date.now()+'.sqlite3'},timeout:30000}
});
