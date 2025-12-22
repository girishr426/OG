# Admin Login Guide

## Overview
When the database (`store.db`) is deleted or recreated, a new admin user is automatically created with default credentials.

## Automatic Admin Creation
When the Flask app starts, it automatically:
1. ✅ Creates the database schema if it doesn't exist
2. ✅ Creates a default admin user if none exists
3. ✅ Uses the password from `ADMIN_DEFAULT_PASSWORD` environment variable

## Default Credentials

### If You Have the `.env` File
The admin password is set in `data/.env`:
```properties
ADMIN_DEFAULT_PASSWORD=admin123
```

**Default Login:**
- **Username:** `admin`
- **Password:** (value of `ADMIN_DEFAULT_PASSWORD` in `.env`)
- **Login URL:** `http://localhost:5000/admin/login`

## If Admin Login is Not Working

### Method 1: Restart the App (Recommended)
Simply restart the Flask application:
```bash
python app.py
```

The app will automatically reinitialize the database and create an admin user.

### Method 2: Run the Reset Script
Execute the `reset_admin_password.py` script to create/reset the admin user:

**On Windows (PowerShell):**
```powershell
cd 'C:\Users\girr\Documents\My\O-G\GIT\MobileView\OG\grocery_store_flask_razorpay'
python reset_admin_password.py
```

**On Mac/Linux:**
```bash
cd ~/path/to/grocery_store_flask_razorpay
python reset_admin_password.py
```

**Expected Output:**
```
✅ Admin user created successfully!
📝 Username: admin
🔑 Password: admin123
🔗 Login at: http://localhost:5000/admin/login
```

### Method 3: Manually Delete the Database
Delete `store.db` and restart the app:
```bash
rm store.db          # Mac/Linux
del store.db         # Windows (CMD)
Remove-Item store.db # Windows (PowerShell)
```

Then restart the Flask app - it will recreate everything automatically.

## Changing the Admin Password

### Option 1: Change via `.env` File
Edit `data/.env`:
```properties
ADMIN_DEFAULT_PASSWORD=your-new-password
```

Then either:
- Restart the app and delete the database, or
- Run the reset script

### Option 2: Change in Database (After Login)
1. Log in as admin at `/admin/login`
2. Look for admin settings (if available)
3. Change password through the UI

## Troubleshooting

### Problem: "Admin user not found in database"
**Solution:** 
1. Run: `python reset_admin_password.py`
2. Check that `data/.env` file exists with `ADMIN_DEFAULT_PASSWORD` set

### Problem: "Database not found"
**Solution:**
1. Restart the Flask app: `python app.py`
2. The app will create the database automatically
3. Then run the reset script if needed

### Problem: Admin password doesn't match
**Solution:**
1. Check the value in `data/.env` under `ADMIN_DEFAULT_PASSWORD`
2. Run: `python reset_admin_password.py`
3. Restart the app

## Default Admin Credentials Summary

| Item | Value |
|------|-------|
| **Username** | `admin` |
| **Password** | `admin123` (from `.env` file) |
| **Login URL** | http://localhost:5000/admin/login |
| **Access to** | Products, Orders, Subscribers, Catalog management |

## Security Notes

⚠️ **Important:**
- Change `ADMIN_DEFAULT_PASSWORD` in `.env` for production
- Never commit the `.env` file with credentials to version control
- Store sensitive information in environment variables only
- Use strong passwords in production environments

## Database Files Location

- **Main Database:** `store.db` (in project root)
- **Config File:** `data/.env` (admin password defined here)
- **Reset Script:** `reset_admin_password.py` (in project root)

---

**Last Updated:** December 22, 2025
