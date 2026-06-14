import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { ActivityService, ActivityPackage } from '../../services/activity.service';
import { AuthStateService } from '../../services/auth-state.service';

export interface ItineraryDay {
  morning: ActivityPackage[];
  afternoon: ActivityPackage[];
  evening: ActivityPackage[];
  [key: string]: ActivityPackage[]; // index signature for dynamic slot access
}

@Component({
  selector: 'app-activities',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './activities.component.html',
  styleUrl: './activities.component.scss'
})
export class ActivitiesComponent implements OnInit {
  // Setup state
  destinations: string[] = [];
  selectedDestination: string = '';
  travelDate: string = '';
  durationDays: number = 3;
  groupSize: number = 2;
  setupCompleted: boolean = false;

  // Loading & error states
  isLoadingDestinations: boolean = false;
  isLoadingActivities: boolean = false;
  isCheckingOut: boolean = false;
  errorMessage: string = '';
  successMessage: string = '';

  // Activities Pool
  activitiesPool: ActivityPackage[] = [];
  filteredPool: ActivityPackage[] = []
  searchQuery: string = '';
  selectedCategory: string = '';
  categories: string[] = [];

  // Itinerary State
  itinerary: Record<string, ItineraryDay> = {};
  totalPrice: number = 0;

  // Drag and Drop State
  isDragging: boolean = false;
  draggedPoolActivity: ActivityPackage | null = null;
  draggedItineraryActivity: { dayKey: string; slot: string; activity: ActivityPackage | null; index: number } | null = null;
  dragOverSlot: { dayKey: string; slot: string } | null = null;
  activeReplacePanel: { dayKey: string; slot: string } | null = null;

  currentUser: any = null;

  constructor(
    private router: Router,
    private activityService: ActivityService,
    private authStateService: AuthStateService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    // Set default travel date to tomorrow
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    this.travelDate = tomorrow.toISOString().split('T')[0];

    // Load available destinations
    this.loadDestinations();

    // Check user auth state
    this.authStateService.currentUser$.subscribe(user => {
      this.currentUser = user;
    });
  }

  loadDestinations(): void {
    this.isLoadingDestinations = true;
    this.activityService.getDestinations().subscribe({
      next: (res) => {
        if (res.EC === 0 && res.data) {
          this.destinations = res.data;
          if (this.destinations.length > 0) {
            this.selectedDestination = this.destinations[0];
          }
        }
        this.isLoadingDestinations = false;
      },
      error: (err) => {
        console.error('Error loading destinations:', err);
        this.errorMessage = 'Không thể tải danh sách điểm đến. Vui lòng tải lại trang.';
        this.isLoadingDestinations = false;
      }
    });
  }

  startPlanning(): void {
    if (!this.selectedDestination) {
      this.errorMessage = 'Vui lòng chọn điểm đến.';
      return;
    }
    if (!this.travelDate) {
      this.errorMessage = 'Vui lòng chọn ngày đi.';
      return;
    }
    if (this.durationDays < 1 || this.durationDays > 7) {
      this.errorMessage = 'Số ngày phải từ 1 đến 7.';
      return;
    }
    if (this.groupSize < 1 || this.groupSize > 20) {
      this.errorMessage = 'Số người phải từ 1 đến 20.';
      return;
    }

    this.errorMessage = '';
    this.successMessage = '';

    // Initialize itinerary structure
    this.itinerary = {};
    for (let i = 1; i <= this.durationDays; i++) {
      this.itinerary[`day_${i}`] = {
        morning: [],
        afternoon: [],
        evening: []
      };
    }
    this.recalculatePrice();

    // Load activities for the destination
    this.isLoadingActivities = true;
    this.activityService.getActivities({ destination: this.selectedDestination, limit: 50 }).subscribe({
      next: (res) => {
        if (res.EC === 0 && res.data) {
          this.activitiesPool = res.data;
          this.filterActivities();

          // Extract unique categories from loaded activities
          const cats = res.data
            .map(act => act.category)
            .filter((c): c is string => !!c);
          this.categories = Array.from(new Set(cats));
        } else {
          this.errorMessage = res.EM || 'Không tải được hoạt động.';
        }
        this.isLoadingActivities = false;
        this.setupCompleted = true;
      },
      error: (err) => {
        console.error('Error loading activities:', err);
        this.errorMessage = 'Lỗi kết nối khi tải danh sách hoạt động.';
        this.isLoadingActivities = false;
      }
    });
  }

  filterActivities(): void {
    const query = this.searchQuery.toLowerCase().trim();
    this.filteredPool = this.activitiesPool.filter(act => {
      const matchesSearch = !query ||
        act.name.toLowerCase().includes(query) ||
        (act.description && act.description.toLowerCase().includes(query)) ||
        (act.location && act.location.toLowerCase().includes(query));

      const matchesCategory = !this.selectedCategory || act.category === this.selectedCategory;

      return matchesSearch && matchesCategory;
    });
  }

  onSearchChange(): void {
    this.filterActivities();
  }

  onCategoryChange(cat: string): void {
    this.selectedCategory = this.selectedCategory === cat ? '' : cat;
    this.filterActivities();
  }

  recalculatePrice(): void {
    let subtotal = 0;
    Object.values(this.itinerary).forEach(day => {
      if (Array.isArray(day.morning)) {
        day.morning.forEach(act => subtotal += act.price);
      }
      if (Array.isArray(day.afternoon)) {
        day.afternoon.forEach(act => subtotal += act.price);
      }
      if (Array.isArray(day.evening)) {
        day.evening.forEach(act => subtotal += act.price);
      }
    });
    this.totalPrice = subtotal * this.groupSize;
  }

  // --- Drag and Drop Handlers ---

  onPoolActivityDragStart(event: DragEvent, activity: ActivityPackage): void {
    console.log('Drag Start (Pool):', activity.name, activity.activity_id);
    if (event.dataTransfer) {
      event.dataTransfer.setData('text/plain', activity.activity_id);
      event.dataTransfer.effectAllowed = 'copyMove';
    }
    this.draggedPoolActivity = activity;
    this.draggedItineraryActivity = null;
    this.isDragging = true;
  }

  onItineraryActivityDragStart(event: DragEvent, dayKey: string, slot: string, activity: ActivityPackage | null, index: number): void {
    if (!activity) return;
    console.log('Drag Start (Itinerary):', activity.name, 'from', dayKey, slot, 'index', index);
    if (event.dataTransfer) {
      event.dataTransfer.setData('text/plain', activity.activity_id);
      event.dataTransfer.effectAllowed = 'move';
    }
    this.draggedItineraryActivity = { dayKey, slot, activity, index };
    this.draggedPoolActivity = null;
    this.isDragging = true;
  }

  onActivityDragOver(event: DragEvent, dayKey: string, slot: string): void {
    event.preventDefault();
    this.dragOverSlot = { dayKey, slot };
  }

  onActivityDragLeave(dayKey: string, slot: string): void {
    if (this.dragOverSlot?.dayKey === dayKey && this.dragOverSlot?.slot === slot) {
      this.dragOverSlot = null;
    }
  }

  isDragOver(dayKey: string, slot: string): boolean {
    return this.dragOverSlot?.dayKey === dayKey && this.dragOverSlot?.slot === slot;
  }

  onActivityDrop(event: DragEvent, targetDayKey: string, targetSlot: string): void {
    event.preventDefault();
    console.log('Drop Target:', targetDayKey, targetSlot);
    console.log('Dragged Pool Activity:', this.draggedPoolActivity?.name);
    console.log('Dragged Itinerary Activity:', this.draggedItineraryActivity?.activity?.name);

    // Reset drop indicator
    this.dragOverSlot = null;
    this.isDragging = false;

    if (this.draggedPoolActivity) {
      if (!this.itinerary[targetDayKey][targetSlot]) {
        this.itinerary[targetDayKey][targetSlot] = [];
      }
      this.itinerary[targetDayKey][targetSlot].push({ ...this.draggedPoolActivity });
      this.draggedPoolActivity = null;
    } else if (this.draggedItineraryActivity) {
      const fromDay = this.draggedItineraryActivity.dayKey;
      const fromSlot = this.draggedItineraryActivity.slot;
      const fromActivity = this.draggedItineraryActivity.activity;
      const fromIdx = this.draggedItineraryActivity.index;

      if (fromActivity) {
        this.itinerary[fromDay][fromSlot].splice(fromIdx, 1);
        if (!this.itinerary[targetDayKey][targetSlot]) {
          this.itinerary[targetDayKey][targetSlot] = [];
        }
        this.itinerary[targetDayKey][targetSlot].push(fromActivity);
      }

      this.draggedItineraryActivity = null;
    }

    this.recalculatePrice();
    this.cdr.detectChanges();
    console.log('Itinerary updated:', this.itinerary);
  }

  onDragEnd(): void {
    console.log('Drag End');
    this.isDragging = false;
    this.dragOverSlot = null;
    // Delay clearing references slightly so onActivityDrop has time to process them
    setTimeout(() => {
      this.draggedPoolActivity = null;
      this.draggedItineraryActivity = null;
      this.cdr.detectChanges();
    }, 300);
  }

  removeActivity(dayKey: string, slot: string, index: number): void {
    if (this.itinerary[dayKey] && this.itinerary[dayKey][slot]) {
      this.itinerary[dayKey][slot].splice(index, 1);
    }
    this.recalculatePrice();
    this.cdr.detectChanges();
  }

  autoFillItinerary(): void {
    const usedIds = new Set<string>();
    
    // Clear current slots
    for (let i = 1; i <= this.durationDays; i++) {
      this.itinerary[`day_${i}`] = {
        morning: [],
        afternoon: [],
        evening: []
      };
    }

    for (let i = 1; i <= this.durationDays; i++) {
      const dayKey = `day_${i}`;
      ['morning', 'afternoon', 'evening'].forEach(slot => {
        const candidates = this.activitiesPool.filter(act => {
          if (act.activity_id && usedIds.has(act.activity_id)) return false;
          return act.time_slot === slot || (act.time_slot as string) === 'full_day';
        });

        if (candidates.length > 0) {
          const selected = candidates[0];
          this.itinerary[dayKey][slot].push({ ...selected });
          if (selected.activity_id) {
            usedIds.add(selected.activity_id);
          }
        }
      });
    }

    this.recalculatePrice();
    this.cdr.detectChanges();
  }

  clearItinerary(): void {
    for (let i = 1; i <= this.durationDays; i++) {
      this.itinerary[`day_${i}`] = {
        morning: [],
        afternoon: [],
        evening: []
      };
    }
    this.recalculatePrice();
    this.cdr.detectChanges();
  }

  toggleReplacePanel(dayKey: string, slot: string): void {
    if (this.activeReplacePanel && this.activeReplacePanel.dayKey === dayKey && this.activeReplacePanel.slot === slot) {
      this.activeReplacePanel = null;
    } else {
      this.activeReplacePanel = { dayKey, slot };
    }
  }

  isReplacePanelOpen(dayKey: string, slot: string): boolean {
    return this.activeReplacePanel?.dayKey === dayKey && this.activeReplacePanel?.slot === slot;
  }

  getReplaceCandidates(dayKey: string, slot: string): ActivityPackage[] {
    const usedIds = new Set<string>();
    Object.values(this.itinerary).forEach(day => {
      ['morning', 'afternoon', 'evening'].forEach(s => {
        if (day[s]) {
          day[s].forEach(act => {
            if (act.activity_id) usedIds.add(act.activity_id);
          });
        }
      });
    });

    return this.activitiesPool.filter(act => {
      if (act.activity_id && usedIds.has(act.activity_id)) return false;
      return act.time_slot === slot || (act.time_slot as string) === 'full_day';
    }).slice(0, 5);
  }

  selectReplacement(dayKey: string, slot: string, activity: ActivityPackage): void {
    if (!this.itinerary[dayKey][slot]) {
      this.itinerary[dayKey][slot] = [];
    }
    this.itinerary[dayKey][slot].push({ ...activity });
    this.activeReplacePanel = null;
    this.recalculatePrice();
    this.cdr.detectChanges();
  }

  resetSetup(): void {
    this.setupCompleted = false;
    this.activitiesPool = [];
    this.filteredPool = [];
    this.itinerary = {};
    this.totalPrice = 0;
  }

  getItineraryDays(): { key: string; num: number; day: ItineraryDay }[] {
    const days: { key: string; num: number; day: ItineraryDay }[] = [];
    for (let i = 1; i <= this.durationDays; i++) {
      const key = `day_${i}`;
      if (this.itinerary[key]) {
        days.push({ key, num: i, day: this.itinerary[key] });
      }
    }
    return days;
  }

  formatPrice(price: number): string {
    return new Intl.NumberFormat('vi-VN', {
      style: 'currency',
      currency: 'VND'
    }).format(price);
  }

  checkout(): void {
    if (!this.currentUser) {
      this.errorMessage = 'Vui lòng đăng nhập để tiến hành đặt lịch trình tự chọn.';
      sessionStorage.setItem('redirect_after_login', '/activities');
      setTimeout(() => {
        this.router.navigate(['/login']);
      }, 2000);
      return;
    }

    // Check if at least one activity has been added
    let hasActivities = false;
    Object.values(this.itinerary).forEach(day => {
      if (day.morning?.length > 0 || day.afternoon?.length > 0 || day.evening?.length > 0) {
        hasActivities = true;
      }
    });

    if (!hasActivities) {
      this.errorMessage = 'Vui lòng chọn ít nhất một hoạt động cho lịch trình của bạn.';
      return;
    }

    this.isCheckingOut = true;
    this.errorMessage = '';
    this.successMessage = '';

    const payload = {
      destination: this.selectedDestination,
      duration_days: this.durationDays,
      group_size: this.groupSize,
      travel_date: this.travelDate,
      itinerary: this.itinerary,
      return_url: `${window.location.origin}/my-bookings?payment_success=true`
    };

    this.activityService.checkoutCustomItinerary(payload).subscribe({
      next: (res) => {
        if (res.EC === 0 && res.data && res.data.payment_url) {
          this.successMessage = 'Lập lịch trình thành công! Đang chuyển hướng đến VNPay để thanh toán...';
          sessionStorage.setItem('payment_return_url', '/my-bookings');
          setTimeout(() => {
            window.location.href = res.data.payment_url || '';
          }, 1500);
        } else {
          this.errorMessage = res.EM || 'Lỗi khi khởi tạo thanh toán.';
          this.isCheckingOut = false;
        }
      },
      error: (err) => {
        console.error('Checkout error:', err);
        this.errorMessage = err.error?.detail || err.error?.EM || 'Đã xảy ra lỗi trong quá trình đặt tour tự chọn.';
        this.isCheckingOut = false;
      }
    });
  }
}
