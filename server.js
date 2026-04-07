const express = require("express");
const { chromium } = require("playwright");

const app = express();
app.use(express.json({ limit: "1mb" }));

let browser = null;

async function getBrowser() {
  if (!browser || !browser.isConnected()) {
    browser = await chromium.launch({
      headless: true,
      args: ["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
    });
  }
  return browser;
}

function errorMessage(err) {
  const text = String(err || "").trim();
  if (!text) return err?.name || "Error";
  return text.split("\n", 1)[0].trim();
}

app.get("/health", (req, res) => {
  res.json({ status: "ok" });
});

app.post("/", async (req, res) => {
  const { url } = req.body || {};
  if (!url || typeof url !== "string" || !url.trim()) {
    return res.status(400).json({ success: false, error: "Missing or invalid 'url' field" });
  }

  let page;
  try {
    const runningBrowser = await getBrowser();
    page = await runningBrowser.newPage();
    await page.goto(url.trim(), { waitUntil: "networkidle", timeout: 60000 });
    const imageBuffer = await page.screenshot({ type: "png", fullPage: true });
    return res.json({ image: imageBuffer.toString("base64"), success: true });
  } catch (err) {
    const msg = errorMessage(err);
    if (msg.toLowerCase().includes("timeout")) {
      return res.status(502).json({ success: false, error: `Page load timed out: ${msg}` });
    }
    return res.status(502).json({ success: false, error: msg });
  } finally {
    if (page) await page.close();
  }
});

const port = Number(process.env.PORT || 10000);
if (require.main === module) {
  app.listen(port, "0.0.0.0", () => {
    console.log(`Listening on ${port}`);
  });
}

module.exports = app;
