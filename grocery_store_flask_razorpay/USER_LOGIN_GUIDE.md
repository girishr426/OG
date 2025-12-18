# User Login & Registration System

## Overview
Added complete user authentication system for customers to register, log in, and track their orders. Users can save their delivery details for faster checkout.

## Features

### 1. **User Registration**
- Email-based sign up
- Password validation (min 6 characters)
- Phone number optional but recommended
- Full name required
- Account verification via email (optional enhancement)

### 2. **User Login**
- Email and password authentication
- Persistent session (stays logged in)
- "Welcome back" message
- Secure password hashing

### 3. **User Profile**
- Save/update delivery information
- Full name, phone, address, city, pincode
- Email display (cannot be changed)
- One-click profile updates

### 4. **Order History**
- View all past orders
- Order status display (Paid/Pending/Failed)
- Order totals
- Estimated delivery dates
- Click to view order details

### 5. **Checkout Integration**
- Auto-fill delivery details if logged in
- No need to re-enter information every time
- Faster checkout process
- Option to register during checkout

## Database Schema

### Users Table
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL,
    phone TEXT,
    address TEXT,
    city TEXT,
    pincode TEXT,
    created_at TEXT,
    updated_at TEXT
)
```

## User Data Required for Ordering

| Field | Required | Purpose |
|-------|----------|---------|
| Email | ✅ Yes | Unique ID & order notifications |
| Full Name | ✅ Yes | Delivery label |
| Phone | ✅ Yes | Contact for delivery |
| Address | ✅ Yes | Delivery location |
| City | ✅ Yes | Shipping zone |
| Pincode | ✅ Yes | Postal code |
| Password | ✅ Yes (at signup) | Account security |

## User Flow

### Registration
```
User visits /user/register
    ↓
Fills form (email, name, phone, password)
    ↓
Server validates data
    ↓
Hashes password with werkzeug
    ↓
Stores in database
    ↓
Redirects to login
    ↓
User logs in
```

### Login & Checkout
```
User logs in /user/login
    ↓
Session marked permanent (30 days)
    ↓
User data stored in session
    ↓
Goes to checkout /checkout
    ↓
Delivery details auto-filled
    ↓
User confirms and completes payment
```

### Profile Management
```
User visits /user/profile
    ↓
Views current information
    ↓
Updates delivery details if needed
    ↓
Changes saved to database
```

### Order History
```
User visits /user/orders
    ↓
Sees all their orders
    ↓
Can click individual orders for details
    ↓
Shows payment status & delivery date
```

## Navigation Changes

### Anonymous User:
```
Home | Cart | Login | Register | Admin
```

### Logged-In User:
```
Home | Cart | 👤 John Doe | Profile | Orders | Logout | Admin
```

### Logged-In Admin:
```
Home | Cart | 👤 admin | Admin | Admin Logout
```

## Routes Added

| Route | Method | Purpose |
|-------|--------|---------|
| `/user/register` | GET, POST | User registration form & processing |
| `/user/login` | GET, POST | User login form & authentication |
| `/user/logout` | GET | Clear session & logout |
| `/user/profile` | GET, POST | View & update user details |
| `/user/orders` | GET | List all user orders |

## Session Variables

When user logs in, session stores:
```python
session['user_logged_in'] = True         # Authentication flag
session['user_id'] = user.id             # User database ID
session['user_email'] = user.email       # Email for orders
session['user_name'] = user.full_name    # Display name
```

## Security Features

✅ **Passwords hashed** - Using werkzeug.security
✅ **Secure session** - Persistent cookie with encryption
✅ **Input validation** - Email format, password strength
✅ **SQL injection protection** - Parameterized queries
✅ **CSRF protection** - Via session mechanism
✅ **No plain text** - Passwords never stored

## Checkout Auto-Fill

When user is logged in and visits checkout, these fields are pre-filled:
```html
<input name="name" value="{{ user_data.get('name', '') }}">
<input name="email" value="{{ user_data.get('email', '') }}">
<input name="phone" value="{{ user_data.get('phone', '') }}">
<input name="address" value="{{ user_data.get('address', '') }}">
<input name="city" value="{{ user_data.get('city', '') }}">
<input name="pincode" value="{{ user_data.get('pincode', '') }}">
```

## Configuration

### Session Duration
Currently set to 30 days. Edit in `app.py`:
```python
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)
```

### Password Requirements
Current: Minimum 6 characters
To change, edit in `user_register()`:
```python
if len(password) < 6:
    flash('Password must be at least 6 characters', 'error')
```

## Files Modified/Created

### Backend
- `app.py` - Added user routes and database table

### Templates
- `user_register.html` - Registration form
- `user_login.html` - Login form
- `user_profile.html` - Profile update form
- `user_orders.html` - Order history
- `base.html` - Updated navigation
- `checkout.html` - Pre-fill user data

### Styling
- `styles.css` - Added auth container & status styles

## Testing Checklist

- [ ] Register new user with valid email
- [ ] Try to register with duplicate email → Error
- [ ] Try password too short → Error
- [ ] Successful registration → Redirect to login
- [ ] Log in with correct credentials
- [ ] Try wrong password → Error
- [ ] Session persists after logout → Re-login required
- [ ] Check if logout clears session
- [ ] Update profile details
- [ ] Navigate to checkout → Details auto-filled
- [ ] View order history
- [ ] All orders show correct details

## Improvement Ideas

### Phase 2 Enhancements:
1. Email verification on signup
2. Password reset functionality
3. Order notifications via email
4. Address book (multiple addresses)
5. Wishlist functionality
6. Coupon codes for registered users
7. Loyalty points system
8. Social login (Google, Facebook)

## User Experience Flow

```
New Customer
    ↓
Browses products
    ↓
Adds to cart
    ↓
Clicks checkout
    ↓
Sees "Register to save details" option
    ↓
Creates account
    ↓
Details auto-filled
    ↓
Quick checkout
    ↓
Order placed
    ↓
Can view in "My Orders"
    ↓
Faster future checkouts
```

## Troubleshooting

### User can't register:
- Check email format
- Verify password is 6+ characters
- Ensure email isn't already registered

### Password reset:
- Currently manual: Ask admin to reset password hash
- TODO: Implement forgot password

### Orders not showing:
- Make sure user email matches order email
- Check database for order records

## Next Steps

1. Test user registration & login
2. Verify checkout auto-fill works
3. Test order history display
4. Monitor for any bugs
5. Consider email verification enhancement
