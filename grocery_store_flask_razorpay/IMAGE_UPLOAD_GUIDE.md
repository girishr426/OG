# Product Image Upload Guide

## What Changed
I've added complete image upload functionality to your Flask app. You can now upload and manage product images directly from the admin panel.

## Features Added

### 1. **File Upload Support**
   - Upload JPG, PNG, or GIF images
   - Automatic image optimization (resized to 400x400px, quality 85%)
   - File size limit: 5MB

### 2. **Admin Product Form Updates**
   - New image upload field in the product form
   - Preview of current image when editing
   - Upload new images or keep existing ones

### 3. **Backend Image Processing**
   - Images are automatically optimized using Pillow
   - Unique filenames to prevent conflicts: `product_{id}_{timestamp}.jpg`
   - Old images deleted when updated with new ones
   - All images saved in `static/product_images/`

## How to Use

### Creating a New Product with Image
1. Go to Admin Dashboard → Products → New Product
2. Fill in product details (Name, Price, Stock, etc.)
3. Click "Choose File" under "Product Image"
4. Select a JPG or PNG image
5. Click "Save"

### Updating Product Image
1. Go to Admin Dashboard → Products → Edit Product
2. Current image is displayed
3. Click "Choose File" to upload a new image
4. Leave blank to keep the current image
5. Click "Save"

## Technical Details

### New Functions in `app.py`
- `allowed_file(filename)` - Validates file extensions
- `save_product_image(file, product_id)` - Handles upload, optimization, and saving

### Configuration
- `UPLOAD_FOLDER = 'static/product_images'`
- `ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif'}`
- `MAX_IMAGE_SIZE = 5 * 1024 * 1024` (5MB)

### Database
- Products table already has `image_path` column
- Images are linked to products by ID

## Image Naming Convention
Images are saved with the pattern:
```
product_{product_id}_{timestamp}.jpg
```

Example: `product_1_1702908000.0.jpg`

## Troubleshooting

### Images not showing
- Ensure Flask is running with the updated app.py
- Check that images exist in `static/product_images/`
- Verify image paths in database: `sqlite3 store.db "SELECT id, name, image_path FROM products;"`

### Upload fails
- Check file size (must be under 5MB)
- Verify file format (JPG, PNG, or GIF only)
- Ensure `static/product_images/` folder exists and is writable

### Image quality issues
- Images are automatically resized to 400x400px
- Quality is set to 85 to balance file size and appearance
- Adjust in `save_product_image()` function if needed

## File Upload Security
- Filenames are sanitized using `secure_filename()`
- File extensions validated against whitelist
- File size limited to 5MB
- MIME type checked (image only)

## Next Steps
- Test uploading a product image through the admin panel
- Verify images display correctly on the product page and checkout
- Deploy to production (images included in static folder)
