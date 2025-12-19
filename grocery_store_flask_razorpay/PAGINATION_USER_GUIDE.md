# Pagination Feature - User Guide

## How It Works

### Product Display
```
╔════════════════════════════════════════════════════════════════╗
║  Organic Gut Point                          🔍 [Search]  [🌍]  ║
╠════════════════════════════════════════════════════════════════╣
║                                                                ║
║  Products                                                      ║
║                                                                ║
║  Showing 1-12 of 48 products                      (INFO LINE)  ║
║  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        ║
║  │ Product 1    │  │ Product 2    │  │ Product 3    │        ║
║  │ ₹299         │  │ ₹349         │  │ ₹279         │        ║
║  │ [Add to Cart]│  │ [Add to Cart]│  │ [Add to Cart]│        ║
║  └──────────────┘  └──────────────┘  └──────────────┘        ║
║  ... (12 products total per page)                             ║
║                                                                ║
║  ← Previous  1  2  3  4  5  ...  Next →                       ║
║             (active page highlighted)                         ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
```

### Pagination Navigation

**Page 1 (with 5 pages total):**
```
← Previous  [1]  2  3  4  5
```
- Previous button: DISABLED (shown in gray)
- Current page: 1 (highlighted in organic gradient)

**Page 3 (with 5 pages total):**
```
← Previous  1  2  [3]  4  5  Next →
```
- Previous button: ENABLED
- Next button: ENABLED
- Page 3: ACTIVE (highlighted)

**Page 1 (with 20 pages total):**
```
← Previous  [1]  2  3  4  5  ...  20  Next →
```
- Shows first 5 page numbers
- Shows ellipsis "..." when gap exists
- Shows last page (20) as shortcut

**Page 12 (with 20 pages total):**
```
← Previous  1  ...  10  11  [12]  13  14  ...  20  Next →
```
- Current page in center: 12
- Smart range: 10-14 (current ± 2)
- First page (1) and last page (20) shown as shortcuts

**Page 20 (with 20 pages total):**
```
← Previous  1  ...  16  17  18  19  [20]
```
- Next button: DISABLED (shown in gray)
- Page 20: ACTIVE (last page)

---

## Features Explained

### 🔢 Product Count Info
```
Showing 1-12 of 48 products
```
- **1-12:** Products currently visible on this page
- **48:** Total products across all pages
- Helps users understand pagination scope

### ⬅️ Previous / Next ➡️
- **Previous:** Jump to previous page (disabled on page 1)
- **Next:** Jump to next page (disabled on last page)
- Touch-friendly on mobile (large tap targets)

### 📄 Page Numbers
- **Click any number:** Jump directly to that page
- **Current page highlighted:** Shows in organic gradient color (brown → tan)
- **Hover effect:** Numbers change background on hover

### 📍 Smart Range
- Shows 5 page links: current page ± 2
- Example: On page 5 of 20, shows pages 3, 4, 5, 6, 7
- Example: On page 1 of 20, shows pages 1, 2, 3, 4, 5

### ... Ellipsis
- Shows "..." when gap > 1 between page ranges
- Example: 1 ... 16 17 18 19 20 (on page 18)
- Indicates there are more pages in between

---

## Search with Pagination

### Search Results Pagination
```
/search?q=organic&page=1     ← Page 1 of search results
/search?q=organic&page=2     ← Page 2 of search results

Search: organic
Showing 1-12 of 24 results

← Previous  [1]  2  Next →
```

**Search query preserved:** When you click page 2, the search term "organic" is still in the URL and search results

---

## Region with Pagination

### Region-Specific Products
```
Select Region: Tumakuru [dropdown]

Products (Tumakuru Region)
Showing 1-12 of 36 products

← Previous  [1]  2  3  Next →
```

### All Regions
```
Select Region: All Regions [dropdown]

All Products
Showing 1-12 of 48 products

← Previous  [1]  2  3  4  Next →
```

**Region selection preserved:** When you change pages, your region selection stays the same

---

## Mobile Experience

### Compact Layout (Tablet - 768px)
```
Products

Showing 1-12 of 48
← Previous  [1] 2 3  Next →
```

### Ultra-Compact (Mobile - 480px & below)
```
Products

Showing 1-12 of 48

[← Previous]  ← Full width button
   [1] 2 3       ← Centered page numbers
[Next →]         ← Full width button
```

- Full-width navigation buttons
- Vertical stacking for easy tapping
- Minimum 40px touch targets for accessibility

---

## Examples

### Example 1: Browsing All Products
**Scenario:** You have 48 products total

1. Visit homepage → Shows page 1 with 12 products
2. Click "2" → Shows page 2 with products 13-24
3. Click "4" → Shows page 4 with products 37-48 (last page, only 12 products)
4. Click "Next" → Button disabled (already on last page)

**URL progression:**
```
/ → /?page=2 → /?page=4
```

### Example 2: Searching Products
**Scenario:** Search for "turmeric" with 20 results

1. Enter "turmeric" in search → Shows page 1 (products 1-12)
2. Click "2" → Shows page 2 (products 13-20)
3. Click "← Previous" → Back to page 1
4. Change region → Search results update for new region only

**URL:**
```
/search?q=turmeric&page=1 → /search?q=turmeric&page=2
```

### Example 3: Region Navigation with Pagination
**Scenario:** Browsing Tumakuru region with 36 products

1. Select "Tumakuru" from dropdown → Page 1 shows 12 products from Tumakuru
2. Click "3" → Shows page 3 (products 25-36)
3. Select "All Regions" → Shows page 1 of ALL products (region filter removed)

**Filters preserved across pages within same region**

---

## Keyboard Navigation

- **Tab:** Navigate between Previous/Next buttons and page numbers
- **Enter:** Click selected button/link
- **Screen Readers:** All elements have proper semantic HTML and ARIA labels

---

## Best Practices

✅ **What Works Well**
- Click page numbers for fast navigation
- Use Previous/Next for sequential browsing
- Combine with search/filters for focused shopping
- Mobile users: Tap Previous/Next for easy one-handed navigation

❌ **What to Avoid**
- Don't manually edit page numbers in URL (gets redirected to max page if invalid)
- Pagination doesn't work without JavaScript for link URLs
- Search/region selection required for proper pagination context

---

## FAQ

**Q: Why only 12 products per page?**
A: Industry standard for e-commerce. Proven to balance content display with page load speed.

**Q: Can I change products per page?**
A: Currently 12 is fixed. Future feature could add a dropdown selector.

**Q: What if I type an invalid page number?**
A: Automatically redirected to the last valid page.

**Q: Do my search/region filters stay when I go to page 2?**
A: Yes! Both search query and region selection are preserved in URLs.

**Q: Is pagination mobile-friendly?**
A: Absolutely! Designed mobile-first with 40px+ touch targets.

---

## Summary

✅ **12 products per page** - Industry standard
✅ **Numbered pagination** - Direct page access
✅ **Smart page range** - Shows context-aware page numbers
✅ **Search & filter preservation** - URLs maintain state
✅ **Fully responsive** - Works great on all devices
✅ **Accessible** - Keyboard navigation, semantic HTML

**Ready to use! Start exploring products across pages.**
