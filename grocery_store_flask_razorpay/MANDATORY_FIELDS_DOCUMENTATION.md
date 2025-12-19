# Mandatory Product Upload Fields

**Date:** December 19, 2025

## Overview

Product upload now has strict validation to ensure data quality. The following fields are **MANDATORY** and must be completed before a product can be created or updated.

## Mandatory Fields

### 1. **Product Name** (Text Input)
- **Requirement:** Must not be empty
- **Validation:** Trimmed and checked for content
- **Error Message:** "Product name is required"
- **Visual Indicator:** Red asterisk (*)

### 2. **Product Description** (Textarea)
- **Requirement:** Must not be empty
- **Validation:** Trimmed and checked for content
- **Error Message:** "Product description is required"
- **Visual Indicator:** Red asterisk (*)

### 3. **Product Price** (Number Input)
- **Requirement:** Must be provided and be a valid positive number
- **Validation:** 
  - Must not be empty
  - Must be convertible to a float
  - Must be greater than or equal to 0
- **Error Messages:**
  - "Product price is required"
  - "Price must be a valid number"
  - "Price must be a positive number"
- **Visual Indicator:** Red asterisk (*)

### 4. **Product Region(s)** (Checkboxes)
- **Requirement:** At least ONE region must be selected
- **Validation:** Checked that at least one checkbox is selected
- **Error Message:** "Please select at least one region for this product"
- **Visual Indicator:** Red asterisk (*) on legend
- **Note:** Multiple regions can be selected

### 5. **Product Image** (File Upload)
- **Requirement:** 
  - For **NEW products:** Image file is mandatory
  - For **EDITING products:** Optional (can keep existing image)
- **Validation:**
  - File must be provided (for new products only)
  - Accepted formats: JPG, PNG
  - Image is processed server-side (auto-fit, EXIF orientation, RGB conversion)
- **Error Message:** "Product image is required"
- **Visual Indicator:** Red asterisk (*)
- **Upload Behavior:**
  - New Product: File input marked as `required`
  - Edit Product: File input is optional with note "Leave blank to keep current image"

## Optional Fields

The following fields are **OPTIONAL**:

- **Stock** (Number) - Default: 0
- **Estimated Delivery Days** (Number) - Default: None
- **Estimated Delivery Date** (Date) - Default: None
- **Display on Home Page** (Checkbox) - Default: Unchecked

## Validation Flow

### When Form is Submitted

1. **Check all mandatory fields:**
   - Name (non-empty)
   - Description (non-empty)
   - Price (valid positive number)
   - At least one region selected
   - Image provided (for new products only)

2. **If any validation fails:**
   - Show error messages for each failed field
   - Return form with previously entered data preserved
   - User can correct errors and resubmit

3. **If all validations pass:**
   - Create/update product in database
   - Save image and process it
   - Assign regions
   - Redirect to products list
   - Show success message

## Error Messages Display

All validation errors are displayed as flash messages with `error` class (red background with dark text):
- Multiple errors show as separate flash items
- All form data is preserved for user correction
- User can immediately see what needs to be fixed

## Template Updates

The form template (`admin_product_form.html`) now includes:

✅ **Visual Indicators:** Red asterisks (*) next to mandatory fields
✅ **Inline Help Text:** Clear notes explaining requirements
✅ **Conditional Image Help:**
  - New products: "Image is required for new products"
  - Edit products: "Leave blank to keep current image"
✅ **Region Instructions:** "Select at least one Karnataka region where this product is available. This is required."

## Backend Validation (Python)

### New Product Creation (`admin_product_new()`)

```python
# Validation checks before product creation
errors = []
if not name:
    errors.append('Product name is required')
if not description:
    errors.append('Product description is required')
if not price_str:
    errors.append('Product price is required')
else:
    try:
        price = float(price_str)
        if price < 0:
            errors.append('Price must be a positive number')
    except ValueError:
        errors.append('Price must be a valid number')

if not selected_regions:
    errors.append('Please select at least one region for this product')

if 'image' not in request.files or request.files['image'].filename == '':
    errors.append('Product image is required')
```

### Existing Product Editing (`admin_product_edit()`)

```python
# Same validation as new product creation
# but image is optional (can keep existing)
```

## User Experience Improvements

✅ **Client-side:** HTML5 `required` attributes prevent empty submissions
✅ **Server-side:** Python validation ensures data integrity
✅ **Error Feedback:** Clear, specific error messages
✅ **Data Preservation:** Form retains user input on validation failure
✅ **Visual Clarity:** Red asterisks mark mandatory fields
✅ **Helpful Text:** Instructions explain what's needed

## Testing Checklist

- [ ] Try creating product without name → Error shown
- [ ] Try creating product without description → Error shown
- [ ] Try creating product without price → Error shown
- [ ] Try creating product with invalid price (letters) → Error shown
- [ ] Try creating product with negative price → Error shown
- [ ] Try creating product without image → Error shown
- [ ] Try creating product without selecting regions → Error shown
- [ ] Create product with all mandatory fields → Success
- [ ] Edit existing product and keep same image → Success
- [ ] Edit existing product without uploading new image → Success
- [ ] Edit existing product and remove region selection → Error shown
- [ ] Verify all mandatory fields are visually marked with asterisks

## Implementation Details

**Files Modified:**
1. `app.py` - `admin_product_new()` function (comprehensive validation)
2. `app.py` - `admin_product_edit()` function (validation with optional image)
3. `templates/admin_product_form.html` - Added required indicators and updated help text

**No Database Changes:** This is a validation layer only - no schema changes needed.
