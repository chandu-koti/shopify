# Deployment & Integration Guide: Shopify ZIP Code Based Pricing Demo

This guide provides step-by-step instructions for deploying and integrating the dynamic ZIP-code product pricing solution from scratch. It is designed for Solutions Engineers and developers deploying to development and production environments.

---

## Architecture Overview
*   **Frontend**: Shopify Theme App Extension (Online Store 2.0 App Block) in JavaScript/Liquid.
*   **Backend**: Python FastAPI service running programmatically on Render (or via Docker).
*   **Data Protocol**: Stateless HTTPS requests containing a correlation `request_id` UUID.

---

## 1. Shopify Partner Account Setup

The Shopify Partner account is required to create development stores, register apps, and publish Theme App Extensions.

1.  Navigate to [Shopify Partners](https://partners.shopify.com/) and click **Join now**.
2.  Fill in the organization profile and select **App Developer** as the primary focus.
3.  **Validation Checkpoint**: Verify access to the Partners Dashboard at `https://partners.shopify.com/<partner_id>/home`.
4.  **Common Failure Scenarios**:
    *   *Scenario*: Creating a standard store account instead of a Partner account.
    *   *Solution*: Ensure you join through the `/partners` URL to access developer tools.

---

## 2. Shopify Development Store Setup

Development stores are free sandbox environments utilized for testing theme integrations and applications.

1.  In your **Partner Dashboard**, click **Stores** in the left sidebar.
2.  Click **Add store** > **Create development store**.
3.  Select **Create a store for testing and previewing B2B** or **Create a store with test data**.
4.  Enter a unique store name (e.g., `zip-pricing-demo-store`).
5.  **Validation Checkpoint**: Confirm you can log into the store's admin panel at `https://admin.shopify.com/store/zip-pricing-demo-store`.
6.  **Common Failure Scenarios**:
    *   *Scenario*: Store is created with password protection, blocking storefront tests.
    *   *Solution*: In Admin, navigate to **Online Store** > **Preferences** > **Password protection**, and disable it (or copy the storefront password for local browsing).

---

## 3. Sample Product Creation

We require at least one sample product to bind our Liquid pricing app block.

1.  In the store Admin, go to **Products** > **Add product**.
2.  Enter details:
    *   **Title**: `Dynamic Premium Sneaker`
    *   **Price**: `$1,999.00`
    *   **Status**: `Active`
    *   **Inventory**: Set quantity to `50` (in stock).
3.  **Validation Checkpoint**: Capture the **Product ID** from the admin URL when viewing the product:
    *   URL format: `https://admin.shopify.com/store/zip-pricing-demo-store/products/8729384910283`
    *   Product ID: `8729384910283`
4.  **Common Failure Scenarios**:
    *   *Scenario*: Product is set as draft, causing 404 on storefront.
    *   *Solution*: Set status to **Active** and verify it appears under the default Catalog page.

---

## 4. Shopify CLI Installation

Shopify CLI is used to build, preview, and deploy apps and extensions.

### Commands
Initialize Shopify CLI globally using your package manager:
```bash
npm install -g @shopify/cli @shopify/theme
```

### Verification Command
Ensure CLI is properly installed:
```bash
shopify version
```
*Expected Output:*
```
@shopify/cli/3.x.x win32-x64 node-v20.x.x
```

### Validation Checkpoint
Run the login command to authenticate the CLI with your Partner Account:
```bash
shopify auth login
```
*Expected Output:* Launches a web browser prompting for Shopify Partners credentials.

---

## 5. Shopify App Creation

Theme App Extensions must belong to a Shopify App container registered in the Partner Dashboard.

### Commands
In your project directory, run:
```bash
shopify app init
```
1.  **Project Name**: `zip-pricing-app`
2.  **Template**: Select `Start with an extension-only project` (or any boilerplate).
3.  Navigate into the created folder:
    ```bash
    cd zip-pricing-app
    ```
4.  **Validation Checkpoint**: Ensure a `shopify.app.toml` config file is created at the app root directory.

---

## 6. Theme App Extension Registration

Now we register the theme app extension within the project directory.

### Commands
Generate the extension template files:
```bash
shopify app generate extension
```
1.  **Type of extension**: Select `Theme app extension`.
2.  **Name of extension**: `ZIP Pricing Extension`.
3.  This creates the `/extensions/zip-pricing-extension` folder. Replace its files with the files provided in the `theme-extension/` directory of this repository:
    *   Copy contents of `theme-extension/shopify.extension.toml` to `extensions/zip-pricing-extension/shopify.extension.toml`.
    *   Copy assets and blocks to their respective folders.

---

## 7. Extension Deployment

Deploy the Theme App Extension code to the Shopify Partners platform so it becomes available in your store customizer.

### Commands
Within your app folder, run:
```bash
shopify app deploy
```

### Expected Output
```
Releasing version 1.0.0 of ZIP Pricing Extension...
✔ ZIP Pricing Extension deployed to Shopify Partners.
```

### Validation Checkpoint
1.  Go to **Partners Dashboard** > **Apps** > **zip-pricing-app** > **Extensions**.
2.  Verify **ZIP Pricing Extension** shows a status of `Live` with version `1.0.0`.
3.  Go to the Development Store Admin > **Online Store** > **Themes** > **Customize** on your active theme (e.g. Dawn).
4.  Navigate to a product page inside the editor, click **Add block** in the sidebar, and confirm the **ZIP Code Product Pricing** block is visible.

---

## 8. Render Deployment for FastAPI Backend

Render connects to your GitHub repository to build and host the Python FastAPI server.

### Simple Render Native Python Setup (Recommended)
1.  Sign in to [Render](https://render.com/).
2.  Click **New** > **Web Service**.
3.  Connect your GitHub repository containing the `/backend` folder.
4.  Configure the settings:
    *   **Name**: `shopify-zip-pricing-api`
    *   **Runtime**: `Python`
    *   **Root Directory**: `backend` (Points Render to the backend sub-folder)
    *   **Build Command**: `pip install -r requirements.txt`
    *   **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
    *   **Instance Type**: `Free` (or higher)
5.  Click **Create Web Service**.

### Validation Checkpoint
Wait for the deployment to log `Your service is live`. Navigate to the service public URL:
*   `https://shopify-zip-pricing-api.onrender.com/health`
*   *Expected Response (JSON)*: `{"status": "healthy"}`

---

## 9. Environment Variables Configuration

Set environment variables on Render to control network behaviors and CORS configurations.

1.  In the Render Dashboard, click your Web Service and navigate to **Environment**.
2.  Add the following keys:
    *   `ENV`: `production`
    *   `ALLOWED_ORIGINS`: `https://zip-pricing-demo-store.myshopify.com` (Replace with your actual store domain. To support multiple storefronts, use a comma-separated list).
3.  Click **Save Changes**. Render will trigger an automatic zero-downtime redeployment.

---

## 10. CORS Configuration

CORS settings block unauthorized cross-origin requests.

*   **Local Development**: When `ENV` is `development` and `ALLOWED_ORIGINS` is default `*`, requests are accepted from all storefront origins.
*   **Production Checkpoint**: Ensure the `ALLOWED_ORIGINS` value matches your Shopify custom domain exactly. If the storefront domain is `https://my-custom-shop.com`, the API environment variable must match that URL (excluding the trailing slash).

---

## 11. Connecting Theme Extension to Render API URL

1.  Go to the Development Store Admin > **Online Store** > **Themes** > **Customize**.
2.  Select **ZIP Code Product Pricing** app block from your layout.
3.  In the settings panel, replace the default **FastAPI Server Base URL** (`http://127.0.0.1:8000`) with your production Render URL (e.g., `https://shopify-zip-pricing-api.onrender.com`).
4.  Click **Save** in the top-right corner of the Customizer.

---

## 12. Local Testing Workflow

Test end-to-end pricing lookups locally on your machine before pushing to production.

### Step 1: Start Local FastAPI Server
In the `backend/` directory:
```bash
.venv\Scripts\uvicorn app.main:app --reload --port 8000
```
Confirm server logs show:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

### Step 2: Boot Shopify CLI local dev preview
In your Shopify App directory:
```bash
shopify app dev
```
*   Select your Partner Organization.
*   Select your Development Store.
*   Shopify CLI will output a local preview storefront link: `https://zip-pricing-demo-store.myshopify.com/?preview_theme_id=xxxx`.

### Step 3: Trigger Lookups
1.  Navigate to the preview link, open your sample product page.
2.  Ensure the "FastAPI Server Base URL" in the Customize Editor block settings is set to local dev: `http://127.0.0.1:8000`.
3.  Open browser developer console (`F12`).
4.  Enter ZIP `75028` and click **Check Price**.
5.  *Expected UI Output*: Price text transitions to `$1,499.00`. Success banner appears.
6.  *Expected Console Output*: API call logged with a UUID `request_id`.
7.  *Expected Server Logs*:
    ```
    [b3b29c12-38d5-45be-91b5-1cf5dfd0c9f1] Querying dynamic pricing for product_id=8729384910283, zip_code='75028'
    [b3b29c12-38d5-45be-91b5-1cf5dfd0c9f1] Custom price applied: $1,499.00 for ZIP 75028
    ```

---

## 13. Production Testing Workflow

Verify that the live Render API is communicating properly with the storefront.

1.  Navigate to your live Shopify store product page.
2.  Verify the dynamic price widget is visible.
3.  Enter unmapped ZIP `44101` and click **Check Price**.
    *   *Expected UI*: Standalone Polaris banner displays `Standard pricing applies for your region.`, and the main storefront price does not alter.
4.  Enter valid ZIP `10001` and click **Check Price**.
    *   *Expected UI*: Storefront price updates to `$1,699.00` with a smooth fade animation. Success banner displays.
5.  Enter invalid ZIP `12abc` and click **Check Price**.
    *   *Expected UI*: Warning label `Please enter a valid 5-digit US ZIP code.` is displayed inline under the input field. No API request is sent.

---

## 14. Troubleshooting Guide

| Issue | Common Cause | Diagnostic Step | Resolution |
| :--- | :--- | :--- | :--- |
| **CORS Blocked Error** | Server rejected origin domain. | Open browser console; look for Access-Control-Allow-Origin error. | Update Render `ALLOWED_ORIGINS` env var to match active shop domain. |
| **Price element not updating** | Selector mismatch. | Inspect your theme's price element tag in the browser. | Add the selector class (e.g. `.price-item--regular`) to the block's **Custom Price Element CSS Selector** in theme settings. |
| **Widget loading spinner hangs** | Backend service went cold. | Ping `https://your-service.onrender.com/health` in browser. | Render free tier service spins down after 15m inactivity. Wait 1 min for backend container to spin up. |
| **422 Unprocessable Entity** | Invalid request payload. | Check backend logs using the logged `request_id` correlation UUID. | Ensure payload attributes match Pydantic schema types (Product ID must be integer, ZIP must be 5-digit string). |
| **Price resets on page reload** | Stateless behavior. | Refresh storefront page. | Expected behavior. The design is stateless to protect customer privacy. |
| **Missing CSS/JS assets** | Asset compilation delay. | Inspect console for asset download HTTP 404 errors. | Run `shopify app deploy` to redeploy theme block assets. |
