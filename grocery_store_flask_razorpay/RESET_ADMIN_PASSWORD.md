# How to Reset Admin Password

## Method 1: Use the Reset Script (EASIEST)

### Step 1: Make sure Flask app is NOT running
Press `Ctrl+C` in the terminal if it's running

### Step 2: Run the reset script
```powershell
python reset_password.py
```

### Expected Output:
```
============================================================
ADMIN PASSWORD RESET TOOL
============================================================

✅ Database found: store.db
✅ werkzeug imported successfully
✅ Connected to database
✅ admin_users table exists
✅ Admin password updated

============================================================
✅ SUCCESS!
============================================================

Username: admin
Password: admin123

Login at: http://localhost:5000/admin/login

============================================================
```

### Step 3: Start Flask and log in
```powershell
python app.py
```

Go to: http://localhost:5000/admin/login
- Username: `admin`
- Password: `admin123`

---

## Method 2: Quick Command Line (One-liner)

If you want to do it without a separate script:

```powershell
python -c "import sqlite3; from werkzeug.security import generate_password_hash; conn = sqlite3.connect('store.db'); c = conn.cursor(); c.execute('UPDATE admin_users SET password_hash = ? WHERE username = ?', (generate_password_hash('admin123'), 'admin')); conn.commit(); print('✅ Admin password reset to: admin123'); conn.close()"
```

---

## Method 3: Using the Diagnostic URL

### Step 1: Make sure Flask is running
```powershell
python app.py
```

### Step 2: Check admin status
Go to: http://localhost:5000/admin/diagnose

### Step 3: Run the command shown above (Method 2)

---

## Method 4: Complete Reset (Nuclear Option)

If nothing works, do a complete reset:

```powershell
# Stop Flask first (Ctrl+C)

# Delete the database
Remove-Item store.db

# Start Flask - it will create a new database with fresh admin
python app.py
```

Then log in with:
- Username: `admin`
- Password: `admin123`

---

## Troubleshooting

### Error: "werkzeug not installed"
**Solution:**
```powershell
pip install werkzeug
```

### Error: "admin_users table not found"
**Solution:** Database is corrupted
```powershell
Remove-Item store.db
python app.py
```

### Error: "Database not found"
**Solution:** Run Flask first to create the database
```powershell
python app.py
```

---

## Quick Reference

| Task | Command |
|------|---------|
| Reset password | `python reset_password.py` |
| Check admin status | Visit http://localhost:5000/admin/diagnose |
| Start Flask | `python app.py` |
| Admin login page | http://localhost:5000/admin/login |

---

## Default Credentials After Reset

- **Username:** `admin`
- **Password:** `admin123`
- **URL:** http://localhost:5000/admin/login

---

**Last Updated:** December 22, 2025
