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
    // The press is named in history, so it can be undone straight away (decision 0112).
    expect((await text('button[data-undo]')).includes('Undo Mark returned'), 'After Mark returned the notice should offer "Undo Mark returned".');
    await submit('button[data-undo]');
    expect((await text('[role=status]')).includes('Undone. Mark returned was taken back'), `Undo should say the press was taken back; it says "${await text('[role=status]')}".`);
    expect(await page.inputValue('#f-status') === 'out', 'After Undo, "Is it back?" should read No, still out again.');
    expect(await page.locator(button).count() === 1, 'After Undo, Mark returned should be offered again.');
    await submit(button);
    expect(await page.inputValue('#f-status') === 'returned', 'Mark returned should work again after an Undo.');
    ok(`Mark returned: one press on "${name}" saves it as back today, says so, the button goes, and Undo puts it back`);
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

  async function checkThingsToDo() {  // Things to do (decision 0107): a late routine once, ticked once, undone, at phone width
    const name = plan.routine.name;
    await page.setViewportSize({ width: 320, height: 900 });
    await goto('/to-do');
    const wide = await page.evaluate(() => document.documentElement.scrollWidth);
    expect(wide <= 320, `Things to do should fit a 320 pixel phone screen; it is ${wide} pixels wide.`);
    const row = page.locator('li.todo-row', { hasText: name });
    expect(await row.count() === 1, `"${name}" should show once on Today; it shows ${await row.count()} times.`);
    const when = await row.locator('.todo-when').innerText();
    expect(when.startsWith('Due since'), `A late routine should say "Due since"; it says "${when}".`);
    await Promise.all([page.waitForNavigation(), page.click(`a[aria-label="Mark this occurrence done: ${name}"]`)]);
    expect(!(await page.locator('input[name=next_choice]:checked').count()), 'No next date should be chosen before the person chooses one.');
    await page.check('input[name=next_choice][value=repeat]');
    const [response] = await Promise.all([page.waitForNavigation(), page.dblclick('form.record button[type=submit]')]);
    expect(response && response.ok(), `Saving the routine answered ${response ? response.status() : 'nothing'}.`);
    expect(new URL(page.url()).pathname === '/to-do', `Saving from Things to do should come back to it; it went to ${page.url()}.`);
    const said = await text('[role=status]');
    expect(said.includes('Marked done on'), `After the tick Things to do should say "Marked done on"; it says "${said}".`);
    expect(await page.locator('#done-title + ul li', { hasText: name }).count() === 1, `"${name}" should be listed once under Done today after a double click.`);
    expect(!(await page.locator('section:not([aria-labelledby=done-title]) li.todo-row', { hasText: name }).count()), `"${name}" should leave Late once it is done.`);
    await Promise.all([page.waitForNavigation(), page.click(`button[aria-label="Undo this tick: ${name}"]`)]);
    expect((await text('[role=status]')).startsWith('Undone.'), `Undo should say "Undone."; it says "${await text('[role=status]')}".`);
    const back = await page.locator('li.todo-row', { hasText: name }).locator('.todo-when').innerText();
    expect(back === when, `After Undo "${name}" should be back as "${when}"; it says "${back}".`);
    await goto('/to-do/year');  // This year's month summary must not widen the page (batch 21 item 98, decision 0113)
    const yearWide = await page.evaluate(() => document.documentElement.scrollWidth);
    expect(yearWide <= 320, `Things to do, This year should fit a 320 pixel phone screen; it is ${yearWide} pixels wide.`);
    const months = await page.locator('table.todo-months tbody tr').count();
    expect(months === 12, `This year should list twelve months; it lists ${months}.`);
    const label = await page.locator('table.todo-months tbody td').first().evaluate((e) => getComputedStyle(e, '::before').content);
    expect(label.includes('Due'), `At 320 pixels each month's numbers should be labelled; the first says ${label}.`);
    await page.setViewportSize({ width: 1280, height: 900 });
    ok(`Things to do: "${name}" shown once as ${when}, ticked once at 320 pixels, then undone back to the same date; This year fits 320 pixels with 12 labelled months`);
  }

  async function checkReceiptLine(r) {  // a receipt line the helper could not match (decision 0105)
    expect((await text('[data-line=waiting]')).includes(r.line), 'The unmatched receipt line should still wait after Accept all.');
    await page.setViewportSize({ width: 320, height: 800 });
    const wide = async (what) => {
      const sideways = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
      expect(sideways <= 0, `At 320px wide, ${what} scrolls sideways by ${sideways}px.`);
    };
    await wide('Review with a receipt line');
    await Promise.all([page.waitForNavigation(), page.click('[data-line=waiting] a:has-text("Choose item")')]);
    await wide('Choose item');
    const choice = await page.locator('#line-item option').evaluateAll(
      (els, name) => (els.find((e) => e.textContent.startsWith(name)) || {}).value, r.existing);
    expect(choice, `Choose item should offer ${r.existing}.`);
    await page.selectOption('#line-item', choice);
    await Promise.all([page.waitForNavigation(), page.click('button:has-text("Next")')]);
    expect(await page.inputValue('#line-amount') === r.hint, 'A hint in the item\'s own unit should fill the amount for the person to check.');
    await wide('the amount form');
    await submit('button:has-text("Save this Stock in")');
    const said = await text('[role=status]');
    expect(said.includes(`Added 1 tin of ${r.existing}`) && said.includes('from this line'), `Saving should say what the line added; Review says "${said}".`);
    await submit('button:has-text("Finish receipt review")');
    expect((await text('[role=status]')).includes('Finished this receipt'), 'Finish receipt review should close the receipt.');
    await page.setViewportSize({ width: 1280, height: 900 });
    ok(`Review: an unmatched receipt line waits after Accept all, Choose item adds 1 tin of ${r.existing} at 320px, and Finish receipt review closes it`);
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
    expect((await text('.review-group .group-label')).includes('Accepting only the Stock item leaves the Stock in waiting'), 'The group should say what accepting only the new item does.');
    await page.click(`summary:has-text("Accept ${r.rows - 1} ready rows; 1 line still needs your choice")`);
    expect((await text('details.confirm-all[open]')).includes('1 to Stock items and 1 to Stock in and out'), 'Accept all should say which lists get records.');
    await submit(`button:has-text("Yes, accept these ${r.rows - 1}")`);
    expect((await text('[role=status]')).includes('Added 1 to Stock items and 1 to Stock in and out.'), `Accept all should add the group and name what it added; Review says "${await text('[role=status]')}".`);
    ok(`Review: Accept and Reject stay in one column at 1280px and 375px; J, K and arrows move, Space ticks a whole group, A accepts, keys in a field do nothing; Accept all asks first, then adds "${r.item}" with its Stock in`);
    await checkReceiptLine(r);
  }

  async function checkQuestions() {  // Have you thought about…? (decision 0104): a record offered, a person answers
    const q = plan.questions;
    await goto('/questions/readiness');
    const before = await text('.card strong');
    const looked = Number((before.match(/^(\d+) of/) || [])[1]);
    expect(!Number.isNaN(looked), `The Questions page should start with "N of M ... looked at"; it says "${before}".`);
    expect((await html()).includes('It does not say whether your household is safe or ready.'), 'The Questions page lost its "not a safety score" caption.');
    await Promise.all([page.waitForNavigation(), page.click(`a[href="/questions/readiness/${q.id}"]`)]);
    await page.setViewportSize({ width: 320, height: 800 });
    const wide = await page.evaluate(() => document.documentElement.scrollWidth);
    expect(wide <= 321, `The question page is ${wide} pixels wide on a 320-pixel screen.`);
    await page.setViewportSize({ width: 1280, height: 800 });
    expect(await page.isVisible('text=You already recorded this. Does it answer the question?'), `"${q.id}" should offer the household's own record.`);
    expect(!(await page.isChecked(`input[name=record][value^="${q.table}:"]`)), 'The record must not be chosen before the person chooses it.');
    await page.check(`input[name=record][value^="${q.table}:"]`);
    await page.click('summary:has-text("Tell me more")');
    expect(await page.isVisible('details[open] >> text=checked'), 'Tell me more should show the source and the date it was checked.');
    await submit('button[name=answer][value=yes]');
    expect((await text('[role=status]')).includes('Saved your answer. You can change it later.'), 'Answering Yes should say "Saved your answer. You can change it later."');
    expect((await text('main')).includes('You used one of your records for this answer.'), 'The answer should say a record was used.');
    await goto('/questions/readiness');
    const after = await text('.card strong');
    expect(after.startsWith(`${looked + 1} of`), `After one Yes the count should read ${looked + 1}; it says "${after}".`);
    ok(`questions: "${q.id}" offered the household's record, Yes saved with it, count ${looked} -> ${looked + 1}, fits 320 pixels`);
  }

  async function checkCharts() {  // the first charts (decision 0109): drawn on the server, readable at 320px, keyboard reachable
    const c = plan.charts;
    await page.setViewportSize({ width: 320, height: 800 });
    try {
      await goto('/');
      await Promise.all([page.waitForNavigation(), page.click('a:has-text("What is counted")')]);
      const wide = await page.evaluate(() => document.documentElement.scrollWidth);
      expect(wide <= 320, `At 320px the drinking-water page is ${wide}px wide; it should not scroll sideways.`);
      const bars = await page.locator('svg.chart-svg a').count();
      const counted = await page.locator('table.chart-table tbody tr:not(.left-out)').count();
      expect(bars > 0 && bars <= counted, `The water chart should draw a bar for each counted item (${counted}); it drew ${bars}.`);
      const size = await page.$eval('svg.chart-svg text', (t) => t.getBoundingClientRect().height);
      expect(size >= 10, `Chart labels at 320px should stay readable; they are ${size.toFixed(1)}px tall.`);
      await page.focus('svg.chart-svg a');
      await page.keyboard.press('Enter');
      expect(/-row-\d+$/.test(page.url()), `Choosing a bar with the keyboard should go to its table row; the page is at ${page.url()}.`);
      await goto('/t/pets__pets');
      await Promise.all([page.waitForNavigation(), page.click(`a[aria-label="Open ${c.pet}"]`)]);
      const dots = await page.locator('svg.chart-svg a').count();
      const rows = await page.locator('table.chart-table tbody tr').count();
      expect(dots === c.dots && rows === c.dots, `${c.pet}'s page should show ${c.dots} weigh-in dots and ${c.dots} table rows; it shows ${dots} and ${rows}.`);
      const pwide = await page.evaluate(() => document.documentElement.scrollWidth);
      expect(pwide <= 320, `At 320px ${c.pet}'s page is ${pwide}px wide; it should not scroll sideways.`);
      ok(`charts at 320px: ${bars} water bars for ${counted} counted items, keyboard reaches a row; ${c.pet}: ${dots} dots, ${rows} rows`);
    } finally {
      await page.setViewportSize({ width: 1280, height: 720 });
    }
  }

  async function checkExitSketch() {  // the way-out sketch (decision 0118): drawn on the server, same facts as text, 320px
    const e = plan.exit;
    await page.setViewportSize({ width: 320, height: 800 });
    try {
      await goto('/set-up-home');
      await Promise.all([page.waitForNavigation(), page.click('#way-out a[href="/exit-sketch"]')]);
      const wide = await page.evaluate(() => document.documentElement.scrollWidth);
      expect(wide <= 320, `At 320px the way-out sketch page is ${wide}px wide; only the drawing should scroll sideways.`);
      const scrolls = await page.$eval('.sketch-scroll', (d) => d.scrollWidth > d.clientWidth);
      expect(scrolls, 'At 320px the drawing should scroll inside its own labelled box.');
      const ids = async (scope, what) => [...new Set(await page.$$eval(`${scope} [data-${what}]`, (els, w) => els.map((x) => x.dataset[w]), what))].sort().join(',');
      const drawnRooms = await ids('.sketch-scroll', 'room');
      const textRooms = await ids('#as-text', 'room');
      expect(drawnRooms && drawnRooms === textRooms, `The drawing's rooms (${drawnRooms}) and the text version's (${textRooms}) should be the same.`);
      const drawnLinks = await ids('.sketch-scroll', 'connection');
      const textLinks = await ids('#as-text', 'connection');
      expect(drawnLinks === textLinks, `The drawing's connections (${drawnLinks}) and the text version's (${textLinks}) should be the same.`);
      expect((await text('#as-text')).includes(e.room), `The text version should list ${e.room}.`);
      await page.focus('#read-as-text');
      await page.keyboard.press('Enter');
      expect(page.url().endsWith('#as-text'), `"Read the connections as text" should go to the text version; the page is at ${page.url()}.`);
      for (const w of e.words) expect((await text('main')).includes(w), `The sketch page should say "${w}".`);
      await Promise.all([page.waitForNavigation(), page.click('#print-a4')]);
      expect((await text('main')).includes('Page 1 of'), 'The printable sketch should number its pages.');
      const pwide = await page.evaluate(() => document.documentElement.scrollWidth);
      expect(pwide <= 320, `At 320px the printable sketch is ${pwide}px wide; it should not scroll sideways.`);
      ok(`way-out sketch at 320px: rooms ${drawnRooms} drawn and listed as text, keyboard reaches the text, sheet numbered`);
    } finally {
      await page.setViewportSize({ width: 1280, height: 720 });
    }
  }

  async function checkFeeding() {  // Pet feeding log (decision 0110): Add food at 320px, last choices shown, back to the pet
    const f = plan.feeding;
    await page.setViewportSize({ width: 320, height: 800 });
    try {
      await goto('/t/pets__pets');
      await Promise.all([page.waitForNavigation(), page.click(`a[aria-label="Open ${f.pet}"]`)]);
      expect((await text('main')).includes('Food put out today'), `${f.pet}'s page should show "Food put out today".`);
      await Promise.all([page.waitForNavigation(), page.click('a[data-add-food]')]);
      const wide = await page.evaluate(() => document.documentElement.scrollWidth);
      expect(wide <= 320, `At 320px the Add food form is ${wide}px wide; it should not scroll sideways.`);
      expect((await text('main')).includes('Filled in from a recent entry'), 'Add food should say it filled in a recent entry.');
      const amount = await page.inputValue('#f-amount');
      const when = await page.inputValue('#f-given_at');
      expect(amount === f.amount, `Add food should show the last amount (${f.amount}) for checking; it shows "${amount}".`);
      expect(/^\d{4}-\d\d-\d\dT\d\d:\d\d$/.test(when), `Add food should fill in the time now; it shows "${when}".`);
      const box = await page.locator('button[name=then][value=back]').boundingBox();
      expect(box && box.height >= 40, 'The Save button should be easy to press with one thumb (at least 40px tall).');
      await submit('button[name=then][value=back]');
      const words = await text('main');
      expect(words.includes(f.after), `After Add food, ${f.pet}'s page should say "${f.after}".`);
      const pwide = await page.evaluate(() => document.documentElement.scrollWidth);
      expect(pwide <= 320, `At 320px ${f.pet}'s page is ${pwide}px wide; it should not scroll sideways.`);
      await goto('/');
      expect((await text('main')).includes(`${f.pet} · 1 feeding recorded today`), `Home should say "${f.pet} · 1 feeding recorded today".`);
      ok(`pet feeding at 320px: Add food showed the last ${f.amount} ${f.unit}, saved, and ${f.pet}'s page and Home say so`);
    } finally {
      await page.setViewportSize({ width: 1280, height: 720 });
    }
  }

  async function checkCalendar() {  // Calendars and trends (decision 0119): month grids and range presets at 320px
    const c = plan.calendar;
    const fits = async (what) => {
      const wide = await page.evaluate(() => document.documentElement.scrollWidth);
      expect(wide <= 320, `At 320px ${what} is ${wide}px wide; it should not scroll sideways.`);
    };
    await page.setViewportSize({ width: 320, height: 800 });
    try {
      await goto('/t/pets__pets');
      await Promise.all([page.waitForNavigation(), page.click(`a[aria-label="Open ${c.pet}"]`)]);
      await fits(`${c.pet}'s page with its feeding calendar`);
      await Promise.all([page.waitForNavigation(), page.click('a:has-text("Open the feeding calendar")')]);
      await fits('the feeding calendar');
      const heads = await page.locator('table.cal thead th').count();
      expect(heads === 7, `The calendar should name 7 weekdays; it has ${heads}.`);
      const today = page.locator('table.cal td[aria-current="date"]');
      expect(await today.count() === 1, 'The calendar should mark today once.');
      const said = await today.locator('.vh').innerText();
      expect(said.includes(c.today), `Today's cell should say "${c.today}" in words; it says "${said}".`);
      const symbol = await today.locator('.cal-chip').first().innerText();
      expect(symbol.includes('●'), `A day with a feeding should show its symbol, not only a colour; it shows "${symbol}".`);
      await page.focus('table.cal td[aria-current="date"] a.cal-num');
      await page.keyboard.press('Enter');
      expect(/-d-\d{4}-\d\d-\d\d$/.test(page.url()), `Choosing a day with the keyboard should go to its words; the page is at ${page.url()}.`);
      await Promise.all([page.waitForNavigation(), page.click('a[rel=prev]')]);
      expect((await text('main')).includes('A blank day has no feeding entry recorded'), 'The previous month should say what a blank day means.');
      await goto('/to-do/calendar');
      await fits('Things to do, Calendar');
      const legend = await page.locator('.cal-legend li').count();
      expect(legend === 5, `The routines legend should explain done, skipped, due, planned and a blank day; it has ${legend} lines.`);
      await goto(`/charts/pets__weigh_ins`);
      await Promise.all([page.waitForNavigation(), page.click('.chart-ranges a:has-text("Last year")')]);
      await fits('the weights chart with a range chosen');
      expect(await page.locator('.chart-ranges a[aria-current="page"]').innerText() === 'Last year', 'Last year should be marked as chosen.');
      expect((await text('main')).includes('Since the reading before'), 'The weights page should say the change since the reading before.');
      ok(`calendars at 320px: ${c.pet}'s feeding month with today in words and a symbol, keyboard reaches the day, routines legend of 5, weights for the last year with the change in words`);
    } finally {
      await page.setViewportSize({ width: 1280, height: 720 });
    }
  }

  async function checkRunning() {  // Vehicle running log (decision 0111): a lower reading asks first, quotes behind Show
    const r = plan.running;
    await goto('/t/vehicles__vehicles');
    await Promise.all([page.waitForNavigation(), page.click(`a[aria-label="Open ${r.vehicle}"]`)]);
    const carUrl = new URL(page.url()).pathname;
    expect((await text('main')).includes(`Last recorded: ${r.last}`), `${r.vehicle}'s page should say "Last recorded: ${r.last}".`);
    await Promise.all([page.waitForNavigation(), page.click('a:has-text("Add a reading")')]);
    expect(await page.inputValue('#f-unit') === 'km', 'A new reading should start in the household\'s usual unit, km.');
    await page.fill('#f-read_at', r.at);
    await page.fill('#f-distance', r.lower);
    await Promise.all([page.waitForNavigation(), page.click('form.record button[name=then][value=back]')]);
    const asked = await text('#confirm-box');
    expect(asked.includes('This is lower than the last reading.'), `A lower reading should ask first; the page says "${asked}".`);
    await Promise.all([page.waitForNavigation(), page.click('#confirm-save')]);
    expect(new URL(page.url()).pathname === carUrl, `Save as entered should go back to ${r.vehicle}'s page; it is at ${page.url()}.`);
    expect((await text('main')).includes('3 readings recorded'), 'After Save as entered the vehicle should have 3 readings.');
    await page.setViewportSize({ width: 320, height: 800 });
    try {
      const wide = await page.evaluate(() => document.documentElement.scrollWidth);
      expect(wide <= 320, `At 320px ${r.vehicle}'s page is ${wide}px wide; it should not scroll sideways.`);
      await goto('/t/vehicles__services');
      await Promise.all([page.waitForNavigation(), page.click(`a[aria-label="Open ${r.service}"]`)]);
      expect(!(await html()).includes(r.amount), 'The service page sent an estimated cost before Show was pressed.');
      await page.click('button:has-text("Show estimated cost and scope")');
      await page.locator('#under-vehicle_running__estimates span', { hasText: r.amount }).waitFor({ timeout: 5000 }).catch(() => {});
      expect((await text('#under-vehicle_running__estimates')).includes(r.amount), 'Show estimated cost and scope did not show the quotes.');
      const swide = await page.evaluate(() => document.documentElement.scrollWidth);
      expect(swide <= 320, `At 320px the service page is ${swide}px wide; it should not scroll sideways.`);
    } finally {
      await page.setViewportSize({ width: 1280, height: 720 });
    }
    ok(`vehicle running log: a lower reading asked first, saved as entered; quotes shown only on Show; fits 320 pixels`);
  }

  async function checkDrills() {  // Think it through (decision 0108): a step, Continue later, own words behind Show
    const d = plan.drills;
    await goto('/drills/readiness');
    expect((await text('.drill-first')).includes(`first: ${d.number}`), `Think it through should name the emergency number ${d.number} first.`);
    await Promise.all([page.waitForNavigation(), page.click(`a[href="/drills/readiness/${d.scenario}"]`)]);
    expect((await text('main')).includes('Sources and local limits'), 'A drill should list its sources.');
    await submit('.drill-start button[type=submit]');
    await page.setViewportSize({ width: 320, height: 800 });
    const wide = await page.evaluate(() => document.documentElement.scrollWidth);
    expect(wide <= 321, `A drill step is ${wide} pixels wide on a 320-pixel screen.`);
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.check('input[name=choice][value=plan]');
    await page.fill('#own_words', d.words);
    await submit('button[name=action][value=later]');
    expect((await text('[role=status]')).includes('it is not marked as practised yet'), 'Continue later should say it is not marked as practised.');
    await submit('.drill-start button[type=submit]');
    expect((await text('main')).includes(d.record), `Step 2 should offer the household's own record "${d.record}".`);
    expect(!(await page.isChecked('input[name=record]:not([value=""])')), 'A record must not be chosen before the person chooses it.');
    for (let step = 2; step <= d.steps; step++) {
      await page.check('input[name=choice][value=check]');
      await submit('button[name=action][value=next]');
    }
    await submit('button:text-is("Save this practice")');
    expect((await text('[role=status]')).startsWith('Practised on'), 'Saving the practice should confirm "Practised on … · Look again on …".');
    expect(!(await html()).includes(d.words), 'The practice page sent the household\'s own words before Show was pressed.');
    await page.locator('button.secret').first().click();
    await page.locator('span', { hasText: d.words }).waitFor({ timeout: 5000 }).catch(() => {});
    expect((await text('main')).includes(d.words), 'Pressing Show did not show the household\'s own words.');
    ok(`drills: "${d.scenario}" names ${d.number}, Continue later is not practised, "${d.record}" offered not chosen, saved with own words behind Show, fits 320 pixels`);
  }

  async function checkBills() {  // Bills and insurance (decision 0117): nothing moves until chosen; Move, then Transfer back
    const b = plan.bills;
    await goto('/t/bills_insurance__commitments');
    expect((await text('#moves-choice')).includes(b.title), `The Bills list should say "${b.title}" before anything moves.`);
    let attention = (await (await page.goto(base + '/attention')).text());
    expect(attention.includes(b.earlier), `Before a choice, Needs attention should still remind about "${b.earlier}" from Vehicles.`);
    await goto('/t/bills_insurance__commitments');
    await submit('#moves-review');
    await page.setViewportSize({ width: 320, height: 800 });
    try {
      const wide = await page.evaluate(() => document.documentElement.scrollWidth);
      expect(wide <= 320, `At 320px Review and move is ${wide}px wide; it should not scroll sideways.`);
      expect((await text('main')).includes('permanent ID'), 'Review and move should show each record\'s permanent ID.');
      await submit('button[data-move]');
      expect((await text('#moves-done')).includes(b.done), `After Move the page should say "${b.done}".`);
    } finally {
      await page.setViewportSize({ width: 1280, height: 720 });
    }
    attention = await (await page.goto(base + '/attention')).text();
    expect(!attention.includes(b.earlier), `After Move, Needs attention still reminds about "${b.earlier}" from Vehicles.`);
    expect(attention.includes(b.name), `After Move, Needs attention should remind about "${b.name}" from Bills.`);
    await goto('/t/vehicles__insurance');
    await Promise.all([page.waitForNavigation(), page.click(`a[aria-label="Open ${b.earlier}"]`)]);
    expect((await text('[data-reminder="source_moved"]')).includes('Insurance reminder is in Bills and insurance'),
      'The earlier Vehicle insurance record should say its reminder is in Bills and insurance.');
    await submit('[data-reminder="source_moved"] button[data-reminder-button]');
    attention = await (await page.goto(base + '/attention')).text();
    expect(attention.includes(b.earlier), `After Transfer back, Needs attention should remind about "${b.earlier}" from Vehicles again.`);
    ok(`bills: "${b.earlier}" stays in Vehicles until chosen, moves to Bills with one reminder, fits 320px, and Transfer back returns it`);
  }

  async function switchModule(name, on) {  // Settings: tick or untick one module, then Save settings
    await goto('/settings');
    await page.setChecked(`input[name=modules][value=${name}]`, on);
    await submit('button[type=submit]:has-text("Save settings")');
  }

  async function checkOptionalLink() {  // Utilities with Our home off (decision 0115): the meter link is kept, unseen
    const o = plan.optional;
    await switchModule('home_layout', false);
    await goto('/t/utilities__services');
    let words = await text('main');
    expect(words.includes(o.kept), `With Our home off, the Utilities list should say "${o.kept}".`);
    expect(!(await html()).includes(o.meter), `With Our home off, the Utilities list still names the meter "${o.meter}".`);
    await page.setViewportSize({ width: 320, height: 800 });
    try {
      await Promise.all([page.waitForNavigation(), page.click(`a[aria-label="Open ${o.service}"]`)]);
      const recordUrl = new URL(page.url()).pathname;
      expect(!(await page.locator('select[name=meter]').count()), 'With Our home off, the service still offers a meter picker.');
      expect((await text('#f-meter-note')) === o.keptHelp, `The service should say "${o.keptHelp}" where the picker was.`);
      const wide = await page.evaluate(() => document.documentElement.scrollWidth);
      expect(wide <= 320, `At 320px the service page is ${wide}px wide; it should not scroll sideways.`);
      await page.focus('#f-name');
      let reached = false;
      for (let i = 0; i < 30 && !reached; i++) {
        await page.keyboard.press('Tab');
        const at = await page.evaluate(() => document.activeElement && (document.activeElement.id || document.activeElement.textContent));
        if (at === 'f-meter-note') reached = true;
        if (at && at.includes('Save changes')) break;
      }
      expect(reached, 'The keyboard should reach the saved-link words before Save changes.');
      await page.fill('#f-name', `${o.service} (checked)`);
      await submit('button[type=submit]:has-text("Save changes")');
      await goto(recordUrl);
      expect((await text('#f-meter-note')) === o.keptHelp, 'Saving another field should keep the saved meter link.');
      await goto('/t/utilities__services/new');
      expect((await text('#f-meter-note')) === o.offHelp, `A new service should say "${o.offHelp}" before Save.`);
      const nwide = await page.evaluate(() => document.documentElement.scrollWidth);
      expect(nwide <= 320, `At 320px the new service form is ${nwide}px wide; it should not scroll sideways.`);
    } finally {
      await page.setViewportSize({ width: 1280, height: 720 });
    }
    await switchModule('home_layout', true);
    await goto('/t/utilities__services');
    words = await text('main');
    expect(words.includes(o.meter), `With Our home on again, the service should show its same meter "${o.meter}".`);
    ok(`optional link: with Our home off "${o.service}" keeps its meter link unseen, fits 320px, keyboard reaches the words; on again it shows "${o.meter}"`);
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
      if (plan.routine) await checkThingsToDo();
      if (plan.csv) await checkImport();
      if (plan.review) await checkReview();
      if (plan.questions) await checkQuestions();
      if (plan.charts) await checkCharts();
      if (plan.exit) await checkExitSketch();
      if (plan.feeding) await checkFeeding();
      if (plan.calendar) await checkCalendar();
      if (plan.running) await checkRunning();
      if (plan.drills) await checkDrills();
      if (plan.bills) await checkBills();
      if (plan.optional) await checkOptionalLink();
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
