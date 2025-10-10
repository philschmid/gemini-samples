// npm init -y
// npm install @browserbasehq/stagehand
// npx playwright install
// node gemini-stagehand.js

import { Stagehand } from "@browserbasehq/stagehand";

const stagehand = new Stagehand({
    env: "LOCAL",
	localBrowserLaunchOptions: {
		headless: false, // Show browser window
		viewport: { width: 1280, height: 720 },
		executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', // Custom Chrome path
	},
	verbose: 1, // 0 = errors only, 1 = info, 2 = debug
  });

// Initialize Stagehand (launches browser) and navigate to a page
await stagehand.init()
await stagehand.page.goto("https://ai.google.dev/gemini-api/docs");

// Create an agent with Gemini-2.5 Computer Use Preview model
const agent = stagehand.agent({
    provider: "google",
    model: "gemini-2.5-computer-use-preview-10-2025",
	instructions: `You are a helpful assistant that can use a web browser.
Do not ask follow up questions, the user will trust your judgement.`,
    options: {
      apiKey: process.env.GEMINI_API_KEY,
    },
	
})

// Execute the agent
const res = await agent.execute("What is the latest Gemini version?");
console.log("Agent response:", res);

// Close the browser and cleanup
await stagehand.close()