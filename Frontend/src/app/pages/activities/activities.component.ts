import { Component, OnInit, OnDestroy, ChangeDetectorRef, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { DialogModule } from 'primeng/dialog';
import * as QRCode from 'qrcode';
import { ActivityService, ActivityPackage } from '../../services/activity.service';
import { AuthStateService } from '../../services/auth-state.service';
import { SharedItineraryService, ItineraryPayload } from '../../services/shared-itinerary.service';
import { TripPlannerService } from '../../services/trip-planner.service';
import html2canvas from 'html2canvas';

/** A single placement of an activity inside a slot. A slot holds many of these,
 *  each optionally assigned to a "khung giờ" (time frame) via `time`. */
interface PlacedActivity {
  uid: string;
  activity: ActivityPackage;
  time?: string;
}

export interface ItineraryDay {
  morning: PlacedActivity[];
  afternoon: PlacedActivity[];
  evening: PlacedActivity[];
  [key: string]: PlacedActivity[];
}

interface SlotConfig {
  key: 'morning' | 'afternoon' | 'evening';
  label: string;
  short: string;
  /** Font Awesome icon class (without the fa-solid prefix). */
  icon: string;
  hint: string;
  /** Hex accent color — drives every per-slot visual via the `--slot-c` CSS var. */
  ring: string;
}

interface ItineraryDayView {
  key: string;
  num: number;
  day: ItineraryDay;
}

interface DraggedItineraryItem {
  dayKey: string;
  slot: string;
  uid: string;
}

interface DragOverTarget {
  dayKey: string;
  slot: string;
  index: number;
}

@Component({
  selector: 'app-activities',
  standalone: true,
  imports: [CommonModule, FormsModule, DialogModule],
  templateUrl: './activities.component.html',
  styleUrl: './activities.component.scss',
})
export class ActivitiesComponent implements OnInit, OnDestroy {
  // --- Setup state ---
  destinations: string[] = [];
  selectedDestination = '';
  travelDate = '';
  durationDays = 3;
  groupSize = 2;
  setupCompleted = false;

  // --- Loading & error states ---
  isLoadingDestinations = false;
  isLoadingActivities = false;
  isCheckingOut = false;
  isSharing = false;
  isOptimizing = false;
  /** Bảng giải thích sau khi AI tối ưu (mỗi dòng: ngày · buổi: thay đổi + lý do). */
  optimizeExplanation: string[] = [];
  optimizeWeather: { day: string; rain: boolean }[] = [];
  showOptimizePanel = false;
  errorMessage = '';
  successMessage = '';
  /** Transient toast for soft warnings (duplicate add, etc.). */
  infoMessage = '';

  // --- Activities pool ---
  activitiesPool: ActivityPackage[] = [];
  filteredPool: ActivityPackage[] = [];
  searchQuery = '';
  selectedCategory = '';
  categories: string[] = [];

  // --- Itinerary state ---
  itinerary: Record<string, ItineraryDay> = {};
  totalPrice = 0;

  // --- Drag & drop state ---
  isDragging = false;
  draggedPoolActivity: ActivityPackage | null = null;
  draggedItineraryActivity: DraggedItineraryItem | null = null;
  dragOverSlot: DragOverTarget | null = null;

  // --- UI / menus ---
  activeReplacePanel: { dayKey: string; slot: string } | null = null;
  activeClickToAddMenu: string | null = null;
  /** Optional time-frame the user is about to assign while the add panel is open. */
  pendingAddTime = '';
  isRollingSlot: Record<string, boolean> = {};

  currentUser: any = null;

  // --- Modes ---
  activeMode: 'manual' | 'ai' | 'surprise' | 'budget' = 'manual';
  selectedTheme = '';
  maxBudget: number | null = null;

  /** Theme presets drive the "AI theme" quick-fill. */
  readonly themes: Array<{ key: string; icon: string; name: string; sub: string; categories: string[] }> = [
    { key: 'relax', icon: 'fa-umbrella-beach', name: 'Nghỉ Dưỡng', sub: 'Thư giãn, nhẹ nhàng', categories: ['relax', 'spiritual', 'culture'] },
    { key: 'adventure', icon: 'fa-person-hiking', name: 'Trải Nghiệm', sub: 'Khám phá, vận động', categories: ['adventure', 'nature'] },
    { key: 'food', icon: 'fa-bowl-food', name: 'Ẩm Thực', sub: 'Đặc sản địa phương', categories: ['food', 'relax'] },
    { key: 'culture', icon: 'fa-landmark', name: 'Văn Hóa', sub: 'Lịch sử, tâm linh', categories: ['culture', 'spiritual', 'nature'] },
  ];

  // Slot configuration drives the per-day template so the markup stays DRY.
  readonly slots: SlotConfig[] = [
    { key: 'morning', label: 'Buổi Sáng', short: 'Sáng', icon: 'fa-sun', hint: 'sáng', ring: '#3b82f6' },
    { key: 'afternoon', label: 'Buổi Trưa / Chiều', short: 'Chiều', icon: 'fa-cloud-sun', hint: 'chiều', ring: '#f59e0b' },
    { key: 'evening', label: 'Buổi Tối', short: 'Tối', icon: 'fa-moon', hint: 'tối', ring: '#8b5cf6' },
  ];

  private rollTimers: Record<string, ReturnType<typeof setInterval>> = {};
  private infoTimer: ReturnType<typeof setTimeout> | null = null;
  private uidSeq = 0;

  constructor(
    private router: Router,
    private activityService: ActivityService,
    private authStateService: AuthStateService,
    private sharedItineraryService: SharedItineraryService,
    private tripPlannerService: TripPlannerService,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit(): void {
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    this.travelDate = tomorrow.toISOString().split('T')[0];

    this.loadDestinations();
    this.authStateService.currentUser$.subscribe(user => (this.currentUser = user));
  }

  ngOnDestroy(): void {
    Object.values(this.rollTimers).forEach(t => clearInterval(t));
    if (this.infoTimer !== null) {
      clearTimeout(this.infoTimer);
    }
  }

  /** Close the "add to day/slot" panel whenever the user clicks elsewhere. */
  @HostListener('document:click')
  onDocumentClick(): void {
    this.activeClickToAddMenu = null;
  }

  // ---------------------------------------------------------------------------
  // Data loading
  // ---------------------------------------------------------------------------

  loadDestinations(): void {
    this.isLoadingDestinations = true;
    this.activityService.getDestinations().subscribe({
      next: res => {
        if (res.EC === 0 && res.data) {
          this.destinations = res.data;
          if (this.destinations.length > 0 && !this.selectedDestination) {
            this.selectedDestination = this.destinations[0];
          }
        }
        this.isLoadingDestinations = false;
      },
      error: err => {
        console.error('Error loading destinations:', err);
        this.errorMessage = 'Không thể tải danh sách điểm đến. Vui lòng tải lại trang.';
        this.isLoadingDestinations = false;
      },
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
    // Guard against a departure in the past.
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const departure = new Date(this.travelDate + 'T00:00:00');
    if (Number.isNaN(departure.getTime()) || departure < today) {
      this.errorMessage = 'Ngày xuất phát không được trong quá khứ.';
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
    this.infoMessage = '';

    this.resetItineraryStructure();
    this.recalculatePrice();

    this.isLoadingActivities = true;
    this.activityService.getActivities({ destination: this.selectedDestination, limit: 50 }).subscribe({
      next: res => {
        if (res.EC === 0 && res.data) {
          this.activitiesPool = res.data;
          this.filterActivities();
          const cats = res.data.map(a => a.category).filter((c): c is string => !!c);
          this.categories = Array.from(new Set(cats));
        } else {
          this.errorMessage = res.EM || 'Không tải được hoạt động.';
        }
        this.isLoadingActivities = false;
        this.setupCompleted = true;
      },
      error: err => {
        console.error('Error loading activities:', err);
        this.errorMessage = 'Lỗi kết nối khi tải danh sách hoạt động.';
        this.isLoadingActivities = false;
      },
    });
  }

  filterActivities(): void {
    const query = this.searchQuery.toLowerCase().trim();
    this.filteredPool = this.activitiesPool.filter(act => {
      const matchesSearch =
        !query ||
        act.name.toLowerCase().includes(query) ||
        (act.description?.toLowerCase().includes(query)) ||
        (act.location?.toLowerCase().includes(query));
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

  clampDuration(value: number): void {
    this.durationDays = Math.max(1, Math.min(7, Math.floor(value) || 1));
  }

  clampGroup(value: number): void {
    this.groupSize = Math.max(1, Math.min(20, Math.floor(value) || 1));
  }

  stepDuration(direction: 1 | -1): void {
    this.durationDays = Math.max(1, Math.min(7, this.durationDays + direction));
  }

  stepGroup(direction: 1 | -1): void {
    this.groupSize = Math.max(1, Math.min(20, this.groupSize + direction));
  }

  // ---------------------------------------------------------------------------
  // Pricing
  // ---------------------------------------------------------------------------

  recalculatePrice(): void {
    let subtotal = 0;
    Object.values(this.itinerary).forEach(day => {
      this.slots.forEach(s => {
        const arr = day[s.key];
        if (Array.isArray(arr)) arr.forEach(p => (subtotal += p.activity.price || 0));
      });
    });
    this.totalPrice = subtotal * this.groupSize;
  }

  get selectedActivitiesCount(): number {
    let count = 0;
    Object.values(this.itinerary).forEach(day => {
      this.slots.forEach(s => (count += day[s.key]?.length || 0));
    });
    return count;
  }

  // ---------------------------------------------------------------------------
  // Drag & drop
  // ---------------------------------------------------------------------------

  onPoolActivityDragStart(event: DragEvent, activity: ActivityPackage): void {
    if (event.dataTransfer) {
      event.dataTransfer.setData('text/plain', activity.activity_id);
      event.dataTransfer.effectAllowed = 'copy';
    }
    this.draggedPoolActivity = activity;
    this.draggedItineraryActivity = null;
    this.isDragging = true;
  }

  onItineraryActivityDragStart(
    event: DragEvent,
    dayKey: string,
    slot: string,
    placed: PlacedActivity,
  ): void {
    if (event.dataTransfer) {
      event.dataTransfer.setData('text/plain', placed.uid);
      event.dataTransfer.effectAllowed = 'move';
    }
    this.draggedItineraryActivity = { dayKey, slot, uid: placed.uid };
    this.draggedPoolActivity = null;
    this.isDragging = true;
  }

  onActivityDragOver(event: DragEvent, dayKey: string, slot: string): void {
    event.preventDefault();
    if (event.dataTransfer) {
      event.dataTransfer.dropEffect = this.draggedItineraryActivity ? 'move' : 'copy';
    }
    const index = this.computeDropIndex(event);
    const current = this.dragOverSlot;
    if (!current || current.dayKey !== dayKey || current.slot !== slot || current.index !== index) {
      this.dragOverSlot = { dayKey, slot, index };
    }
  }

  /**
   * Determine where within a slot the pointer is so we can both render an
   * insertion indicator and place the dropped item at the correct index
   * (enabling reorder inside the same slot).
   */
  private computeDropIndex(event: DragEvent): number {
    const container = event.currentTarget as HTMLElement | null;
    if (!container) return 0;
    const items = Array.from(container.querySelectorAll<HTMLElement>('[data-dnd-item]'));
    if (items.length === 0) return 0;
    const y = event.clientY;
    for (let i = 0; i < items.length; i++) {
      const rect = items[i].getBoundingClientRect();
      if (y < rect.top + rect.height / 2) return i;
    }
    return items.length;
  }

  onActivityDragLeave(event: DragEvent, dayKey: string, slot: string): void {
    const container = event.currentTarget as HTMLElement | null;
    const related = event.relatedTarget as Node | null;
    if (related && container && container.contains(related)) return;
    if (this.dragOverSlot?.dayKey === dayKey && this.dragOverSlot?.slot === slot) {
      this.dragOverSlot = null;
    }
  }

  onActivityDrop(event: DragEvent, targetDayKey: string, targetSlot: string): void {
    event.preventDefault();
    const over = this.dragOverSlot;
    let insertIndex =
      over && over.dayKey === targetDayKey && over.slot === targetSlot ? over.index : 0;

    if (this.draggedPoolActivity) {
      // Copy from the pool — no time assigned yet; lands at the drop position.
      this.insertPlaced(this.draggedPoolActivity, targetDayKey, targetSlot, undefined, insertIndex);
      this.draggedPoolActivity = null;
    } else if (this.draggedItineraryActivity) {
      // Move within the itinerary — a reorder, never a duplicate.
      const { dayKey: fromDay, slot: fromSlot, uid } = this.draggedItineraryActivity;
      const fromArr = this.itinerary[fromDay]?.[fromSlot] || [];
      const i = fromArr.findIndex(p => p.uid === uid);
      if (i !== -1) {
        const moved = fromArr[i];
        // Remove from source (immutable reassign → guarantees re-render).
        const newFrom = fromArr.filter(p => p.uid !== uid);
        this.setSlot(fromDay, fromSlot, newFrom);
        // Insert into target (immutable).
        const base = fromDay === targetDayKey && fromSlot === targetSlot ? newFrom : this.ensureSlot(targetDayKey, targetSlot);
        let idx = insertIndex;
        if (fromDay === targetDayKey && fromSlot === targetSlot && i < idx) {
          idx = Math.max(0, idx - 1);
        }
        const newTarget = [...base];
        newTarget.splice(idx, 0, moved);
        this.setSlot(targetDayKey, targetSlot, newTarget);
        this.afterItineraryChange();
      }
      this.draggedItineraryActivity = null;
    }

    this.dragOverSlot = null;
    this.isDragging = false;
  }

  onDragEnd(): void {
    this.isDragging = false;
    this.dragOverSlot = null;
    this.draggedPoolActivity = null;
    this.draggedItineraryActivity = null;
  }

  isDragOver(dayKey: string, slot: string): boolean {
    return !!this.dragOverSlot && this.dragOverSlot.dayKey === dayKey && this.dragOverSlot.slot === slot;
  }

  isDropIndicator(dayKey: string, slot: string, index: number): boolean {
    return (
      !!this.dragOverSlot &&
      this.dragOverSlot.dayKey === dayKey &&
      this.dragOverSlot.slot === slot &&
      this.dragOverSlot.index === index
    );
  }

  isDraggingSource(dayKey: string, slot: string, uid: string): boolean {
    const d = this.draggedItineraryActivity;
    return !!d && d.dayKey === dayKey && d.slot === slot && d.uid === uid;
  }

  removeActivity(dayKey: string, slot: string, uid: string): void {
    const arr = this.itinerary[dayKey]?.[slot];
    if (!arr) return;
    this.setSlot(dayKey, slot, arr.filter(p => p.uid !== uid));
    this.afterItineraryChange();
  }

  // ---------------------------------------------------------------------------
  // Adding activities (single source of truth — keeps duplicate logic tight)
  // ---------------------------------------------------------------------------

  /**
   * Insert an activity into a slot. The SAME activity may appear in different
   * slots/days — only an identical repeat within the SAME slot is rejected.
   * When `time` is provided the item is placed in its chronological khung giờ.
   * Returns true on success.
   */
  private insertPlaced(
    activity: ActivityPackage,
    dayKey: string,
    slot: string,
    time: string | undefined,
    atIndex?: number,
  ): boolean {
    const id = activity.activity_id;
    const arr = this.ensureSlot(dayKey, slot);
    if (id && arr.some(p => p.activity.activity_id === id)) {
      this.flashInfo(`"${activity.name}" đã có trong buổi này rồi.`);
      return false;
    }
    const placed: PlacedActivity = { uid: this.nextUid(), activity: { ...activity }, time };
    const index = atIndex !== undefined ? atIndex : this.sortedInsertIndex(arr, time);
    // Immutable reassign so *ngFor always sees a fresh iterable and re-renders.
    const next = [...arr];
    next.splice(index, 0, placed);
    this.setSlot(dayKey, slot, next);
    this.afterItineraryChange();
    return true;
  }

  /** Optional khung giờ assigned from the inline add panel. */
  addToItineraryDirectly(activity: ActivityPackage, dayKey: string, slot: string): void {
    const ok = this.insertPlaced(activity, dayKey, slot, this.pendingAddTime || undefined);
    if (ok) {
      const dayNum = dayKey.replace('day_', '');
      const slotLabel = this.slots.find(s => s.key === slot)?.short || slot;
      this.flashInfo(`Đã thêm "${activity.name}" vào Ngày ${dayNum} · ${slotLabel}.`);
      this.cdr.detectChanges();
    }
  }

  selectReplacement(dayKey: string, slot: string, activity: ActivityPackage): void {
    if (this.insertPlaced(activity, dayKey, slot, undefined)) {
      this.activeReplacePanel = null;
    }
  }

  /** Change the khung giờ of an already-placed activity. */
  setItemTime(dayKey: string, slot: string, uid: string, time: string): void {
    const arr = this.ensureSlot(dayKey, slot);
    this.setSlot(dayKey, slot, arr.map(p => (p.uid === uid ? { ...p, time: time || undefined } : p)));
    this.afterItineraryChange();
  }

  private flashInfo(message: string): void {
    this.infoMessage = message;
    if (this.infoTimer !== null) {
      clearTimeout(this.infoTimer);
    }
    this.infoTimer = setTimeout(() => {
      this.infoMessage = '';
      this.infoTimer = null;
      this.cdr.detectChanges();
    }, 2800);
  }

  // ---------------------------------------------------------------------------
  // Auto-fill & quick actions
  // ---------------------------------------------------------------------------

  autoFillItinerary(): void {
    this.resetItineraryStructure();
    const used = new Set<string>();
    for (let i = 1; i <= this.durationDays; i++) {
      const dayKey = `day_${i}`;
      this.slots.forEach(s => {
        const picked = this.pickActivityForSlot(s.key, used);
        if (picked) {
          this.itinerary[dayKey][s.key].push({ uid: this.nextUid(), activity: { ...picked } });
          if (picked.activity_id) used.add(picked.activity_id);
        }
      });
    }
    this.afterItineraryChange();
  }

  clearItinerary(): void {
    this.resetItineraryStructure();
    this.recalculatePrice();
  }

  autoFillByTheme(themeKey: string): void {
    this.selectedTheme = themeKey;
    const theme = this.themes.find(t => t.key === themeKey);
    const allowed = theme?.categories || [];

    this.resetItineraryStructure();
    const used = new Set<string>();
    for (let i = 1; i <= this.durationDays; i++) {
      const dayKey = `day_${i}`;
      this.slots.forEach(s => {
        const themed = this.activitiesPool.filter(act => {
          if (act.activity_id && used.has(act.activity_id)) return false;
          const slotOk = act.time_slot === s.key || (act.time_slot as string) === 'full_day';
          return slotOk && allowed.includes(act.category || '');
        });
        const pool = themed.length > 0 ? themed : this.getAvailableCandidates(s.key, used);
        if (pool.length > 0) {
          const picked = pool[Math.floor(Math.random() * Math.min(3, pool.length))];
          this.itinerary[dayKey][s.key].push({ uid: this.nextUid(), activity: { ...picked } });
          if (picked.activity_id) used.add(picked.activity_id);
        }
      });
    }
    this.afterItineraryChange();
  }

  /** Gọi backend AI optimizer: gap-fill slot trống + thời tiết + preference.
   *  Giữ nguyên activity user đã đặt, chỉ bổ sung chỗ trống + gợi ý. */
  async optimizeWithAI(): Promise<void> {
    if (!this.selectedDestination) {
      this.flashInfo('Hãy chọn điểm đến trước.');
      return;
    }
    if (this.activitiesPool.length === 0) {
      this.flashInfo('Chưa tải được hoạt động để tối ưu.');
      return;
    }
    this.isOptimizing = true;
    try {
      const theme = this.themes.find(t => t.key === this.selectedTheme);
      const prefs = theme?.categories || [];
      const result = await this.tripPlannerService.optimizeItinerary(
        this.serializeItineraryForCheckout(),
        this.selectedDestination,
        this.durationDays,
        prefs,
        this.travelDate,
      );
      if (result?.EC === 0 && result.data?.itinerary) {
        // Rebuild itinerary từ kết quả optimizer (user's activities + slot fills).
        this.itinerary = {};
        Object.entries(result.data.itinerary).forEach(([dayKey, day]) => {
          const toPlaced = (arr: any[]) => (arr || []).map(a => ({ uid: this.nextUid(), activity: { ...a } }));
          this.itinerary[dayKey] = {
            morning: toPlaced(day.morning),
            afternoon: toPlaced(day.afternoon),
            evening: toPlaced(day.evening),
          };
        });
        this.optimizeExplanation = result.data.explanation || [];
        this.optimizeWeather = result.data.weather || [];
        this.showOptimizePanel = this.optimizeExplanation.length > 0;
        this.activeMode = 'ai';
        this.afterItineraryChange();
        this.flashInfo('✨ Đã tối ưu lịch trình bằng AI.');
      } else {
        this.flashInfo(result?.EM || 'Không tối ưu được lịch trình.');
      }
    } catch (e: any) {
      this.flashInfo(e?.message || 'Lỗi khi tối ưu lịch trình.');
    } finally {
      this.isOptimizing = false;
    }
  }

  closeOptimizePanel(): void {
    this.showOptimizePanel = false;
  }

  rollSurpriseActivity(dayKey: string, slot: string): void {
    const slotKey = `${dayKey}_${slot}`;
    if (this.isRollingSlot[slotKey]) return;

    const candidates = this.getAvailableCandidates(slot);
    if (candidates.length === 0) {
      this.flashInfo('Không còn hoạt động phù hợp cho buổi này.');
      return;
    }

    this.isRollingSlot[slotKey] = true;
    const targetSlot = this.ensureSlot(dayKey, slot);
    const original = [...targetSlot];

    let rollCount = 0;
    const maxRolls = 6;
    const timer = setInterval(() => {
      const temp = candidates[Math.floor(Math.random() * candidates.length)];
      this.itinerary[dayKey][slot] = [{ uid: this.nextUid(), activity: { ...temp } }];
      this.recalculatePrice();
      this.cdr.detectChanges();

      rollCount++;
      if (rollCount >= maxRolls) {
        clearInterval(timer);
        delete this.rollTimers[slotKey];
        this.isRollingSlot[slotKey] = false;
        if (!this.itinerary[dayKey]?.[slot]?.length) {
          this.itinerary[dayKey][slot] = original;
        }
        this.afterItineraryChange();
        this.cdr.detectChanges();
      }
    }, 140);
    this.rollTimers[slotKey] = timer;
  }

  toggleReplacePanel(dayKey: string, slot: string): void {
    this.activeReplacePanel =
      this.activeReplacePanel?.dayKey === dayKey && this.activeReplacePanel?.slot === slot
        ? null
        : { dayKey, slot };
  }

  isReplacePanelOpen(dayKey: string, slot: string): boolean {
    return this.activeReplacePanel?.dayKey === dayKey && this.activeReplacePanel?.slot === slot;
  }

  getReplaceCandidates(_dayKey: string, slot: string): ActivityPackage[] {
    return this.getAvailableCandidates(slot).slice(0, 5);
  }

  toggleClickToAddMenu(activityId: string, event: Event): void {
    event.stopPropagation();
    this.activeClickToAddMenu = this.activeClickToAddMenu === activityId ? null : activityId;
  }

  resetSetup(): void {
    this.setupCompleted = false;
    this.activitiesPool = [];
    this.filteredPool = [];
    this.itinerary = {};
    this.totalPrice = 0;
    this.activeMode = 'manual';
    this.selectedTheme = '';
    this.maxBudget = null;
    this.pendingAddTime = '';
  }

  // ---------------------------------------------------------------------------
  // Budget
  // ---------------------------------------------------------------------------

  isBudgetExceeded(): boolean {
    return this.maxBudget !== null && this.maxBudget > 0 && this.totalPrice > this.maxBudget;
  }

  getBudgetPercentage(): number {
    if (this.maxBudget === null || this.maxBudget === 0) return 0;
    return Math.min(100, (this.totalPrice / this.maxBudget) * 100);
  }

  /** Checkout is blocked while working, when empty, or when over budget. */
  get canCheckout(): boolean {
    return !this.isCheckingOut && this.selectedActivitiesCount > 0 && !this.isBudgetExceeded();
  }

  // ---------------------------------------------------------------------------
  // Checkout
  // ---------------------------------------------------------------------------

  checkout(): void {
    if (!this.currentUser) {
      this.errorMessage = 'Vui lòng đăng nhập để tiến hành đặt lịch trình tự chọn.';
      sessionStorage.setItem('redirect_after_login', '/activities');
      setTimeout(() => this.router.navigate(['/login']), 2000);
      return;
    }

    if (this.selectedActivitiesCount === 0) {
      this.errorMessage = 'Vui lòng chọn ít nhất một hoạt động cho lịch trình của bạn.';
      return;
    }

    if (this.isBudgetExceeded()) {
      this.errorMessage = `Tổng chi phí vượt ngân sách ${formatPriceDiff(
        this.totalPrice - (this.maxBudget || 0),
      )}. Vui lòng điều chỉnh lại.`;
      return;
    }

    this.isCheckingOut = true;
    this.errorMessage = '';
    this.successMessage = '';
    this.infoMessage = '';

    const payload = {
      destination: this.selectedDestination,
      duration_days: this.durationDays,
      group_size: this.groupSize,
      travel_date: this.travelDate,
      // Flatten PlacedActivity back to ActivityPackage (with optional `time`) so
      // the backend contract (price/activity_id/name) is unchanged.
      itinerary: this.serializeItineraryForCheckout(),
      return_url: `${window.location.origin}/my-bookings?payment_success=true`,
    };

    this.activityService.checkoutCustomItinerary(payload as any).subscribe({
      next: res => {
        if (res.EC === 0 && res.data?.payment_url) {
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
      error: err => {
        console.error('Checkout error:', err);
        this.errorMessage =
          err.error?.detail || err.error?.EM || 'Đã xảy ra lỗi trong quá trình đặt tour tự chọn.';
        this.isCheckingOut = false;
      },
    });
  }

  // ---------------------------------------------------------------------------
  // Share itinerary as image (quảng bá qua mạng xã hội)
  // ---------------------------------------------------------------------------

  /**
   * Render poster lịch trình (off-screen, text-only để tránh CORS taint) thành PNG
   * qua html2canvas, rồi dùng Web Share API (nếu hỗ trợ) hoặc tải file về.
   */
  async shareItinerary(): Promise<void> {
    if (this.selectedActivitiesCount === 0) {
      this.flashInfo('Hãy thêm ít nhất một hoạt động để chia sẻ.');
      return;
    }
    this.isSharing = true;
    this.errorMessage = '';
    try {
      const el = document.querySelector<HTMLElement>('.share-poster');
      if (!el) throw new Error('Không tạo được ảnh lịch trình.');
      // Chờ một frame để chắc chắn poster đã render với dữ liệu mới nhất.
      await new Promise(r => requestAnimationFrame(() => r(null)));
      const canvas = await html2canvas(el, {
        backgroundColor: '#ffffff',
        scale: 2,
        useCORS: true,
        logging: false,
      });
      const blob: Blob | null = await new Promise(resolve => canvas.toBlob(b => resolve(b), 'image/png'));
      if (!blob) throw new Error('Không tạo được file ảnh.');

      const fileName = `UITravel-${(this.selectedDestination || 'lich-trinh').replace(/\s+/g, '-')}.png`;
      const navAny = navigator as any;
      const file = new File([blob], fileName, { type: 'image/png' });

      if (navAny.canShare && navAny.canShare({ files: [file] })) {
        await navAny.share({
          files: [file],
          title: `Lịch trình ${this.selectedDestination}`,
          text: `Lịch trình ${this.selectedDestination} do tôi tự thiết kế trên UITravel!`,
        });
      } else {
        // Fallback: tải ảnh về để user tự đăng lên MXH.
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = fileName;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
        this.flashInfo('Đã tải ảnh lịch trình — hãy chia sẻ lên mạng xã hội nhé!');
      }
    } catch (e: any) {
      // AbortError = user tự hủy khung share -> không báo lỗi.
      if (e?.name !== 'AbortError') {
        this.errorMessage = e?.message || 'Không thể chia sẻ lịch trình lúc này.';
      }
    } finally {
      this.isSharing = false;
    }
  }

  // --- Share via QR + public link (backend persistence) ---
  shareLinkVisible = false;
  shareUrl = '';
  shareQr = '';
  isShareLinkLoading = false;
  shareLinkError = '';
  shareLinkCopied = false;

  /** Đóng gói trạng thái lịch trình hiện tại thành payload để lưu & chia sẻ. */
  buildItineraryPayload(): ItineraryPayload {
    const days = this.getItineraryDays().map(d => ({
      day: d.num,
      morning: this.getSlotItems(d.day, this.slots[0]).map(p => p.activity.name),
      afternoon: this.getSlotItems(d.day, this.slots[1]).map(p => p.activity.name),
      evening: this.getSlotItems(d.day, this.slots[2]).map(p => p.activity.name),
    }));
    return {
      destination: this.selectedDestination || '',
      travel_date: this.travelDate || '',
      duration_days: this.durationDays,
      group_size: this.groupSize,
      total_price: this.totalPrice,
      days,
    };
  }

  /** Mở dialog QR + link: tạo share backend -> sinh QR -> hiển thị. */
  async openShareLink(): Promise<void> {
    if (this.selectedActivitiesCount === 0) {
      this.flashInfo('Hãy thêm ít nhất một hoạt động để chia sẻ.');
      return;
    }
    this.shareLinkVisible = true;
    this.isShareLinkLoading = true;
    this.shareLinkError = '';
    this.shareUrl = '';
    this.shareQr = '';
    this.shareLinkCopied = false;
    try {
      const title = this.selectedDestination
        ? `${this.selectedDestination} ${this.durationDays} ngày`
        : 'Lịch trình UITravel';
      const res = await this.sharedItineraryService.createShare(this.buildItineraryPayload(), title);
      this.shareUrl = res.url || '';
      if (this.shareUrl) {
        this.shareQr = await QRCode.toDataURL(this.shareUrl, { width: 240, margin: 1 });
      }
    } catch (e: any) {
      this.shareLinkError = e?.message || 'Không tạo được link chia sẻ lúc này.';
    } finally {
      this.isShareLinkLoading = false;
    }
  }

  closeShareLink(): void {
    this.shareLinkVisible = false;
  }

  async copyShareLink(): Promise<void> {
    if (!this.shareUrl) return;
    try {
      await navigator.clipboard.writeText(this.shareUrl);
      this.shareLinkCopied = true;
      setTimeout(() => (this.shareLinkCopied = false), 2000);
    } catch {
      this.flashInfo('Không sao chép được — hãy copy thủ công từ ô link.');
    }
  }

  // ---------------------------------------------------------------------------
  // View helpers
  // ---------------------------------------------------------------------------

  getItineraryDays(): ItineraryDayView[] {
    const days: ItineraryDayView[] = [];
    for (let i = 1; i <= this.durationDays; i++) {
      const key = `day_${i}`;
      if (this.itinerary[key]) days.push({ key, num: i, day: this.itinerary[key] });
    }
    return days;
  }

  trackDayKey(_: number, day: ItineraryDayView): string {
    return day.key;
  }

  trackPlacedUid(_: number, placed: PlacedActivity): string {
    return placed.uid;
  }

  /** ISO date string for today — used to clamp the departure `<input type="date">`. */
  todayISO(): string {
    const t = new Date();
    t.setHours(0, 0, 0, 0);
    const mm = String(t.getMonth() + 1).padStart(2, '0');
    const dd = String(t.getDate()).padStart(2, '0');
    return `${t.getFullYear()}-${mm}-${dd}`;
  }

  getSlotItems(day: ItineraryDay, slot: SlotConfig): PlacedActivity[] {
    return day[slot.key] || [];
  }

  slotActivityCount(day: ItineraryDay, slot: SlotConfig): number {
    return day[slot.key]?.length || 0;
  }

  /** True when an item should open a new "khung giờ" header (time differs from previous). */
  isFrameStart(items: PlacedActivity[], i: number): boolean {
    if (i === 0) return true;
    return (items[i].time || '') !== (items[i - 1].time || '');
  }

  frameLabel(time?: string): string {
    return time ? time : 'Linh hoạt';
  }

  /** Count how many times an activity already appears across the itinerary (for the pool badge). */
  activityUsageCount(activityId: string): number {
    let count = 0;
    Object.values(this.itinerary).forEach(day => {
      this.slots.forEach(s => {
        count += day[s.key]?.filter(p => p.activity.activity_id === activityId).length || 0;
      });
    });
    return count;
  }

  formatPrice(price: number): string {
    return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(price || 0);
  }

  // ---------------------------------------------------------------------------
  // Private helpers
  // ---------------------------------------------------------------------------

  private nextUid(): string {
    this.uidSeq += 1;
    return 'p' + this.uidSeq;
  }

  /** Insertion index that keeps a slot sorted by time (blank times last). */
  private sortedInsertIndex(arr: PlacedActivity[], time?: string): number {
    if (!time) return arr.length;
    for (let i = 0; i < arr.length; i++) {
      const t = arr[i].time;
      if (!t) return i;
      if (time < t) return i;
    }
    return arr.length;
  }

  private serializeItineraryForCheckout(): Record<string, Record<string, any[]>> {
    const out: Record<string, Record<string, any[]>> = {};
    Object.entries(this.itinerary).forEach(([dayKey, day]) => {
      out[dayKey] = {};
      this.slots.forEach(s => {
        out[dayKey][s.key] = (day[s.key] || []).map(p =>
          p.time ? { ...p.activity, time: p.time } : { ...p.activity },
        );
      });
    });
    return out;
  }

  private resetItineraryStructure(): void {
    this.itinerary = {};
    for (let i = 1; i <= this.durationDays; i++) {
      this.itinerary[`day_${i}`] = { morning: [], afternoon: [], evening: [] };
    }
  }

  private ensureSlot(dayKey: string, slot: string): PlacedActivity[] {
    if (!this.itinerary[dayKey]) {
      this.itinerary[dayKey] = { morning: [], afternoon: [], evening: [] };
    }
    if (!Array.isArray(this.itinerary[dayKey][slot])) {
      this.itinerary[dayKey][slot] = [];
    }
    return this.itinerary[dayKey][slot];
  }

  /** Replace a slot's array with a new reference so change detection always
   *  picks up the change (avoids "data changed but view didn't update"). */
  private setSlot(dayKey: string, slot: string, arr: PlacedActivity[]): void {
    this.ensureSlot(dayKey, slot);
    this.itinerary[dayKey][slot] = arr;
  }

  private collectUsedIds(): Set<string> {
    const used = new Set<string>();
    Object.values(this.itinerary).forEach(day => {
      this.slots.forEach(s => {
        day[s.key]?.forEach(p => {
          if (p.activity.activity_id) used.add(p.activity.activity_id);
        });
      });
    });
    return used;
  }

  private getAvailableCandidates(slot: string, used: Set<string> = this.collectUsedIds()): ActivityPackage[] {
    return this.activitiesPool.filter(act => {
      if (act.activity_id && used.has(act.activity_id)) return false;
      return act.time_slot === slot || (act.time_slot as string) === 'full_day';
    });
  }

  private pickActivityForSlot(slot: string, used: Set<string>): ActivityPackage | null {
    const candidates = this.getAvailableCandidates(slot, used);
    if (candidates.length === 0) return null;
    return candidates[Math.floor(Math.random() * candidates.length)];
  }

  private afterItineraryChange(): void {
    this.recalculatePrice();
  }
}

/** Module-level helper for the budget-exceeded message (keeps the template tidy). */
function formatPriceDiff(amount: number): string {
  return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(amount);
}
