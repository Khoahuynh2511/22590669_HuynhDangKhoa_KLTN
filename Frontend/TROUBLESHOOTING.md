# Troubleshooting Guide - Why Can't I See the Itinerary Components?

## Step-by-Step Debugging

### Step 1: Check if the Tour Details Page Loads AT ALL

**Navigate to:** `http://localhost:4200/tour-details/{some-tour-id}`

Replace `{some-tour-id}` with an actual tour package ID from your database.

**Do you see:**
- ✅ Tour images?
- ✅ Tour title and pricing?
- ✅ Tour description?
- ✅ Info cards (duration, departure, etc.)?

#### If YES - Tour page loads fine:
Continue to Step 2.

#### If NO - Page is completely blank:
The problem is NOT with the new itinerary components. The issue is:
1. Tour ID doesn't exist in database
2. API is not responding
3. `isTourMode` is not being set correctly

**Check browser console (F12) for errors**

---

### Step 2: Scroll Down to Itinerary Section

After tour description, highlights, and services, scroll down to find:

**Option A: You should see ONE of these:**

**Scenario 1:** Empty State Message (Currently expected)
```
📅 [Large calendar icon]

Lịch trình chi tiết đang được cập nhật

Hiện tại tour này chưa có lịch trình chi tiết theo từng ngày.
Vui lòng liên hệ với chúng tôi để biết thêm thông tin về chương trình tour.

📞 Hotline: 1900-xxxx
```

**Scenario 2:** Stepper Navigation (Only if tour has itinerary data)
```
🗺️ Lịch trình chi tiết
Khám phá hành trình của bạn từng ngày

[Progress bar: Ngày 1 / 3]
[○ Ngày 1] [○ Ngày 2] [○ Ngày 3]
[← Ngày trước] [Ngày sau →]

[Day content shows here]
```

**Option B: Nothing at all**
If you see NOTHING in the itinerary section (no empty state, no stepper), there's a rendering issue.

---

### Step 3: Open Browser Console (F12)

Press F12 to open Developer Tools, go to **Console** tab.

**Look for these messages:**

```
Tour itinerary: undefined
Total itinerary days: 0
Current day data: undefined
```

This confirms: **No itinerary data exists** (expected)

**OR look for errors:**
```
ERROR Error: ... TourDayNavigatorComponent ...
ERROR Error: ... TourDayDetailComponent ...
```

This means: **Component is broken**

---

### Step 4: Check Network Tab

In Developer Tools, go to **Network** tab.

Find the request to get tour details (something like `GET /api/tour-packages/{id}`)

**Click on it and check the Response:**

```json
{
  "package_id": "...",
  "package_name": "...",
  "description": "...",
  "itinerary": null  ← Should be null or undefined
}
```

If `itinerary` is null/undefined → Empty state should show

---

### Step 5: Check Elements Tab

In Developer Tools, go to **Elements** tab.

Press Ctrl+F and search for: `itinerary-empty-section`

**Do you find it?**
- ✅ YES → Element exists, check if it has `display: none` or `opacity: 0`
- ❌ NO → Angular is not rendering it at all

---

## Common Issues & Solutions

### Issue 1: Nothing Shows Up (No empty state, no stepper)

**Possible Cause:** The parent `<div>` wrapping everything has condition `*ngIf="isTourMode && tour && !isLoadingTour"`

**Solution:** Check console logs:
```javascript
// You should see these in console:
Tour itinerary: undefined
Total itinerary days: 0
```

If you DON'T see these logs, the tour is not loading at all.

---

### Issue 2: "Cannot read property 'itinerary' of undefined"

**Cause:** Tour object is undefined

**Solution:** Make sure you're navigating to correct route:
- ✅ `http://localhost:4200/tour-details/YOUR-TOUR-ID`
- ❌ `http://localhost:4200/tour/YOUR-TOUR-ID` (wrong route!)

---

### Issue 3: Components showing as `<app-tour-day-navigator></app-tour-day-navigator>` in DOM but empty

**Cause:** Component not imported properly

**Check:** `F:\UIT\SE347\doan\SE347_IE104_Frontend\src\app\pages\produc-details\produc-details.component.ts`

Line 43 should be:
```typescript
imports: [CommonModule, TourCardComponent, TourDayNavigatorComponent, TourDayDetailComponent],
```

---

### Issue 4: CSS Not Loaded

**Symptom:** You see text but no styling

**Solution:** Clear browser cache (Ctrl+Shift+Delete) and hard refresh (Ctrl+F5)

---

## What to Report Back

Please tell me:

1. **Can you see the tour details page at all?** (images, title, price)
   - [ ] Yes
   - [ ] No

2. **What do you see in the itinerary section area?**
   - [ ] Nothing (blank/empty)
   - [ ] Empty state message ("Lịch trình chi tiết đang được cập nhật")
   - [ ] Stepper navigation
   - [ ] Error message

3. **Console errors?** (copy-paste any errors from browser console)

4. **Network response?** (does the API return the tour data?)

---

## Quick Test URLs

Try these URLs (replace with your actual tour IDs):

```
http://localhost:4200/tour-details/PASTE-YOUR-TOUR-ID-HERE
```

Make sure:
- Backend is running
- Tour ID exists in database
- You're using the correct route (`tour-details` not `tour`)

---

## Emergency: Force Test with Mock Data

If you want to bypass the backend completely to test the components, edit this file:

`F:\UIT\SE347\doan\SE347_IE104_Frontend\src\app\pages\produc-details\produc-details.component.ts`

Add after line 175 (after `await this.loadRelatedTours();`):

```typescript
// TEMPORARY TEST - Remove after testing
this.totalItineraryDays = 2;
this.currentItineraryDay = 1;
this.currentDayData = {
  title: "Test Day 1",
  hotel: "Test Hotel 5*",
  meals: "Breakfast, Lunch",
  morning: "Morning activities test",
  afternoon: "Afternoon activities test",
  evening: "Evening activities test"
};
console.log("FORCED TEST DATA - Components should now appear!");
```

Rebuild and refresh browser. You should now see the stepper with test data.

---

**After following these steps, please tell me exactly what you see!**
