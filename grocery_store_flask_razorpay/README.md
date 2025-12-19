# Organic Gut Point (Flask) — Razorpay Ready

Minimal grocery ordering website with **Flask + SQLite** and **Razorpay** checkout.

## Features
- Browse products, add to cart, checkout
- **Razorpay Standard Checkout** with server-side **Orders API** & **signature verification**
- Admin: add/update/delete products, price, stock, and **estimated delivery** (days or date)
- View orders and update payment status & estimated delivery

## Quickstart

1. **Create a virtual environment**
```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Set environment variables**

Option A — Use `.env` file (recommended for local dev)

```bash
cp data/env.example data/.env   # Windows PowerShell: Copy-Item data/env.example data/.env
# Then edit data/.env and set your secrets, e.g.:
# APP_SECRET_KEY=replace_with_random
# RAZORPAY_KEY_ID=rzp_test_xxxxx
# RAZORPAY_KEY_SECRET=xxxxx
# RAZORPAY_WEBHOOK_SECRET=your_webhook_secret
# ADMIN_DEFAULT_PASSWORD=your_admin_password
```

Option B — Export in shell

macOS/Linux (bash/zsh):
```bash
export APP_SECRET_KEY=replace_with_random
export RAZORPAY_KEY_ID=rzp_test_xxxxx
export RAZORPAY_KEY_SECRET=xxxxx
export RAZORPAY_WEBHOOK_SECRET=your_webhook_secret
export ADMIN_DEFAULT_PASSWORD=your_admin_password
```

Windows PowerShell:
```powershell
$env:APP_SECRET_KEY = "replace_with_random"
$env:RAZORPAY_KEY_ID = "rzp_test_xxxxx"
$env:RAZORPAY_KEY_SECRET = "xxxxx"
$env:RAZORPAY_WEBHOOK_SECRET = "your_webhook_secret"
$env:ADMIN_DEFAULT_PASSWORD = "your_admin_password"
```

4. **Run**
```bash
python app.py
```
Open http://127.0.0.1:5000

## Razorpay Integration
- **Create Order** on server and pass `order_id` to Checkout. (Standard checkout steps) [Docs] (
https://razorpay.com/docs/payments/payment-gateway/web-integration/standard/integration-steps/) 
- **Orders API** (create/fetch/update) — server-side [Docs] (
https://razorpay.com/docs/api/orders/create/ ; https://razorpay.com/docs/payments/orders/apis/)
- **Verify Payment Signature** on server using HMAC SHA-256 of `order_id|payment_id`. [Docs] (
https://razorpay.com/docs/payments/payment-gateway/web-integration/standard/build-integration/)
- **Webhooks**: validate `X-Razorpay-Signature` using the **raw** request body. [Docs] (
https://razorpay.com/docs/webhooks/ ; https://razorpay.com/docs/webhooks/validate-test/)
- **Test vs Live**: use **Test** keys during development; switch to **Live** after activation. [Docs] (
https://razorpay.com/docs/payments/dashboard/test-live-modes/ ; https://razorpay.com/docs/api/authentication/)

## WordPress (WooCommerce) Deployment Plan
If you prefer WordPress in production, migrate products via CSV and use the official plugin:
- **Razorpay for WooCommerce** (WordPress plugin) [Docs] (
https://wordpress.org/plugins/woo-razorpay/ ; https://razorpay.com/docs/payments/payment-gateway/ecommerce-plugins/woocommerce/)
- **Import products via CSV** (WooCommerce) [Docs] (
https://woocommerce.com/document/product-csv-importer-exporter/)
- For **Estimated Delivery**, add custom fields (ACF) and render via Woo hooks. [Docs] (
https://wordpress.org/plugins/advanced-custom-fields/ ; https://woocommerce.com/document/custom-product-fields/)

## Notes
- Amounts passed to Razorpay are in **paise** (smallest unit).
- Payment capture can be centrally configured in the Dashboard. [Docs] (
https://razorpay.com/docs/payments/payment-gateway/web-integration/standard/best-practices/)
- Use HTTPS and secure secrets.
- Default admin user: username `admin`, password is taken from `ADMIN_DEFAULT_PASSWORD`.
	- If not set, the app will generate a random password on first run and print it to the console.

## License
MIT
