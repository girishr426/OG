# Admin Login - Not Able to Login - SOLUTION

## Step 1: Check Admin Setup Status

**Start the Flask app:**
```powershell
python app.py
```

**Open your browser and go to:**
```
http://localhost:5000/admin/diagnose
```

This will show you something like:
```json
{
  "admin_users_table_exists": true,
  "admin_users": [{"id": 1, "username": "admin"}],
  "admin_default_password_set": true,
  "env_password_value": "admin123",
  "db_path": "store.db",
  "db_exists": true
}
```

---

## Step 2: Based on the Diagnostic Results

### **If admin_users is EMPTY [] :**
The admin user doesn't exist. Run this command:
```powershell
python -c "import sqlite3, os; from werkzeug.security import generate_password_hash; conn = sqlite3.connect('store.db'); c = conn.cursor(); c.execute('INSERT OR REPLACE INTO admin_users (username, password_hash) VALUES (?, ?)', ('admin', generate_password_hash('admin123'))); conn.commit(); print('✅ Admin user created'); conn.close()"
```

### **If admin_users HAS [{"id": 1, "username": "admin"}] :**
The admin user exists, but password verification might be failing.

**Check the Flask console** when you try to log in. Look for messages like:
```
[DEBUG LOGIN] ✅ Admin user 'admin' found in database
[DEBUG LOGIN] ❌ Password verification failed for 'admin'
```

If password verification fails, the password hash might be corrupted. **Rebuild it:**
```powershell
python -c "import sqlite3, os; from werkzeug.security import generate_password_hash; conn = sqlite3.connect('store.db'); c = conn.cursor(); c.execute('UPDATE admin_users SET password_hash = ? WHERE username = ?', (generate_password_hash('admin123'), 'admin')); conn.commit(); print('✅ Password updated'); conn.close()"
```

### **If admin_users_table_exists is FALSE :**
The table doesn't exist. Delete and recreate the database:
```powershell
Remove-Item store.db
python app.py
```
The app will recreate the database automatically.

---

## Step 3: Try Logging In

**Go to:** http://localhost:5000/admin/login

**Use:**
- **Username:** `admin`
- **Password:** `admin123`

**Check the Flask console** for debug messages showing the login process.

---

## Step 4: If Still Not Working

**Complete Reset:**
```powershell
# Stop the Flask app first (Ctrl+C)

# Delete the database
Remove-Item store.db

# Restart Flask - it will recreate everything
python app.py
```

Then try logging in again with `admin` / `admin123`.

---

## Troubleshooting Checklist

- [ ] `/admin/diagnose` shows admin_users is not empty
- [ ] `/admin/diagnose` shows admin_default_password_set is true
- [ ] Flask console shows `[DEBUG LOGIN] ✅ Admin user 'admin' found in database`
- [ ] Flask console shows `[DEBUG LOGIN] ✅ Password verification successful`
- [ ] Login form accepts username: `admin`, password: `admin123`

---

## Still Having Issues?

**Option 1: Check if werkzeug is installed**
```powershell
pip install werkzeug
```

**Option 2: Check if data/.env has the password**
```powershell
type data\.env | grep ADMIN_DEFAULT_PASSWORD
```

Should show:
```
ADMIN_DEFAULT_PASSWORD=admin123
```

**Option 3: Full System Reset**
```powershell
# Stop Flask app (Ctrl+C)
Remove-Item store.db
pip install --upgrade werkzeug flask
python app.py
```

---

## Important Files

| File | Purpose |
|------|---------|
| `store.db` | Database file (contains admin user) |
| `data/.env` | Configuration with ADMIN_DEFAULT_PASSWORD |
| `app.py` | Flask app with login logic |

---

**Login URL:** http://localhost:5000/admin/login
**Diagnostic URL:** http://localhost:5000/admin/diagnose
**Default Username:** admin
**Default Password:** admin123

---

**Last Updated:** December 22, 2025
