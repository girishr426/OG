# 🎠 Hero Carousel Setup - Quick Guide

## ✅ FIXED! Carousel Now Displays

The hero carousel is now fully functional! Follow these steps to see it in action:

---

## 🚀 Step-by-Step Setup

### Step 1: Upload Hero Images
1. Go to **Admin Panel** (top right menu)
2. Click **"Manage Catalog Images"**
3. Select region: **"Hero Section (Home Page Carousel)"**
4. Upload 1-5 beautiful images (JPG/PNG)
5. Add alt text for accessibility
6. Click **"Upload"**

### Step 2: Repeat for More Images
- Upload 2-5 images for smooth carousel
- Images appear in order (position 1, 2, 3...)
- Carousel loops automatically

### Step 3: Visit Home Page
1. Close admin panel
2. Go to home page (`/`)
3. **No filters active** (important!)
4. See carousel auto-scrolling images! 🎉

---

## 🖼️ Recommended Image Specs

```
Format:       JPG or PNG
Dimensions:   1200px × 400px (landscape, 3:1 ratio)
File Size:    200-500KB each
Orientation:  Landscape (wider than tall)
Content:      Product showcases, fresh produce, farm views
```

---

## 🎯 Important Notes

### ✅ Carousel Shows When:
- ✅ User is on HOME page (`/`)
- ✅ NO region filter selected
- ✅ NO product status filter selected
- ✅ Hero images exist in database

### ❌ Carousel Hides When:
- ❌ User selected a region filter
- ❌ User selected a product status filter
- ❌ Viewing category pages (/gutcare, /corporate, /gifts)
- ❌ Viewing search results
- ❌ No hero images uploaded

---

## 🎠 Carousel Features (Now Active!)

✅ **Auto-Scrolls** - Every 5 seconds
✅ **Manual Controls** - Previous/Next buttons (❮ ❯)
✅ **Indicator Dots** - Click to jump to slide
✅ **Pause on Hover** - Stops when mouse over carousel
✅ **Resume on Leave** - Auto-scrolls again when mouse leaves
✅ **Smooth Animations** - Professional transitions
✅ **Responsive** - Works on desktop, tablet, mobile

---

## 📸 Image Upload Checklist

- [ ] Image is landscape orientation (wider than tall)
- [ ] Image is at least 800px wide (1200px recommended)
- [ ] Image is clear and high-quality
- [ ] File is under 5MB (optimize if needed)
- [ ] Region selected: **"Hero Section"** (not Left/Right)
- [ ] Alt text filled in for accessibility
- [ ] Image uploaded successfully (no error)

---

## 🐛 If Carousel Still Not Showing

### Check These:

1. **Are images uploaded?**
   - Admin → Manage Catalog Images
   - Check "Hero Section" images exist
   - Should list images with region "Hero"

2. **Correct page?**
   - Visit home page exactly: `/`
   - NOT `/search` or `/gutcare` etc.
   - No filters active (None/None selected)

3. **Refresh browser**
   - Ctrl+F5 (hard refresh)
   - Clear cache if needed
   - Close and reopen browser

4. **Check browser console**
   - Press F12 → Console tab
   - Look for JavaScript errors
   - Report any red errors

5. **Restart Flask app**
   - Stop the app
   - Start it again
   - Refresh home page

---

## 💡 Pro Tips

### Best Practices:
1. **Use 3-5 images** - Smooth scrolling experience
2. **High-quality photos** - Professional appearance
3. **Consistent style** - All images similar color tone
4. **Show products** - Feature what you're selling
5. **Update seasonally** - Keep content fresh
6. **Optimize file size** - Faster page load

### Image Ideas:
- 🥬 Fresh vegetables in basket
- 🌾 Farm or garden view
- 👨‍🌾 Farmer with produce
- 🛒 Shopping experience
- 🌱 Organic/natural theme
- 🎁 Special offers/promotions

---

## 🎬 Expected Behavior

### On Home Page Load:
```
1. Page loads
2. Carousel displays first image
3. Hero text overlay appears (white text)
4. Indicator dots show at bottom
5. Auto-scroll starts (first slide for 5 seconds)
6. Slide 2 automatically appears (with animation)
7. Continues auto-scrolling...
8. After last slide → loops back to first
```

### On User Interaction:
```
User hovers over carousel:
  → Auto-scroll PAUSES
  → Can click buttons/dots manually
  
User moves mouse away:
  → Auto-scroll RESUMES
  
User clicks ❮ button:
  → Jumps to previous slide
  → Timer resets for 5 seconds
  
User clicks indicator dot:
  → Jumps to that slide
  → Timer resets for 5 seconds
```

---

## 📞 Still Need Help?

1. Check uploaded images: Admin → Manage Catalog Images
2. Verify home page URL is exactly `/` (no parameters)
3. Try different images (in case files corrupted)
4. Clear browser cache completely
5. Restart browser and Flask app
6. Check browser console (F12) for errors

---

## ✨ You're Ready!

Carousel is now fully functional and waiting for your beautiful images! 

**Next Step**: Upload 3-5 hero images and see the magic happen! 🎠✨
