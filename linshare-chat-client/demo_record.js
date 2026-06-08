// Records a demo of the LinShare MCP "attach + share" use case.
// Attaches Contrat.pdf, asks the assistant to share it, waits for confirmation.
const { chromium } = require('playwright');

const PDF = '/home/walidboudiche/Téléchargements/LinShareUploads/Contrat.pdf';
const PROMPT = 'Partage ce contrat avec amy.wolsh@linshare.org';
const OUT_DIR = '/home/walidboudiche/working/linshare-mcp/demo-video';
const URL = 'http://127.0.0.1:8000/';

const sleep = (ms) => new Promise(r => setTimeout(r, ms));

async function waitForText(page, regex, timeoutMs, label) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    const txt = await page.evaluate(() => document.body.innerText);
    if (regex.test(txt)) { console.log(`✓ ${label}`); return txt; }
    if (/❌|Connection Failed|Transcription failed/i.test(txt) && label !== 'error') {
      console.log(`⚠️ error-like text on page while waiting for ${label}`);
    }
    await sleep(1000);
  }
  throw new Error(`timeout waiting for ${label}`);
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1280, height: 820 },
    recordVideo: { dir: OUT_DIR, size: { width: 1280, height: 820 } },
  });
  const page = await context.newPage();
  let videoPath;
  try {
    console.log('→ navigating');
    await page.goto(URL, { waitUntil: 'domcontentloaded' });

    // Wait for the assistant welcome + composer to be ready.
    await waitForText(page, /ready to help|manage your files/i, 60000, 'welcome message');
    await page.waitForSelector('#chat-input', { timeout: 20000 });
    await sleep(2500); // let the viewer settle on the welcome screen

    // 1. Attach the contract (staged into the composer).
    console.log('→ attaching PDF');
    await page.setInputFiles('#upload-button-input', PDF);
    // Wait for the attachment chip to render in the composer.
    await waitForText(page, /Contrat\.pdf/i, 20000, 'attachment chip');
    await sleep(2000);

    // 2. Type the request, char-by-char for a natural feel.
    console.log('→ typing prompt');
    await page.click('#chat-input');
    await page.type('#chat-input', PROMPT, { delay: 55 });
    await sleep(1200);

    // 3. Send.
    console.log('→ sending');
    await page.keyboard.press('Enter');

    // 4. Wait for the upload to complete (unambiguous text, not in the user prompt).
    await waitForText(page, /Successfully uploaded Contrat\.pdf/i, 120000, 'upload done');

    // 5. Wait for the assistant to finish generating: poll page text until it
    //    stops changing for several seconds (the streamed final answer settled).
    console.log('→ waiting for assistant to finish');
    const settleStart = Date.now();
    let last = '', stableFor = 0, sawShare = false;
    while (Date.now() - settleStart < 200000) {
      const txt = await page.evaluate(() => document.body.innerText);
      if (/Shared Successfully|partag|shared|lien|envoy/i.test(txt.replace(PROMPT, ''))) sawShare = true;
      if (txt === last) { stableFor += 1; } else { stableFor = 0; last = txt; }
      // Require: upload + a share-ish word seen + text unchanged for 5s.
      if (sawShare && stableFor >= 5) { console.log('✓ assistant finished'); break; }
      await sleep(1000);
    }

    // Hold on the final confirmation a beat for the viewer.
    await sleep(4000);
    console.log('✓ flow complete');
  } catch (e) {
    console.error('✗ FAILED:', e.message);
    try { await page.screenshot({ path: OUT_DIR + '/failure.png' }); } catch {}
    process.exitCode = 1;
  } finally {
    videoPath = await page.video().path().catch(() => null);
    await context.close(); // flushes the video file
    await browser.close();
    if (videoPath) console.log('VIDEO:' + videoPath);
  }
})();
