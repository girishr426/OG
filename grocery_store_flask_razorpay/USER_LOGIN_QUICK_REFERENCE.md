# User Login System - Quick Start

## User Registration & Login Endpoints

### Registration
- **URL**: `/user/register`
- **Steps**: 
  1. Click "Register" in header
  2. Fill form with: Email, Full Name, Phone (optional), Password
  3. Click Register
  4. Redirected to login page

### Login
- **URL**: `/user/login`
- **Steps**:
  1. Click "Login" in header
  2. Enter email and password
  3. Click Login
  4. Session active for 30 days

## User Required Data for Ordering

### At Signup:
- ✅ Email (required, unique)
- ✅ Full Name (required)
- ✅ Password (required, 6+ characters)
- ✅ Phone (recommended)

### In Profile (optional at signup):
- Address
- City
- Pincode

### At Checkout (if not logged in):
All of above required to place order

## User Features

| Feature | URL | Description |
|---------|-----|-------------|
| Register | `/user/register` | Create new account |
| Login | `/user/login` | Sign in to account |
| Profile | `/user/profile` | View & update details |
| Orders | `/user/orders` | See order history |
| Logout | `/user/logout` | Sign out |

## Checkout Benefits When Logged In

✅ Auto-filled delivery details  
✅ No need to re-enter information  
✅ Faster checkout (1 click instead of typing)  
✅ Order history available  
✅ Session persists for 30 days  

## User Header Navigation

### When NOT Logged In:
```
Home | Cart | Login | Register | Admin
```

### When Logged In:
```
Home | Cart | 👤 John Doe | Profile | Orders | Logout | Admin
```

## Database - Users Table

```
id          → User ID (auto)
email       → Login email (unique)
password_hash → Hashed password
full_name   → User's name
phone       → Contact number
address     → Street address
city        → City name
pincode     → Postal code
created_at  → Registration date
updated_at  → Last modified
```

## Session Storage

After login, user info saved in session (not password!):
```python
session['user_logged_in'] = True
session['user_id'] = 1
session['user_email'] = 'john@example.com'
session['user_name'] = 'John Doe'
```

## Flow Diagram

```
┌─────────────┐
│ New Visitor │
└──────┬──────┘
       │
       ├─→ Register → Create Account
       │   
       ├─→ Login → Start Session
       │   
       └─→ Browse & Add to Cart
            │
            ↓
       ┌──────────────┐
       │   Checkout   │
       └──────┬───────┘
              │
       ┌──────┴──────┐
       │             │
    Logged In    Not Logged In
       │             │
       ↓             ↓
   Auto-fill    Enter details
   Pre-filled   manually
   delivery
       │
       ↓
  ┌─────────┐
  │ Payment │
  └────┬────┘
       │
       ↓
  ┌──────────────┐
  │ Order placed │
  │ View in      │
  │ "My Orders"  │
  └──────────────┘
```

## Required Data Summary

### Registration Data:
- Email ✅ (required)
- Password ✅ (required)
- Full Name ✅ (required)
- Phone (optional but recommended)

### Checkout Data (if logged in):
- Pre-filled from profile
- User can edit before payment
- Address, Phone, Name can be modified

### Checkout Data (if NOT logged in):
- Must enter: Name, Email, Phone, Address, City, Pincode
- All fields required
- Option to register after checkout

## Test Credentials

After first run, you can create test user:
- Email: `test@example.com`
- Password: `test123`
- Name: `Test User`

Or register through UI at `/user/register`

## Common Tasks

### Change user password:
Currently not available in UI. To reset:
1. Access database: `sqlite3 store.db`
2. Get user hash from database
3. Ask user to use forgot password (TODO)

### Delete user account:
Currently not available in UI. Admin access to database needed.

### See all users:
```bash
sqlite3 store.db "SELECT id, email, full_name, phone FROM users;"
```

### See user orders:
```bash
sqlite3 store.db "SELECT * FROM orders WHERE email='user@example.com';"
```
