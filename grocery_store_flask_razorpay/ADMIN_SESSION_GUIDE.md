# Admin Session Persistence - Keep Admin Logged In

## What Changed
Updated the Flask app to keep admin users logged in persistently until they manually log out. Sessions now survive server restarts and browser closures.

## Configuration Changes

### Session Settings Added (in app.py):
```python
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)  # 30 days
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True for HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True  # Prevent JavaScript access
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # CSRF protection
```

### Login Update:
Added `session.permanent = True` in the admin_login function to activate persistent sessions.

## How It Works

### Before:
- Admin session expired after browser closure or server restart
- Admin had to log in again each time

### After:
- Admin stays logged in for **30 days** (configurable)
- Session persists across:
  - Browser closures
  - Server restarts
  - Page refreshes
  - Network interruptions

## Session Behavior

| Event | Result |
|-------|--------|
| Admin logs in | Session set to persistent (30 days) |
| Browser closed | Session continues on next visit |
| Server restarts | Session continues (stored in cookies) |
| Admin logs out | Session immediately destroyed |
| 30 days pass | Session automatically expires |

## Customization

### Change Session Duration:
Edit line in `app.py`:
```python
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=X)  # Change X to desired days
```

Examples:
- `timedelta(days=1)` - 1 day
- `timedelta(days=7)` - 1 week
- `timedelta(hours=2)` - 2 hours
- `timedelta(days=365)` - 1 year

### Enable HTTPS (Production):
In `app.py`, change:
```python
app.config['SESSION_COOKIE_SECURE'] = True  # Only send over HTTPS
```

## Security Notes

✅ **Secure by default:**
- `SESSION_COOKIE_HTTPONLY = True` - Prevents XSS attacks
- `SESSION_COOKIE_SAMESITE = 'Lax'` - Prevents CSRF attacks
- Passwords are hashed with werkzeug

### For Production:
1. Set `SESSION_COOKIE_SECURE = True` (requires HTTPS)
2. Use strong `APP_SECRET_KEY` environment variable
3. Consider shorter session lifetime for sensitive operations
4. Implement logout on user request (already done via `/admin/logout`)

## Testing

1. Log in as admin (username: `admin`, password: `admin123`)
2. Close the browser completely
3. Reopen and go to `/admin` - You should still be logged in ✓
4. Restart the Flask server
5. Go to `/admin` - You should still be logged in ✓
6. Click "Logout" - Session is destroyed ✓

## Session Storage

- Session data stored in encrypted cookies
- No database queries needed for session verification
- Reduces server load
- Works across multiple server instances (with same SECRET_KEY)

## Logout Behavior

Admin can log out by:
1. Clicking "Logout" link on any admin page
2. This clears the session immediately
3. Must log in again to access admin features

## Files Modified
- `app.py` - Added session configuration and persistent login
