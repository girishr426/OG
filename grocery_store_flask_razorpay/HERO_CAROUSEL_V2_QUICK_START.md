# Hero Carousel - v2.0 Enhanced Scrolling Guide

## What's New? 🎉

The hero section carousel has been **completely redesigned** with:

### ✨ Enhanced Features
- **Smooth manual scrolling** with Previous/Next buttons (❮ ❯)
- **Interactive indicator dots** at the bottom
- **5-second auto-advance** with pause on hover
- **Keyboard support** - Use Arrow Left/Right when hovering
- **Smooth transitions** - 0.6s ease animations between slides
- **Professional styling** - Rounded buttons, glowing indicators
- **Mobile-friendly** - 50x50px touch-friendly buttons

---

## How to Upload Hero Images

### Step 1: Go to Admin Panel
```
http://localhost:5000/admin
```

### Step 2: Click "Catalog" in Navigation
This takes you to: `/admin/catalog-images`

### Step 3: Upload Hero Images
1. **Region**: Select "Hero Section (Home Page Carousel)"
2. **Image File**: Choose JPG, PNG, or GIF
3. **Alt Text**: Add description (e.g., "Fresh organic vegetables")
4. **Submit**: Click "Upload Image"

### Image Requirements
- **Format**: JPG, PNG, GIF
- **Max Size**: 5MB
- **Recommended**: 1200x400px or larger
- **Aspect Ratio**: 16:9 (landscape)
- **Max per region**: 4 images

---

## Hero Carousel Controls

### Auto-Scroll
- Automatically changes every 5 seconds
- **Pauses on hover** - Move mouse over to pause
- **Resumes** when mouse leaves the carousel

### Navigation Buttons
- **❮ Previous** button (left side)
  - Click to go to previous slide
  - Resets auto-scroll timer
  
- **❯ Next** button (right side)
  - Click to next slide
  - Resets auto-scroll timer

### Indicator Dots (●)
- Shows at bottom center
- One dot per image
- **Click any dot** to jump to that slide
- **Active dot** is larger and glowing
- Color: Semi-transparent white

### Keyboard Navigation
When hovering over carousel:
- **← Arrow Left** = Previous slide
- **→ Arrow Right** = Next slide

---

## Example Flow

**If you upload 3 hero images:**

```
Upload Progress:
[Image 1] "Organic vegetables" → Position #1
[Image 2] "Fresh fruits" → Position #2
[Image 3] "Farm produce" → Position #3
```

**Homepage Display:**

```
Initial (0s):     Shows Image 1 → ● ○ ○
Auto (5s):        Shows Image 2 → ○ ● ○
Auto (10s):       Shows Image 3 → ○ ○ ●
Auto (15s):       Back to Image 1 → ● ○ ○
```

**User Clicks "Next":**

```
Current: Image 1 → ○ ○ ●
Click ❯ →  Image 2 → ○ ● ○ (timer resets to 5s)
```

---

## CSS & Styling

### Visual Elements
- **Container Height**: 500px (full-width)
- **Buttons**: White with opacity, scale on hover
- **Dots**: Small circles, glow when active
- **Transitions**: 0.6s smooth animation
- **Overlay**: Gradient for text readability

### Responsive
- Mobile: Touch-friendly buttons
- Tablet: Optimized spacing
- Desktop: Full animations active

---

## Database Info

All hero images stored in `catalog_images` table:
```sql
- region: 'hero'
- position: 1, 2, 3, or 4
- image_path: static/catalog_images/...
- alt_text: Your description
- created_at: Upload timestamp
- updated_at: Last modified
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Carousel not showing | Check: Homepage only + no filters applied |
| Images not rotating | Verify: At least 1 hero image uploaded |
| Buttons not clickable | Refresh browser + check console (F12) |
| Slow animations | Check browser: Disable extensions |
| Images blurry | Upload higher resolution (1200x400px+) |
| Dots not visible | Ensure image contrast is sufficient |

---

## Quick Stats

- **Auto-scroll interval**: 5 seconds
- **Transition duration**: 0.6s
- **Max images**: 4 per region
- **Button size**: 50x50px (mobile friendly)
- **Keyboard support**: Yes (Arrow keys)
- **Touch support**: Yes (responsive buttons)

---

## Pro Tips

✅ **Best Practices**
- Use 3-4 images for optimal looping
- Maintain consistent aspect ratio
- Include farm/organic imagery
- Optimize before uploading
- Update seasonally

❌ **Avoid**
- Using low-resolution images
- Mixing aspect ratios
- More than 4 images
- Oversized files (>2MB)

---

## Admin URLs

- **Upload Hub**: `/admin/catalog-images`
- **View All Images**: Same page (scroll to "Current Catalog Images")
- **Delete Image**: Click "Delete" button on image card
- **Admin Dashboard**: `/admin`

---

**Created**: December 22, 2025
**Version**: Hero Carousel v2.0 (Enhanced Scrolling with Manual Controls)
**Status**: ✅ Production Ready
