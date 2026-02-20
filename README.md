## 1. Behavioral & UX Metrics (The "Friction" Factors)
These metrics measure how hard the website makes the user work to give them money. High friction usually correlates with a "Bad" categorization.

Click Depth to Checkout: How many clicks from the homepage to the payment screen. (Ideal is 2-4).

Popup/Interstitial Count: How many times the bot has to close an overlay, cookie banner, or newsletter prompt.

Guest Checkout Availability: Does the site force you to create an account to buy? (Forced accounts are a major friction point).

Cart Persistence: If you add an item, close the browser, and reopen it, is the item still in the cart?

How to collect it: Playwright. You will use scripts similar to the ones we just built to automate a headless browser, navigate the site, count popups, check for "Guest Checkout" buttons, and manage browser cookies to test cart persistence.

## 2. Performance Metrics (The "Frustration" Factors)
If a site is slow or jumpy, users leave. Google's Core Web Vitals are the industry standard for this.

Largest Contentful Paint (LCP): How long it takes for the main product image to load. (Good: Under 2.5s).

Cumulative Layout Shift (CLS): How much the page visually "jumps" as it loads. A high CLS means a user might accidentally click the wrong button. (Good: Under 0.1).

Total Blocking Time (TBT): How long the page is frozen by background scripts while loading.

Time to First Byte (TTFB): Server response time.

How to collect it: Google PageSpeed Insights API (often referred to as the Lighthouse API). You pass the URL to the API via Python's requests library, and it returns a JSON file with all these exact numbers.

## 3. Functional Features (The "Usability" Factors)
These features test if the modern conveniences of e-commerce are present and working.

Search Bar Auto-Suggest: When typing in the search bar, does a dropdown appear with suggestions?

Quick Buy / Buy Now Buttons: Does the site allow bypassing the cart entirely to go straight to checkout?

Broken Link Rate (404s): When clicking random product categories, do any return an error?

Mobile Responsiveness: Does the site render correctly on a phone screen?

How to collect it: Playwright. You can configure Playwright to simulate a mobile device viewport (like an iPhone 14) and check if elements overlap. You can also use Playwright to type into the search bar and check if an auto-suggest <div> appears.

## 4. Trust & Legality Signals (The "Legitimacy" Factors)
Scam sites and dropshipping operations that spin up overnight often lack foundational business information.

Contact Information: Presence of a physical address, customer support email, and phone number.

Policy Pages: Presence of links to "Return Policy", "Privacy Policy", and "Terms of Service" in the footer.

Social Proof: Presence of active social media links (Instagram, Facebook) or integrated customer reviews.

Payment Trust Badges: Logos for Visa, Mastercard, PayPal, or security seals like Norton/McAfee.

How to collect it: BeautifulSoup or Playwright. You can scrape the raw HTML of the homepage and footer, searching for keywords like "Returns" or regex patterns that match email addresses and phone numbers.

## 5. Visual Quality (The "Aesthetic" Factors)
The visual appeal and layout of a website heavily influence a user's trust.

Clutter vs. Whitespace: Is the screen crammed with text and low-quality images, or is it clean?

Image Quality: Are the product images high-resolution or pixelated?

Text-to-Image Ratio: Does the page rely on actual HTML text, or is text baked directly into images (a common tactic for cheap, low-effort sites)?

How to collect it: Playwright + A Vision Model. You use Playwright to take a full-page screenshot and pass that image to a Vision AI (like Gemini Pro Vision). You can prompt the AI to return a JSON payload rating the UI from 1-10 on metrics like clutter, modern design, and image quality.

## Bringing It All Together
To build your dataset, your Python script will eventually look like a pipeline that does this for every URL:

Calls the Lighthouse API to get Performance scores.

Uses BeautifulSoup to scrape the HTML for Trust signals.

Launches Playwright to simulate a user buying a product (Behavioral/Functional).

Takes a screenshot with Playwright and sends it to a Vision Model (Visual).

Compiles all these features into a single row in a Pandas DataFrame (e.g., click_depth: 3, LCP: 1.2, has_return_policy: True, popup_count: 1).