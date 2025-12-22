# Admin Login Troubleshooting - Invalid Credentials

## Quick Fix Steps

### Step 1: Check the Database
Run this command to check if the admin user exists and verify the password:

```bash
python check_admin.py
```

Expected output should show:
```
✅ Admin users in database:
📝 Username: admin
🔒 Password Hash: ...
✅ Password 'admin123' is VALID
```

### Step 2: Check Environment Variables
Run this command to verify the ADMIN_DEFAULT_PASSWORD is loaded:

```bash
python check_env.py
```

Expected output:
```
✅ ADMIN_DEFAULT_PASSWORD is set to: admin123
```

### Step 3: Reset the Admin User
Run the reset script to recreate the admin user:

```bash
python reset_admin_password.py
```

Expected output:
```
✅ Admin user created successfully!
📝 Username: admin
🔑 Password: admin123
🔗 Login at: http://localhost:5000/admin/login
```

### Step 4: Delete and Recreate Database
If the above doesn't work, delete the database and restart the app:

**Windows (PowerShell):**
```powershell
Remove-Item store.db
python app.py
```

**Mac/Linux:**
```bash
rm store.db
python app.py
```

The app will automatically recreate the database with a new admin user.

## Common Issues and Solutions

### Issue 1: "Invalid credentials" despite correct password
**Cause:** Password hash mismatch or corrupted database entry

**Solution:**
1. Run: `python reset_admin_password.py`
2. Try logging in again with `admin` / `admin123`

### Issue 2: Admin user not found
**Cause:** Database doesn't have admin user

**Solution:**
1. Check: `python check_admin.py`
2. If no admin users shown, run: `python reset_admin_password.py`

### Issue 3: ADMIN_DEFAULT_PASSWORD not set
**Cause:** .env file not properly configured

**Solution:**
1. Open `data/.env`
2. Verify this line exists: `ADMIN_DEFAULT_PASSWORD=admin123`
3. Save and restart the app

### Issue 4: Still getting invalid credentials
**Cause:** Corrupted database or environment issue

**Solution:**
```bash
# Delete old database
Remove-Item store.db  # PowerShell
# OR
del store.db          # CMD
# OR
rm store.db           # Mac/Linux

# Restart app - it will recreate everything
python app.py
```

## Debug Information

The app now includes detailed debug logging. When you try to log in:
1. Open the terminal/console where Flask is running
2. Look for `[DEBUG]` messages
3. They will show:
   - `[DEBUG] Admin user 'admin' not found in database` → User doesn't exist
   - `[DEBUG] Password mismatch for user 'admin'` → Wrong password
   - `[DEBUG] Admin 'admin' login successful` → Login worked

## File Locations

| File | Purpose |
|------|---------|
| `store.db` | Main database (delete if corrupted) |
| `data/.env` | Configuration with ADMIN_DEFAULT_PASSWORD |
| `reset_admin_password.py` | Script to create/reset admin user |
| `check_admin.py` | Debug script to check admin users |
| `check_env.py` | Debug script to check environment setup |

## Default Login Credentials

- **Username:** `admin`
- **Password:** `admin123` (from `data/.env`)
- **URL:** http://localhost:5000/admin/login

## Still Having Issues?

1. **Check Flask console output** for any error messages
2. **Verify .env file** has ADMIN_DEFAULT_PASSWORD set
3. **Run check scripts** to diagnose the problem
4. **Delete database** and restart as last resort
5. **Ensure python-dotenv is installed:** `pip install python-dotenv`

---

**Last Updated:** December 22, 2025
