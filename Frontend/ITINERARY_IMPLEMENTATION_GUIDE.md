# Tour Itinerary Stepper Navigation - Implementation Guide

## 🎯 Overview

This guide explains the new tour details page enhancement with **stepper navigation** for day-by-day tour itineraries.

---

## ⚠️ IMPORTANT: Current Status

### What You'll See NOW (Without Itinerary Data)

When you open a tour details page (`/tour/{tour-id}`), you will see:

✅ Tour images gallery
✅ Tour header with pricing
✅ Info cards (duration, departure, dates)
✅ Tour description section
✅ Highlights, services, includes/excludes
⚠️ **"Lịch trình chi tiết đang được cập nhật"** message

**Why?** Your backend database currently doesn't have `itinerary` field in the tour packages schema.

### What You'll See AFTER Adding Itinerary Data

Once you add itinerary data to your tours, you will see:

🎉 **Interactive Stepper Navigation**
🎉 **Day-by-day tour details**
🎉 **Progress tracking**
🎉 **Previous/Next buttons**
🎉 **URL deep-linking** (e.g., `/tour/ABC?day=2`)

---

## 📊 Current Database Schema

Your backend (`Backend/app/v1/schema/tour_package_schema.py`) currently has:

```python
class TourPackageBase(BaseModel):
    package_name: str
    destination: str
    description: str
    duration_days: int
    price: float
    available_slots: int
    start_date: date
    end_date: date
    image_urls: Optional[str]
    cuisine: Optional[str]
    suitable_for: Optional[str]
    is_active: bool
```

**Missing:** `itinerary` field! ❌

---

## 🔧 How to Add Itinerary Support

### Step 1: Update Backend Database Schema

#### Option A: Add JSONB Column (Recommended)

**1. Create database migration:**

```sql
-- Add itinerary column to tour_packages table
ALTER TABLE tour_packages
ADD COLUMN itinerary JSONB DEFAULT NULL;
```

**2. Update your Pydantic schema** (`tour_package_schema.py`):

```python
from typing import Optional, Dict, Any

class TourItineraryDay(BaseModel):
    """Schema for a single day in tour itinerary"""
    title: str
    hotel: str
    meals: str
    morning: Optional[str] = None
    afternoon: Optional[str] = None
    evening: Optional[str] = None
    late_afternoon: Optional[str] = None

class TourItinerary(BaseModel):
    """Schema for tour itinerary"""
    day1: Optional[TourItineraryDay] = None
    day2: Optional[TourItineraryDay] = None
    day3: Optional[TourItineraryDay] = None
    day4: Optional[TourItineraryDay] = None
    day5: Optional[TourItineraryDay] = None
    day6: Optional[TourItineraryDay] = None
    day7: Optional[TourItineraryDay] = None
    day8: Optional[TourItineraryDay] = None
    day9: Optional[TourItineraryDay] = None
    day10: Optional[TourItineraryDay] = None
    note: Optional[str] = None
    highlights: Optional[List[str]] = None
    best_season: Optional[List[str]] = None
    photo_spots: Optional[List[str]] = None
    must_try_food: Optional[List[str]] = None

class TourPackageBase(BaseModel):
    # ... existing fields ...
    itinerary: Optional[TourItinerary] = None  # ADD THIS LINE
```

#### Option B: Create Separate Table (More Normalized)

```sql
-- Create itinerary_days table
CREATE TABLE itinerary_days (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    package_id UUID REFERENCES tour_packages(package_id) ON DELETE CASCADE,
    day_number INT NOT NULL,
    title VARCHAR(255) NOT NULL,
    hotel VARCHAR(255),
    meals VARCHAR(255),
    morning TEXT,
    afternoon TEXT,
    evening TEXT,
    late_afternoon TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(package_id, day_number)
);
```

### Step 2: Add Sample Itinerary Data

**Example JSON structure:**

```json
{
  "itinerary": {
    "day1": {
      "title": "Khám phá Đà Lạt - Thành phố ngàn hoa",
      "hotel": "Khách sạn Dalat Palace Heritage 5*",
      "meals": "Ăn trưa, tối",
      "morning": "6:00 - Đón khách tại điểm hẹn, khởi hành đi Đà Lạt. Trên đường nghỉ chân tại các điểm dừng an toàn.",
      "afternoon": "12:00 - Dùng bữa trưa tại nhà hàng. Sau đó check-in khách sạn và nghỉ ngơi.",
      "evening": "18:00 - Dùng bữa tối tại nhà hàng. Tự do khám phá chợ đêm Đà Lạt."
    },
    "day2": {
      "title": "Vườn hoa - Thác Datanla - Langbiang",
      "hotel": "Khách sạn Dalat Palace Heritage 5*",
      "meals": "Ăn sáng, trưa, tối",
      "morning": "7:00 - Ăn sáng buffet. 8:00 - Tham quan Vườn Hoa Đà Lạt với hàng ngàn loài hoa đầy màu sắc.",
      "afternoon": "12:00 - Ăn trưa. 14:00 - Chinh phục Langbiang, đỉnh núi cao 2.167m với view toàn cảnh Đà Lạt tuyệt đẹp.",
      "evening": "18:30 - Dùng bữa tối BBQ đặc sản Đà Lạt. Tự do nghỉ ngơi."
    },
    "day3": {
      "title": "Trở về - Kết thúc hành trình",
      "hotel": "",
      "meals": "Ăn sáng",
      "morning": "7:00 - Ăn sáng và làm thủ tục trả phòng. Tham quan Thiền viện Trúc Lâm và Hồ Tuyền Lâm.",
      "afternoon": "12:00 - Dùng bữa trưa tại nhà hàng. Khởi hành về TP.HCM.",
      "evening": "19:00 - Về đến điểm đón ban đầu. Kết thúc chương trình."
    },
    "note": "* Giá tour có thể thay đổi theo mùa cao điểm\n* Vui lòng mang theo giấy tờ tùy thân\n* Thời gian có thể thay đổi tùy tình hình thực tế",
    "best_season": [
      "Tháng 12 - Tháng 2: Mùa hoa mimosa, mai anh đào nở rộ",
      "Tháng 10 - Tháng 11: Thời tiết mát mẻ, ít mưa"
    ],
    "photo_spots": [
      "Hồ Tuyền Lâm - Cáp treo Đà Lạt",
      "Đỉnh Langbiang",
      "Vườn hoa Đà Lạt",
      "Thiền viện Trúc Lâm"
    ],
    "must_try_food": [
      "Bánh tráng nướng",
      "Lẩu gà lá é",
      "Nem nướng Đà Lạt",
      "Sữa đậu nành"
    ]
  }
}
```

### Step 3: Update Backend API

**Update `tour_package_service.py`:**

```python
async def get_tour_by_id(package_id: UUID):
    # ... existing code ...
    tour = db.query(TourPackage).filter(...).first()

    # If itinerary exists, include it in response
    result = {
        **tour.__dict__,
        "itinerary": tour.itinerary if hasattr(tour, 'itinerary') else None
    }
    return result
```

### Step 4: Test the Frontend

Once backend is updated:

1. **Navigate to a tour page:** `/tour/{tour-id}`
2. **You should see:**
   - Stepper navigation with day circles
   - Progress bar showing X/Y days
   - Single day content at a time
   - Previous/Next buttons
   - Click any step to jump to that day

3. **Test URL deep-linking:**
   - `/tour/{tour-id}?day=2` → Opens directly to Day 2
   - Share link with friends → They see same day

---

## 📁 Files Created/Modified

### New Components Created:

1. **`tour-day-navigator.component.ts`** - Stepper navigation UI
2. **`tour-day-detail.component.ts`** - Single day display
3. Helper functions in **`tour.model.ts`**:
   - `getItineraryDays()`
   - `getTotalItineraryDays()`

### Modified Files:

1. **`produc-details.component.ts`** - Integrated navigation
2. **`produc-details.component.html`** - Updated UI
3. **`produc-details.component.scss`** - Added styles

---

## 🎨 Features Implemented

✅ **Stepper Navigation** - Visual step-by-step navigation
✅ **Progress Bar** - Shows current day / total days
✅ **URL Deep-linking** - Bookmark specific days
✅ **Responsive Design** - Works on mobile/tablet/desktop
✅ **Animations** - Smooth transitions between days
✅ **Empty State** - Graceful fallback when no itinerary
✅ **Keyboard Navigation** - Arrow keys support (future)

---

## 🔍 Debugging

**Check browser console logs:**

When you open a tour page, you'll see:

```
Tour itinerary: undefined (or null)
Total itinerary days: 0
hasItineraryDays check: false totalItineraryDays: 0
```

This confirms no itinerary data exists.

**After adding itinerary data, you should see:**

```
Tour itinerary: {day1: {...}, day2: {...}, ...}
Total itinerary days: 3
Current day data: {...}
hasItineraryDays check: true totalItineraryDays: 3
```

---

## 🚀 Quick Start (With Sample Data)

**To quickly test the feature:**

1. **Create a test tour with itinerary in your database:**

```sql
-- Update an existing tour (replace with actual tour ID)
UPDATE tour_packages
SET itinerary = '{
  "day1": {
    "title": "Arrival Day",
    "hotel": "Test Hotel 5*",
    "meals": "Lunch, Dinner",
    "morning": "Pickup at airport",
    "afternoon": "Check-in and rest",
    "evening": "Welcome dinner"
  },
  "day2": {
    "title": "City Tour",
    "hotel": "Test Hotel 5*",
    "meals": "Breakfast, Lunch, Dinner",
    "morning": "Visit landmarks",
    "afternoon": "Shopping time",
    "evening": "Cultural show"
  }
}'::jsonb
WHERE package_id = 'your-tour-id-here';
```

2. **Open tour page in browser:**
   ```
   http://localhost:4200/tour/your-tour-id-here
   ```

3. **You should now see the stepper navigation!**

---

## 💡 Tips

- Start with 2-3 day tours to test
- Keep day titles short and descriptive
- Use the `note` field for important information
- Add `best_season`, `photo_spots`, `must_try_food` for richer content
- Test on mobile devices for responsive behavior

---

## ❓ FAQ

**Q: Why do I see "Lịch trình chi tiết đang được cập nhật"?**
A: Your tour packages don't have itinerary data yet. Follow the guide above to add it.

**Q: Can I have more than 10 days?**
A: Yes! Extend the `TourItinerary` interface to add day11, day12, etc.

**Q: Does this work with existing tours?**
A: Yes! Just add the `itinerary` field to your tours and they'll show the stepper.

**Q: What if a tour only has 1 day?**
A: The stepper still shows but with a single step.

---

## 📞 Need Help?

Check the console logs and verify:
1. Backend returns `itinerary` field in API response
2. `itinerary` has `day1`, `day2`, etc. properties
3. Each day has `title`, `hotel`, `meals` minimum fields

---

**Created:** 2025-12-30
**Status:** ✅ Ready for integration with backend itinerary data
