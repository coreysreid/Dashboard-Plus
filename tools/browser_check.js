// Click through the real dashboard in Chromium and stop at the first thing that does not work.
// Called by tools/browser_check.py, which starts the server and writes the plan; not run on its own.
// Usage: node tools/browser_check.js <plan.json>
// Prints "ok <what was checked>" for each check; on a failure prints "FAILED: <plain words>" and exits 1.
const fs = require('fs');
const { chromium } = require('playwright');

class Failed extends Error {}
function expect(condition, message) { if (!condition) throw new Failed(message); }

(async () => {
  const plan = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
  const base = plan.base.replace(/\/$/, '');
  const browser = await chromium.launch(plan.executablePath ? { executablePath: plan.executablePath } : {});
  const page = await browser.newPage({ locale: plan.locale, timezoneId: plan.timezone });
  page.setDefaultTimeout(10000);
  const problems = [];  // browser console errors and refused requests, reported together at the end
  let refusalExpected = false;  // set around the one save that is meant to be refused
  const expected = (text) => refusalExpected && /\b422\b/.test(text);
  page.on('console', (msg) => {
    if (msg.type() === 'error' && !expected(msg.text())) problems.push(`console error on ${page.url()}: ${msg.text()}`);
  });
  page.on('pageerror', (error) => problems.push(`script error on ${page.url()}: ${error.message}`));
  page.on('response', (response) => {
    if (response.status() >= 400 && !expected(String(response.status()))) {
      problems.push(`${response.request().method()} ${response.url().replace(base, '')} answered ${response.status()}`);
    }
  });
  const ok = (what) => console.log('ok ' + what);
  const goto = async (path) => {
    const response = await page.goto(base + path);
    expect(response && response.ok(), `Opening ${path} answered ${response ? response.status() : 'nothing'}.`);
  };
  const submit = async (selector) => {
    const [response] = await Promise.all([page.waitForNavigation(), page.click(selector)]);
    expect(response && response.ok(), `Saving the form at ${page.url()} answered ${response ? response.status() : 'nothing'}.`);
    const refused = await page.locator('.problem').allTextContents();
    expect(!refused.length, `The form at ${page.url()} was not saved: ${refused.join(' ').trim()}`);
  };
  const html = () => page.content();
  const text = (selector) => page.locator(selector).innerText();

  async function steps(list) {  // the wizard's steps, written by make_screenshots.wizard_steps
    for (const step of list) {
      if (step.goto) await goto(step.goto);
      if (step.fill) await page.fill(step.fill, String(step.value));
      if (step.select) await page.selectOption(step.select, String(step.value));
      if (step.check) await page.setChecked(step.check, step.value !== false);
      if (step.click) await page.click(step.click);
    }
  }

  async function checkHomeSetup() {  // Set up my home (decision 0103): rooms, a spot inside one, a connection, with the keyboard
    const card = (name) => page.locator(`section.room:has(h3:text-is("${name}"))`);
    for (const name of ['Check room A', 'Check room B']) {
      await page.focus('#new-room');
      await page.keyboard.type(name);
      await Promise.all([page.waitForNavigation(), page.keyboard.press('Enter')]);
      expect(await card(name).count() === 1, `Adding the room "${name}" should show its card; it did not.`);
    }
    await card('Check room A').locator('summary', { hasText: 'Add a storage spot' }).click();
    await card('Check room A').locator('input[name=name]').first().fill('Check shelf');
    await submit(`section.room:has(h3:text-is("Check room A")) button:text-is("Add storage spot")`);
    expect((await card('Check room A').innerText()).includes('Check shelf'), 'The new storage spot should show inside its room.');
    const join = async () => {
      await card('Check room A').locator('summary', { hasText: 'Connect Check room A' }).click();
      const select = card('Check room A').locator('select[name=connects_to]');
      const value = await select.locator('option', { hasText: 'Check room B' }).getAttribute('value');
      await select.selectOption(value);
      await Promise.all([page.waitForNavigation(), card('Check room A').locator('button:text-is("Add connection")').click()]);
    };
    await join();
    expect((await card('Check room B').innerText()).includes('Check room A'), 'A connection should show on both rooms.');
    refusalExpected = true;  // the same two rooms again is refused, in words
    await join();
    refusalExpected = false;
    const refused = (await page.locator('.problem').allTextContents()).join(' ');
    expect(refused.includes('already joined'), `Connecting the same two rooms twice should be refused; the page said "${refused}".`);
    await page.goto(base + '/set-up-home?welcome=1');
    await card('Check room A').locator('summary', { hasText: 'Rename, move or delete Check shelf' }).click();
    await submit(`section.room:has(h3:text-is("Check room A")) button:text-is("Delete Check shelf")`);
    await card('Check room A').locator('summary', { hasText: 'Rename, move or delete Check room A' }).click();
    await submit(`section.room:has(h3:text-is("Check room A")) button:text-is("Delete Check room A")`);
    expect(await card('Check room A').count() === 0, 'A deleted room should leave the page.');
    expect(!(await card('Check room B').innerText()).includes('Check room A'), "A deleted room's connections should go with it.");
    await card('Check room B').locator('summary', { hasText: 'Rename, move or delete Check room B' }).click();
    await submit(`section.room:has(h3:text-is("Check room B")) button:text-is("Delete Check room B")`);
    expect(await page.locator('#skip').count() === 1, 'Set up my home should still offer "Skip for now" after changes.');
    ok('Set up my home: rooms added with the keyboard, a storage spot, a connection on both rooms, a repeat refused, deleting a room takes its connections');
  }

  async function checkSetup() {
    await goto(plan.launch);
    expect(new URL(page.url()).pathname === '/setup', `A new data folder should open the setup questions, but opened ${page.url()}.`);
    await steps(plan.wizard);
    await submit('form.record button[type=submit]');
    expect(new URL(page.url()).pathname === '/set-up-home', `After setup the browser should offer Set up my home, but is on ${page.url()}.`);
    await checkHomeSetup();
    await Promise.all([page.waitForNavigation(), page.click('#skip')]);
    expect(new URL(page.url()).pathname === '/', `"Skip for now" should go to Home, but went to ${page.url()}.`);
    expect(await page.locator('#my-home a[href="/set-up-home"]').count() === 1, 'Home should always link to Set up my home.');
    const areas = await page.locator('.areas section.area h2').allTextContents();
    expect(areas.length >= 2, `Home should show a card for each area, but showed ${areas.length}.`);
    expect(areas.includes('People'), `Home should have a People card; it has: ${areas.join(', ')}.`);
    ok(`setup wizard saves; Home shows ${areas.length} area cards`);
  }

  async function checkDates() {
    const d = plan.dates;
    await goto('/t/stock__items/new');
    await page.fill('#f-name', d.item);
    await page.keyboard.press('Escape');
    // "Is this water safe to drink now?" is asked only for water (show_when in labels.toml).
    await page.selectOption('#f-category', 'water');
    expect(await page.isVisible('#f-drinking-yes'), 'Choosing "Water" should ask whether it is safe to drink; it did not.');
    await page.selectOption('#f-category', 'pantry');
    expect(!(await page.isVisible('#f-drinking-yes')), 'The drinking-water question should go away for pantry items.');
    await page.fill('#f-expires', d.typed);
    const preview = await text('#f-expires-preview');
    expect(preview.includes(d.words), `Typing ${d.typed} should show "${d.words}" beside the date, but showed "${preview}".`);
    await page.fill('#f-expires', d.wrongOrder);
    const hint = await text('#f-expires-preview');
    expect(hint.includes(d.hint), `Typing ${d.wrongOrder} (the other country's order) should say "${d.hint}", but said "${hint}".`);
    await page.fill('#f-expires', d.typed);
    await page.fill('#f-quantity', '4');  // an item's use-by shows on the list only while its batch holds some
    await submit('button[name=then][value=done]');
    const cells = await itemCells(d.item);
    expect(cells.expires === d.typed, `On the stock list the saved use-by date should read ${d.typed}, not "${cells.expires}" (the row reads: ${cells.all}).`);
    await Promise.all([page.waitForNavigation(), page.locator('tr', { hasText: d.item }).locator('a', { hasText: 'Open' }).click()]);
    // Once saved, the use-by date belongs to the item's first batch, shown under Batches.
    const body = await text('main');
    expect(body.includes('use by ' + d.typed), `The item's page should list its batch "use by ${d.typed}"; it does not.`);
    ok(`${plan.locale}: drinking-water question follows the category; typed date ${d.typed} saves and shows back the same; preview "${d.words}"; wrong order hints "${d.hint}"`);
  }

  async function itemCells(name) {  // one row of the stock list, read by its column headings
    await goto('/t/stock__items');
    const row = page.locator('tbody tr', { hasText: name });
    expect(await row.count() === 1, `"${name}" should be on the stock list once; it is there ${await row.count()} times.`);
    const heads = (await page.locator('thead th').allInnerTexts()).map((h) => h.replace(/[↑↓]/g, '').trim());
    const cells = (await row.locator('td').allInnerTexts()).map((c) => c.trim());
    const cell = (heading) => cells[heads.indexOf(heading)];
    return { quantity: Number(cell('Amount on hand')), expires: cell('Use by'), all: heads.map((h, i) => `${h}=${cells[i]}`).join(', ') };
  }

  async function checkStockIn() {
    const name = plan.stock.item;
    await goto('/t/stock__movements/new');
    const itemId = await page.$eval('#f-item', (s, n) => (Array.from(s.options).find((o) => o.text.trim() === n) || {}).value, name);
    expect(itemId, `"${name}" is not offered as an Item on the stock in form.`);
    const before = (await itemCells(name)).quantity;
    await goto('/t/stock__movements/new');
    const note = await text('[data-follows-note="f-lot"]');
    expect(note.includes('Choose the item first'), `Before an item is chosen, "Which batch" should say to choose the item first; it said "${note}".`);
    // Typing in the find box picks the item, as a person would on a long list.
    const find = page.locator('input.find[data-find-for="f-item"]');
    if (await find.count()) {
      await find.fill(name);
      expect(await page.inputValue('#f-item') === itemId, `Typing "${name}" in the find box did not choose it.`);
    } else {
      await page.selectOption('#f-item', itemId);
    }
    const lots = await page.$eval('#f-lot', (s) => Array.from(s.options).filter((o) => o.value && !o.hidden)
      .map((o) => ({ value: o.value, owner: o.dataset.owner, text: o.text })));
    expect(lots.length >= 2, `"${name}" has ${plan.stock.batches} batches but "Which batch" lists ${lots.length}.`);
    const strays = lots.filter((o) => o.owner !== itemId).map((o) => o.text);
    expect(!strays.length, `"Which batch" lists other items' batches: ${strays.join('; ')}.`);
    await page.selectOption('#f-reason', 'bought');
    let blank = await page.$eval('#f-lot option[value=""]', (o) => o.textContent);
    expect(blank === plan.stock.blankAdds, `With Reason "bought", a blank batch should read "${plan.stock.blankAdds}", not "${blank}".`);
    await page.selectOption('#f-reason', 'used');
    blank = await page.$eval('#f-lot option[value=""]', (o) => o.textContent);
    expect(blank === plan.stock.blankTakes, `With Reason "used", a blank batch should read "${plan.stock.blankTakes}", not "${blank}".`);
    expect(!(await page.isVisible('#f-expires')), '"Use by" should be hidden when the reason is not "bought".');
    await page.selectOption('#f-reason', 'bought');
    expect(await page.isVisible('#f-expires') && await page.isVisible('#f-place'),
      '"Use by" and "Where you put it" should show for stock bought into a new batch.');
    await page.selectOption('#f-lot', lots[0].value);
    expect(!(await page.isVisible('#f-expires')) && !(await page.isVisible('#f-place')),
      '"Use by" and "Where you put it" should hide once a batch is chosen.');
    await page.fill('#f-amount', '2');
    await submit('button[name=then][value=done]');
    const after = (await itemCells(name)).quantity;
    expect(Math.abs(after - before - 2) < 1e-9, `Stock in of 2 should take "${name}" from ${before} to ${before + 2}, but it shows ${after}.`);
    ok(`stock in: batches follow the item; blank wording follows Reason; Use by and place hide for a batch; ${before} -> ${after}`);
  }

  async function checkStocktake() {  // Count this batch: one correction of the difference, never the count on top
    const name = plan.stock.item;
    const before = (await itemCells(name)).quantity;
    await page.click(`a[aria-label="Open ${name}"]`);
    const count = page.locator('a[aria-label^="Count "]').first();
    expect(await count.count(), `"${name}" should offer Count next to each batch; it does not.`);
    await Promise.all([page.waitForNavigation(), count.click()]);
    const recorded = Number(((await text('form.record')).match(/Recorded here: ([\d.]+)/) || [])[1]);
    expect(!Number.isNaN(recorded), 'Count this batch should say how many are recorded here.');
    await page.fill('#f-counted', String(recorded + 2));
    await submit('button:has-text("Review count")');
    const review = await text('main');
    expect(review.includes('This adds 2') && review.includes('stocktake correction'), `The review should say it adds 2 as a stocktake correction; it says "${review}".`);
    await submit('button:has-text("Save correction")');
    const saved = await text('[role=status]');
    expect(saved.includes(`This batch has ${recorded + 2}`) && saved.includes('Stocktake correction: +2'), `After saving, the page should say the batch has ${recorded + 2} and show the +2 correction; it says "${saved}".`);
    const after = (await itemCells(name)).quantity;
    expect(Math.abs(after - before - 2) < 1e-9, `Counting ${recorded + 2} where ${recorded} were recorded should take "${name}" from ${before} to ${before + 2}, but it shows ${after}.`);
    ok(`stocktake: counted ${recorded + 2} where ${recorded} were recorded; one correction of +2; ${before} -> ${after}`);
  }

  async function checkMarkReturned() {  // a one-step action declared in tables.toml (decision 0075)
    const name = plan.loan.name;
    await goto('/t/lent_out__loans');
    await Promise.all([page.waitForNavigation(), page.click(`a[aria-label="Open ${name}"]`)]);
    const button = 'button[data-action="returned"]';
    expect(await page.locator(button).count() === 1, `The page for "${name}" should offer Mark returned while it is still out; it does not.`);
    await submit(button);
    const said = await text('[role=status]');
    expect(said.includes('Marked returned today'), `After Mark returned the page should say "Marked returned today"; it says "${said}".`);
    expect(await page.inputValue('#f-status') === 'returned', 'After Mark returned, "Is it back?" should read Yes, returned.');
    expect(await page.inputValue('#f-returned_on') !== '', 'After Mark returned, Returned on should be filled in with today.');
    expect(!(await page.locator(button).count()), 'Mark returned should go away once the loan is back.');
    ok(`Mark returned: one press on "${name}" saves it as back today, says so, and the button goes`);
  }

  async function checkMarkDone() {  // an action with a small form that adds Work done, saved once, with Undo (decision 0091)
    const job = plan.job;
    await goto('/t/home_care__jobs');
    await Promise.all([page.waitForNavigation(), page.click(`a[aria-label="Open ${job.name}"]`)]);
    const jobUrl = page.url();
    const before = await page.inputValue('#f-next_due');
    await Promise.all([page.waitForNavigation(), page.click('a[data-action="done"]')]);
    expect((await text('h1')).includes(job.name), `Mark done should open a form named after "${job.name}"; it shows "${await text('h1')}".`);
    expect(!(await page.locator('input[name=next_choice]:checked').count()), 'No next-date choice should be chosen before the person chooses one.');
    expect(await page.inputValue('#f-done_by') === '', 'Who did it should start blank even though someone usually does this job.');
    await page.fill('#f-next_date', job.next);
    expect(await page.isChecked('#next-date-choice'), 'Typing a next date should choose "Choose a date".');
    const [response] = await Promise.all([page.waitForNavigation(), page.dblclick('form.record button[type=submit]')]);
    expect(response && response.ok(), `Saving Mark done answered ${response ? response.status() : 'nothing'}.`);
    const said = await text('[role=status]');
    expect(said.includes('Marked done on') && said.includes(`Do again by ${job.next}`), `After Mark done the page should name both dates; it says "${said}".`);
    expect(await page.inputValue('#f-next_due') === job.next, `After Mark done, Do again by should read ${job.next}.`);
    const added = (await html()).split('used Mark done').length - 1;
    expect(added === 1, `A double click should save one completion; history shows ${added}.`);
    await Promise.all([page.waitForNavigation(), page.click('button[data-undo]')]);
    expect((await text('[role=status]')).startsWith('Undone.'), `Undo should say "Undone."; it says "${await text('[role=status]')}".`);
    expect(await page.inputValue('#f-next_due') === before, `After Undo, Do again by should be back to ${before}.`);
    expect(page.url().startsWith(jobUrl.split('?')[0]), 'Undo should come back to the job.');
    ok(`Mark done: "${job.name}" saved once with Do again by ${job.next} (double click), then undone back to ${before}`);
  }

  async function checkImport() {  // Import from a spreadsheet: read in the page, checked, sent to Review, accepted (decision 0080)
    const c = plan.csv;
    await goto('/settings/import?table=stock__items');
    await page.setInputFiles('#import-file', { name: c.file, mimeType: 'text/csv', buffer: Buffer.from(c.text, 'utf8') });
    await submit('button[type=submit]:has-text("Read the file")');
    expect(await page.inputValue('#match_1') === 'minimum', 'The heading "Keep at least" should be matched to Keep at least by itself.');
    await Promise.all([page.waitForNavigation(), page.click('button:has-text("Check the rows")')]);
    const summary = await text('#dry-run');
    expect(summary.includes(`${c.ready} rows ready, ${c.fixing} needs fixing`), `The check should say "${c.ready} rows ready, ${c.fixing} needs fixing"; it says "${summary}".`);
    await Promise.all([page.waitForNavigation(), page.click(`button:has-text("Send ${c.ready} rows to Review")`)]);
    expect(new URL(page.url()).pathname === '/review', `Send to Review should open Review, not ${page.url()}.`);
    expect((await html()).includes(`Import &#39;${c.file}&#39;`) || (await html()).includes(`Import '${c.file}'`), 'Review does not show the import by its file name.');
    await page.click(`summary:has-text("Accept all ${c.ready}")`);  // Accept all asks first (decision 0101)
    expect((await text('details.confirm-all[open]')).includes(`This adds ${c.ready} new records`), 'Accept all should say how many records it adds before it adds them.');
    await submit(`button:has-text("Yes, accept all ${c.ready}")`);
    await goto('/t/stock__items');
    await Promise.all([page.waitForNavigation(), page.click(`a[aria-label="Open ${c.item}"]`)]);
    const note = await page.inputValue('#f-notes');
    expect(note.replace(/\r\n/g, '\n') === c.note, `The imported note should read "${c.note}"; it reads "${note}".`);
    ok(`spreadsheet import: ${c.ready} rows ready and ${c.fixing} to fix, sent to Review, accepted; a quoted two-line note kept`);
  }

  async function sameColumn(width) {  // Accept and Reject sit in one fixed column on every row, grouped or not
    await page.setViewportSize({ width, height: 900 });
    for (const which of ['[data-accept]', '[data-reject]']) {
      const boxes = await page.locator(`[data-row] ${which}`).evaluateAll((els) => els.map((e) => {
        const r = e.getBoundingClientRect(); return [Math.round(r.left), Math.round(r.width)];
      }));
      expect(boxes.length === plan.review.rows, `Review should show ${which} on every row; found ${boxes.length}.`);
      const moved = boxes.filter((b) => Math.abs(b[0] - boxes[0][0]) > 1 || Math.abs(b[1] - boxes[0][1]) > 1);
      expect(!moved.length, `At ${width}px wide, the ${which} buttons are not all in the same place: ${JSON.stringify(boxes)}.`);
    }
    const sideways = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    expect(sideways <= 0, `At ${width}px wide, Review scrolls sideways by ${sideways}px.`);
  }

  async function checkReview() {  // a helper's receipt: fixed buttons, keys, group ticking, Accept all (decision 0101)
    const r = plan.review;
    await goto('/review');
    const rows = () => page.locator('[data-row]').count();
    expect(await rows() === r.rows, `Review should show ${r.rows} rows from ${r.helper}.`);
    expect(await page.isVisible('#review-keys'), 'Review should show the keys hint when its script runs.');
    expect((await text('.review-group .group-label')).includes('Added together'), 'The group should be labelled "Added together".');
    await sameColumn(1280);
    await sameColumn(375);
    await page.setViewportSize({ width: 1280, height: 900 });
    const current = () => page.evaluate(() => Array.from(document.querySelectorAll('[data-row]')).findIndex((e) => e.classList.contains('current')));
    const ticks = async () => JSON.stringify(await page.locator('[data-row] input[type=checkbox]').evaluateAll((els) => els.map((e) => e.checked)));
    expect(await current() === 0, 'The first row should be highlighted when Review opens.');
    await page.keyboard.press('j');
    expect(await current() === 1, 'J should move the highlight to the next row.');
    await page.keyboard.press('ArrowUp');
    await page.keyboard.press('ArrowDown');
    expect(await current() === 1, 'Up and Down should move the highlight.');
    await page.keyboard.press(' ');
    expect(await ticks() === '[true,true,false]', `Space should tick the row and the rest of its group; ticks are ${await ticks()}.`);
    await page.keyboard.press(' ');
    expect(await ticks() === '[false,false,false]', 'Space again should untick the whole group.');
    await page.evaluate(() => { const i = document.createElement('input'); i.id = 'typing'; i.type = 'text'; document.querySelector('h1').after(i); });
    await page.focus('#typing');
    await page.keyboard.type('ar jk');
    expect(new URL(page.url()).pathname === '/review' && await current() === 1 && await rows() === r.rows && await ticks() === '[false,false,false]',
      'Keys typed in a field should not move, tick, accept or reject anything.');
    await page.click('h1');
    for (const key of ['k', 'k', 'j', 'j']) await page.keyboard.press(key);
    expect(await current() === 2, 'K and J should move the highlight up and down.');
    await Promise.all([page.waitForNavigation(), page.keyboard.press('a')]);
    expect((await text('[role=status]')).includes('Added to Stock in and out.'), `A should accept the highlighted row; Review says "${await text('[role=status]')}".`);
    expect(await rows() === r.rows - 1, 'After A, the accepted row should be gone from Review.');
    await page.click(`summary:has-text("Accept all ${r.rows - 1}")`);
    expect((await text('details.confirm-all[open]')).includes('1 to Stock items and 1 to Stock in and out'), 'Accept all should say which lists get records.');
    await submit(`button:has-text("Yes, accept all ${r.rows - 1}")`);
    expect((await text('[role=status]')).includes(`Added ${r.rows - 1} records.`), `Accept all should add the group; Review says "${await text('[role=status]')}".`);
    ok(`Review: Accept and Reject stay in one column at 1280px and 375px; J, K and arrows move, Space ticks a whole group, A accepts, keys in a field do nothing; Accept all asks first, then adds "${r.item}" with its Stock in`);
  }

  async function checkPrivateDetail() {
    const p = plan.private;
    await goto('/t/people__important_info');
    expect(!(await html()).includes(p.secret), 'The Important details list sent a private detail to the browser before Show was pressed.');
    const row = page.locator('tr', { hasText: p.person });
    await row.locator('button.secret').click();
    await row.locator('span', { hasText: p.secret }).waitFor({ timeout: 5000 }).catch(() => {});
    expect((await row.innerText()).includes(p.secret), `Pressing Show beside ${p.person} did not show the private detail.`);
    await Promise.all([page.waitForNavigation(), row.locator('a', { hasText: 'Open' }).click()]);
    const recordUrl = new URL(page.url()).pathname;
    expect(!(await html()).includes(p.secret), 'Opening the record sent the private detail before "Show private detail" was pressed.');
    expect(await page.isVisible('text=Show private detail'), 'The record does not offer "Show private detail".');
    // A save refused for another answer must keep the private detail closed, so the next save keeps it too.
    await page.selectOption('#f-kind', '');
    refusalExpected = true;  // this one save is meant to be refused (422), so it is not a problem
    const [refused] = await Promise.all([page.waitForNavigation(), page.click('button[type=submit]:has-text("Save changes")')]);
    refusalExpected = false;
    expect(refused.status() === 422, `Saving with "Kind" left blank should answer 422 (refused), not ${refused.status()}.`);
    expect(await page.isVisible('#error-summary'), 'Saving with "Kind" left blank should be refused, but was not.');
    expect(await page.isVisible('text=Show private detail'), 'After a refused save the private detail came back open and empty.');
    await page.selectOption('#f-kind', 'other');
    await submit('button[type=submit]:has-text("Save changes")');
    await goto(recordUrl);
    expect(await page.inputValue('#f-kind') === 'other', 'Changing the kind of detail was not saved.');
    await page.click('text=Show private detail');
    await page.locator('#f-detail').waitFor({ state: 'visible' });
    const value = await page.inputValue('#f-detail');
    expect(value.includes(p.secret), `Saving another field lost the private detail: it now reads "${value}".`);
    ok('private detail: hidden in the list and the record, shown on Show, kept when another field is saved');
  }

  async function checkPrivateSheet() {
    const p = plan.private;
    await goto('/sheet/people/emergency_medical');
    expect(!(await html()).includes(p.secret), 'The private medical sheet sent private details before being asked.');
    await goto('/sheet/people/emergency_medical?show=1');  // decision 0071: a link cannot skip the question
    expect(!(await html()).includes(p.secret), 'A "?show=1" link opened the private sheet without the Show private sheet button.');
    await Promise.all([page.waitForNavigation(), page.click('text=Show private sheet')]);
    expect((await html()).includes(p.secret), 'After "Show private sheet" the sheet does not show the private details.');
    ok('private medical sheet asks first (a ?show=1 link does not skip it), then shows');
  }

  async function checkClose() {
    await goto('/close');
    await Promise.all([page.waitForNavigation(), page.click('form button[type=submit]')]);
    expect((await text('h1')).includes('Saved and closed'), `Save and exit should end on "Saved and closed", but shows "${await text('h1')}".`);
    ok('save and exit');
  }

  let code = 0;
  try {
    if (plan.phase === 'setup') {
      await checkSetup();
    } else {
      await goto(plan.launch);
      await checkDates();
      if (plan.stock) { await checkStockIn(); await checkStocktake(); }
      if (plan.loan) await checkMarkReturned();
      if (plan.job) await checkMarkDone();
      if (plan.csv) await checkImport();
      if (plan.review) await checkReview();
      if (plan.private) { await checkPrivateDetail(); await checkPrivateSheet(); }
      await checkClose();
    }
    expect(!problems.length, 'The browser reported problems:\n  ' + problems.join('\n  '));
    ok(`${plan.locale}: no console errors and no refused requests`);
  } catch (error) {
    console.log('FAILED: ' + (error instanceof Failed ? error.message : `${error.message} (on ${page.url()})`));
    if (problems.length && !(error instanceof Failed && error.message.startsWith('The browser reported'))) {
      console.log('The browser also reported:\n  ' + problems.join('\n  '));
    }
    code = 1;
  } finally {
    await browser.close();
  }
  process.exit(code);
})().catch((error) => { console.log('FAILED: ' + error.message); process.exit(1); });
