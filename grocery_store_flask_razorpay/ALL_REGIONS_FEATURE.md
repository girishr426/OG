# "All Regions" Option in Region Selector

**Date:** December 19, 2025

## Overview

A new **"All Regions"** option has been added to the region selector dropdown. When selected, it displays all products across all regions, providing users with a comprehensive view of the entire product catalog.

## What Changed

### Region Selector Options

| Option | Value | Behavior |
|--------|-------|----------|
| **None** | `""` (empty) | Shows featured homepage products (or all products as fallback) |
| **All Regions** | `"all"` | Shows ALL products from all regions |
| **Individual Regions** | Region ID (number) | Shows products available in that specific region |

## Implementation

### Frontend Changes

**File: `templates/base.html`**

```html
<select id="region_id" name="region_id" onchange="this.form.submit()">
  <option value="">None</option>
  <option value="all" {% if current_region_id == 'all' %}selected{% endif %}>All Regions</option>
  {% for r in regions %}
  <option value="{{ r.id }}" {% if current_region_id == r.id %}selected{% endif %}>{{ r.name }}</option>
  {% endfor %}
</select>
```

**Location Indicator Updates:**
```html
{% if current_region_name and current_region_id and current_region_id != 'all' %}
  <span class="user-info">📍 {{ current_region_name }}</span>
{% elif current_region_id == 'all' %}
  <span class="user-info">🌍 All Regions</span>
{% endif %}
```

### Backend Changes

**File: `app.py` - Multiple routes updated**

#### 1. `set_region()` Route

```python
@app.post('/set_region')
def set_region():
    rid = request.form.get('region_id')
    try:
        if rid == 'all':
            # "All Regions" selected
            session['region_id'] = 'all'
            flash('Showing all regions', 'success')
        elif rid:
            rid_int = int(rid)
            session['region_id'] = rid_int
            flash('Region updated', 'success')
        else:
            session.pop('region_id', None)
            flash('Region cleared', 'success')
    except (ValueError, Exception):
        session.pop('region_id', None)
        flash('Region cleared', 'success')
    return redirect(request.referrer or url_for('index'))
```

#### 2. `index()` Route

```python
if region_id == 'all':
    # "All Regions" selected: show all products
    products = conn.execute(SQL_SELECT_PRODUCTS_ORDERED).fetchall()
    page_title = 'All Products'
elif region_id:
    # Show products available in selected region
    products = conn.execute(...).fetchall()
else:
    # No region selected: show homepage products
    products = conn.execute(...).fetchall()
```

#### 3. `search()` Route

```python
if region_id == 'all':
    # "All Regions" selected: show all matching products
    products = conn.execute('SELECT * FROM products WHERE name LIKE ? OR description LIKE ? ORDER BY id DESC', (like, like)).fetchall()
elif region_id:
    # Specific region selected: show region matching products
    products = conn.execute(...).fetchall()
else:
    # No region: show all matching products
    products = conn.execute(...).fetchall()
```

## User Experience Flow

### Scenario: User Selects "All Regions"

```
┌─────────────────────────────────────┐
│ Home Page                           │
│ Select Region: [All Regions ▼]      │
└─────────────────────────────────────┘
        ↓ Auto-submit on selection
        ↓
┌─────────────────────────────────────┐
│ ✓ Showing all regions               │
├─────────────────────────────────────┤
│ All Products                        │
│ [Shows ALL items]                   │
│ Location: 🌍 All Regions            │
└─────────────────────────────────────┘
```

### Scenario: Search with "All Regions" Selected

```
1. Select "All Regions"
2. Type "rice" in search
3. Click Search
4. Results: All matching products from all regions
   (Same as searching with no region selected)
```

## Display Logic

### Page Title Based on Region Selection

| Region Selection | Page Title | Message |
|------------------|-----------|---------|
| None | "New Products" | Featured homepage items |
| None (no homepage items) | "Products" | All products (fallback) |
| **All Regions** | **"All Products"** | **All products** |
| Specific Region | "Products" | Region products |
| Search | "Search: [query]" | Matching products |

### Location Indicator

| Region Selection | Icon | Text |
|------------------|------|------|
| None | (hidden) | (hidden) |
| **All Regions** | **🌍** | **All Regions** |
| Specific Region | 📍 | Region name |

## Session Storage

The region selection is stored in Flask session:

```python
session['region_id'] = 'all'      # For "All Regions"
session['region_id'] = 27         # For a specific region (Tumakuru)
session.pop('region_id', None)    # For "None" option
```

## Product Display Summary

### Display All Products When:
- User selects "All Regions"
- User selects "None" with no homepage products (fallback)
- User searches with "All Regions" selected
- User searches with "None" selected

### Display Specific Region Products When:
- User selects a specific region (e.g., Tumakuru)
- User searches with a specific region selected

### Display Homepage Products When:
- User selects "None" and homepage products exist
- User loads home page with no region selected

## Benefits

✅ **Complete Catalog View:** Users can easily see all available products
✅ **Simple Navigation:** One-click access to entire inventory
✅ **Clear Indication:** "🌍 All Regions" badge shows user's current selection
✅ **Consistent Behavior:** Works seamlessly with search
✅ **Session Persistence:** Selection remembered during user session

## Files Modified

1. **templates/base.html**
   - Added "All Regions" option to dropdown
   - Updated location indicator for "all" case

2. **app.py**
   - Updated `set_region()` to handle "all" value
   - Updated `index()` to display all products for "all" region
   - Updated `search()` to search all products when "all" is selected

## Testing Checklist

- [ ] Select "All Regions" → Page shows "All Products"
- [ ] Select "All Regions" → Location shows "🌍 All Regions"
- [ ] Flash message shows "Showing all regions"
- [ ] All products displayed (no region filtering)
- [ ] Search with "All Regions" selected → Shows matching products from all regions
- [ ] Switch from specific region to "All Regions" → All products shown
- [ ] Switch from "All Regions" to specific region → Only region products shown
- [ ] Switch from "All Regions" to "None" → Shows homepage products
- [ ] Mobile: Dropdown works correctly
- [ ] Mobile: Location indicator displays properly

## SQL Queries

### Display All Products
```sql
SELECT p.* FROM products p ORDER BY p.id DESC
```

### Search All Products
```sql
SELECT * FROM products WHERE name LIKE ? OR description LIKE ? ORDER BY id DESC
```

## Performance Impact

✅ **Minimal:**
- No additional database complexity
- Same queries as existing "show all products" fallback
- Session storage handles "all" as string
- No performance degradation

## Browser Compatibility

✅ **Full Support:** All browsers
- Dropdown works on all browsers
- Session handling works universally
- Auto-submit on change works on all modern browsers

## Related Features

This feature integrates with:
- **Region Filtering:** Provides bypass when users want complete catalog
- **Search:** Works with all-regions search
- **Homepage Products:** Distinct from "All Regions" - different behavior
- **Navigation Highlighting:** Active link still highlights correctly

## Future Enhancements

Optional improvements:
- [ ] Show region count badge
- [ ] Add "All Regions" to admin filters
- [ ] Sort regions alphabetically
- [ ] Add region grouping (e.g., North, South)
- [ ] Regional statistics dashboard

## Technical Notes

### Why String "all" Instead of Special Number?

- Clear distinction from region IDs (which are integers)
- Prevents ID conflicts if region count exceeds a certain number
- Makes code more readable and maintainable
- Easier to understand intent in debugging

### Session Data Type Handling

```python
region_id = session.get('region_id')  # Could be int, string "all", or None

if region_id == 'all':       # String comparison
    # All regions logic
elif region_id:              # Integer check
    # Specific region logic
else:                        # None case
    # Homepage or no region logic
```

## Troubleshooting

### Issue: "All Regions" not showing all products

**Solution:** Ensure `SQL_SELECT_PRODUCTS_ORDERED` constant is defined and queries all products without region filtering.

### Issue: Location indicator showing wrong text

**Solution:** Check template condition:
```html
{% elif current_region_id == 'all' %}
  <span class="user-info">🌍 All Regions</span>
{% endif %}
```

### Issue: Search results incomplete with "All Regions"

**Solution:** Verify search route handles `region_id == 'all'` case specifically before checking truthiness.
