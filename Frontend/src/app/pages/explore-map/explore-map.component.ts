import { AfterViewInit, Component, NgZone, OnDestroy, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import * as L from 'leaflet';
import { MessageService } from 'primeng/api';
import { ToastModule } from 'primeng/toast';
import { ProgressSpinnerModule } from 'primeng/progressspinner';
import { VisitedProvinceService, Province } from '../../services/visited-province.service';
import { AuthStateService } from '../../services/auth-state.service';
import { PlaceService, PlaceSuggestion } from '../../services/place.service';
import { PlaceCollectionService, CombinedCollection, SavedPlace } from '../../services/place-collection.service';

const CATEGORY_LABELS: Record<string, string> = {
    attraction: 'Điểm tham quan',
    museum: 'Bảo tàng',
    viewpoint: 'Điểm ngắm cảnh',
    historic: 'Di tích lịch sử',
    park: 'Công viên / Vườn',
    theme_park: 'Công viên giải trí'
};

@Component({
    selector: 'app-explore-map',
    imports: [CommonModule, FormsModule, ToastModule, ProgressSpinnerModule],
    providers: [MessageService],
    templateUrl: './explore-map.component.html',
    styleUrl: './explore-map.component.scss'
})
export class ExploreMapComponent implements OnInit, AfterViewInit, OnDestroy {
    isLoading = true;
    isSyncing = false;
    errorMsg: string | null = null;

    mode: 'vn' | 'world' = 'vn';

    // ---- Vietnam mode ----
    allProvinces: Province[] = [];
    private byName = new Map<string, Province>();
    private layerByProvinceId = new Map<string, L.Path>();

    totalVisited = 0;
    totalProvinces = 63;
    north = 0;
    central = 0;
    south = 0;
    progress = 0;

    // ---- World mode ----
    worldQuery = '';
    worldResults: PlaceSuggestion[] = [];
    worldLoading = false;
    worldLoadingMore = false;
    worldError: string | null = null;
    worldLocationName: string | null = null;
    worldTotal = 0;
    private worldOffset = 0;
    private readonly worldPageSize = 12;
    private readonly worldRadiusKm = 20;
    private worldMarkers = L.layerGroup();
    private placeByOsm = new Map<number, PlaceSuggestion>();

    // ---- Collection (bộ sưu tập) ----
    showCollection = false;
    collectionLoading = false;
    collectionData: CombinedCollection | null = null;

    private map?: L.Map;
    private geoLayer?: L.GeoJSON;

    constructor(
        private visitedService: VisitedProvinceService,
        private authState: AuthStateService,
        private router: Router,
        private messageService: MessageService,
        private ngZone: NgZone,
        private placeService: PlaceService,
        private collectionService: PlaceCollectionService
    ) {}

    ngOnInit(): void {
        if (!this.authState.getIsAuthenticated()) {
            this.router.navigate(['/login']);
            return;
        }
    }

    async ngAfterViewInit(): Promise<void> {
        try {
            await this.loadData();
        } catch (e: any) {
            this.errorMsg = e?.message || 'Không tải được dữ liệu bản đồ.';
        } finally {
            this.isLoading = false;
            this.initMap();
        }
    }

    ngOnDestroy(): void {
        this.map?.remove();
        this.map = undefined;
    }

    private async loadData(): Promise<void> {
        const [visited, all] = await Promise.all([
            this.visitedService.getMyVisited(),
            this.visitedService.getAllProvinces()
        ]);
        this.allProvinces = all.provinces || [];
        this.byName = new Map(this.allProvinces.map(p => [p.province_name, p]));
        this.applyStats(visited);
    }

    private applyStats(v: any): void {
        this.totalVisited = v.total || 0;
        this.totalProvinces = v.total_provinces || 63;
        this.north = v.north_count || 0;
        this.central = v.central_count || 0;
        this.south = v.south_count || 0;
        this.progress = this.roundProgress();
    }

    private roundProgress(): number {
        return Math.round(((this.totalVisited / this.totalProvinces) * 100) * 10) / 10;
    }

    private styleForName(name: string): L.PathOptions {
        const prov = this.byName.get(name);
        const isVisited = !!(prov && this.visitedService.isVisited(prov.province_id));
        return isVisited
            ? { weight: 1.5, color: '#047857', fillColor: '#10b981', fillOpacity: 0.7 }
            : { weight: 1, color: '#9ca3af', fillColor: '#e5e7eb', fillOpacity: 0.4 };
    }

    private initMap(): void {
        if (this.map) return;
        const el = document.getElementById('vn-map');
        if (!el) return;

        this.ngZone.runOutsideAngular(() => {
            this.map = L.map(el, { scrollWheelZoom: true, worldCopyJump: true }).setView([16.2, 107.6], 5);
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                maxZoom: 18,
                attribution: '© OpenStreetMap contributors'
            }).addTo(this.map!);
            this.worldMarkers.addTo(this.map!);

            // Wire nút "Lưu" trong popup (HTML tĩnh -> gắn listener thủ công).
            this.map!.on('popupopen', (e: any) => this.wirePopupActions(e.popup));
        });

        fetch('/assets/vietnam-provinces.geojson')
            .then(res => {
                if (!res.ok) throw new Error('geojson');
                return res.json();
            })
            .then((data: any) => {
                this.ngZone.runOutsideAngular(() => {
                    this.geoLayer = L.geoJSON(data, {
                        style: (feat: any) => this.styleForName(feat?.properties?.name),
                        onEachFeature: (feat: any, layer: any) => {
                            const prov = this.byName.get(feat?.properties?.name);
                            if (prov) this.layerByProvinceId.set(prov.province_id, layer);
                            layer.bindTooltip(feat?.properties?.name || '', { sticky: true });
                            layer.on('click', () => this.onProvinceClick(prov));
                        }
                    }).addTo(this.map!);
                    this.map?.invalidateSize();
                });
            })
            .catch(() => {
                this.ngZone.run(() => (this.errorMsg = 'Không tải được bản đồ Việt Nam.'));
            });
    }

    // ============================ mode switching ============================
    switchMode(m: 'vn' | 'world'): void {
        if (this.mode === m) return;
        this.mode = m;
        this.ngZone.runOutsideAngular(() => {
            if (!this.map) return;
            if (m === 'vn') {
                this.worldMarkers.clearLayers();
                if (this.geoLayer && !this.map.hasLayer(this.geoLayer)) {
                    this.geoLayer.addTo(this.map);
                }
                this.map.setView([16.2, 107.6], 5);
            } else {
                if (this.geoLayer && this.map.hasLayer(this.geoLayer)) {
                    this.map.removeLayer(this.geoLayer);
                }
                this.map.setView([20, 0], 2);
            }
            this.map.invalidateSize();
        });
    }

    // ============================ World search ============================
    async searchWorld(): Promise<void> {
        const q = this.worldQuery.trim();
        if (!q) return;
        this.worldLoading = true;
        this.worldError = null;
        this.worldOffset = 0;
        try {
            const res = await this.placeService.suggest(q, this.worldPageSize, this.worldRadiusKm, 0);
            if (res.EC !== 0 || !res.places?.length) {
                this.worldResults = [];
                this.worldTotal = 0;
                this.worldLocationName = null;
                this.worldError = res.EM || `Không tìm thấy điểm tham quan quanh "${q}".`;
                this.worldMarkers.clearLayers();
                this.placeByOsm.clear();
                return;
            }
            this.worldResults = res.places;
            this.worldTotal = res.total ?? res.places.length;
            this.worldLocationName = res.location?.display_name || q;
            this.addMarkers(res.places, true, res.location!);
        } catch (e: any) {
            this.worldError = e?.message || 'Lỗi khi tìm kiếm địa điểm.';
            this.worldResults = [];
            this.worldTotal = 0;
            this.worldMarkers.clearLayers();
            this.placeByOsm.clear();
        } finally {
            this.worldLoading = false;
        }
    }

    get hasMorePlaces(): boolean {
        return this.worldResults.length < this.worldTotal;
    }

    /** Tải trang tiếp theo (offset += pageSize) và ghép thêm vào danh sách + marker. */
    async loadMorePlaces(): Promise<void> {
        if (!this.hasMorePlaces || this.worldLoadingMore) return;
        const q = this.worldQuery.trim();
        if (!q) return;
        this.worldLoadingMore = true;
        this.worldOffset += this.worldPageSize;
        try {
            const res = await this.placeService.suggest(q, this.worldPageSize, this.worldRadiusKm, this.worldOffset);
            if (res.EC === 0 && res.places?.length) {
                const seen = new Set(this.worldResults.map(p => p.osm_id));
                const fresh = res.places.filter(p => !seen.has(p.osm_id));
                this.worldResults = [...this.worldResults, ...fresh];
                this.worldTotal = res.total ?? this.worldTotal;
                // Chỉ thêm marker mới, giữ nguyên viewport hiện tại của người dùng.
                this.addMarkers(fresh, false);
            } else {
                // Hết địa điểm -> ghim total để ẩn nút "Xem thêm".
                this.worldTotal = this.worldResults.length;
            }
        } catch (e: any) {
            // Lỗi -> hoàn tác offset để thử lại được.
            this.worldOffset = Math.max(0, this.worldOffset - this.worldPageSize);
            this.messageService.add({
                severity: 'error',
                summary: 'Lỗi',
                detail: e?.message || 'Không tải được thêm địa điểm'
            });
        } finally {
            this.worldLoadingMore = false;
        }
    }

    /**
     * Vẽ marker cho danh sách places.
     * @param reset true (trang đầu / tìm mới): xoá sạch marker cũ + fitBounds theo places + location.
     *              false (load thêm): chỉ thêm marker mới, giữ viewport.
     */
    private addMarkers(places: PlaceSuggestion[], reset: boolean, location?: { lat: number; lon: number }): void {
        if (reset) {
            this.worldMarkers.clearLayers();
            this.placeByOsm.clear();
        }
        const bounds = reset ? L.latLngBounds([]) : null;
        places.forEach(p => {
            if (this.placeByOsm.has(p.osm_id)) return; // khử trùng osm_id
            this.placeByOsm.set(p.osm_id, p);
            const marker = L.marker([p.lat, p.lng], { icon: this.pinIcon() });
            marker.bindPopup(this.buildPopupHtml(p), { maxWidth: 280, className: 'explore-popup' });
            this.worldMarkers.addLayer(marker);
            bounds?.extend([p.lat, p.lng]);
        });
        if (reset && bounds && location) {
            bounds.extend([location.lat, location.lon]);
            this.ngZone.runOutsideAngular(() => {
                this.map!.fitBounds(bounds.pad(0.25), { maxZoom: 13 });
                this.map!.invalidateSize();
            });
        } else if (!reset) {
            // Load thêm: sidebar dài ra -> container map cao hơn -> báo Leaflet vẽ lại.
            this.ngZone.runOutsideAngular(() => {
                setTimeout(() => this.map?.invalidateSize(), 0);
            });
        }
    }

    private pinIcon(): L.DivIcon {
        // Clean dot marker (no icon/emoji) — styled via .explore-pin-dot in SCSS.
        return L.divIcon({
            className: 'explore-pin',
            html: `<span class="explore-pin-dot"></span>`,
            iconSize: [22, 22],
            iconAnchor: [11, 11],
            popupAnchor: [0, -12]
        });
    }

    private buildPopupHtml(p: PlaceSuggestion): string {
        const img = p.image_url
            ? `<img class="pp-img" src="${p.image_url}" alt="${this.escape(p.name)}" onerror="this.style.display='none'" />`
            : '';
        const desc = p.description ? `<p class="pp-desc">${this.escape(this.truncate(p.description, 160))}</p>` : '';
        const wiki = p.wikipedia_url ? `<a class="pp-link" href="${p.wikipedia_url}" target="_blank" rel="noopener">Xem trên Wikipedia</a>` : '';
        const label = p.saved_by_user ? 'Đã lưu' : 'Lưu vào bộ sưu tập';
        return `
            <div class="place-popup">
                ${img}
                <div class="pp-body">
                    <h4 class="pp-title">${this.escape(p.name)}</h4>
                    <span class="pp-cat">${this.categoryLabel(p.category)} · ${p.distance_km} km</span>
                    ${desc}
                    <button class="pp-save" data-save-btn data-osm-id="${p.osm_id}">${label}</button>
                    ${wiki}
                </div>
            </div>`;
    }

    private wirePopupActions(popup: L.Popup): void {
        const el = popup.getElement();
        if (!el) return;
        const btn = el.querySelector('[data-save-btn]') as HTMLButtonElement | null;
        if (!btn) return;
        const osmId = Number(btn.getAttribute('data-osm-id'));
        const place = this.placeByOsm.get(osmId);
        if (!place) return;
        btn.addEventListener('click', () => {
            this.ngZone.run(async () => {
                try {
                    await this.toggleSave(place);
                    btn.textContent = place.saved_by_user ? 'Đã lưu' : 'Lưu vào bộ sưu tập';
                    btn.classList.toggle('saved', place.saved_by_user);
                } catch (e: any) {
                    this.messageService.add({ severity: 'error', summary: 'Lỗi', detail: e?.message || 'Thao tác thất bại' });
                }
            });
        });
    }

    // ============================ save / collection ============================
    async toggleSave(place: PlaceSuggestion): Promise<void> {
        if (place.saved_by_user) {
            // Cần save_id để remove -> tìm trong collection (load nếu chưa có).
            let item = this.collectionData?.wishlist.find(w => w.osm_id === place.osm_id);
            if (!item) {
                await this.loadCollection();
                item = this.collectionData?.wishlist.find(w => w.osm_id === place.osm_id);
            }
            if (item) {
                await this.collectionService.remove(item.save_id, place.osm_id);
                place.saved_by_user = false;
                this.messageService.add({ severity: 'info', summary: place.name, detail: 'Đã bỏ khỏi bộ sưu tập' });
            }
        } else {
            await this.collectionService.save({
                place_name: place.name,
                place_display_name: place.name,
                latitude: place.lat,
                longitude: place.lng,
                category: place.category,
                image_url: place.image_url || undefined,
                description: place.description || undefined,
                wikipedia_url: place.wikipedia_url || undefined,
                osm_id: place.osm_id
            });
            place.saved_by_user = true;
            this.messageService.add({ severity: 'success', summary: place.name, detail: 'Đã lưu vào bộ sưu tập' });
        }
    }

    openCollection(): void {
        this.showCollection = true;
        if (!this.collectionData) {
            this.loadCollection();
        }
    }

    async loadCollection(): Promise<void> {
        this.collectionLoading = true;
        try {
            this.collectionData = await this.collectionService.getCombined();
        } catch (e: any) {
            this.messageService.add({ severity: 'error', summary: 'Lỗi', detail: e?.message || 'Không tải được bộ sưu tập' });
        } finally {
            this.collectionLoading = false;
        }
    }

    async removeFromCollection(item: SavedPlace): Promise<void> {
        try {
            await this.collectionService.remove(item.save_id, item.osm_id);
            if (this.collectionData) {
                this.collectionData.wishlist = this.collectionData.wishlist.filter(w => w.save_id !== item.save_id);
                this.collectionData.total_wishlist = Math.max(0, this.collectionData.total_wishlist - 1);
            }
            // đồng bộ danh sách gợi ý nếu đang hiển thị
            const sugg = this.worldResults.find(s => s.osm_id === item.osm_id);
            if (sugg) sugg.saved_by_user = false;
            this.messageService.add({ severity: 'info', summary: item.place_name, detail: 'Đã bỏ lưu' });
        } catch (e: any) {
            this.messageService.add({ severity: 'error', summary: 'Lỗi', detail: e?.message || 'Bỏ lưu thất bại' });
        }
    }

    flyTo(lat: number, lng: number, zoom = 12): void {
        this.ngZone.runOutsideAngular(() => {
            if (!this.map) return;
            if (this.mode !== 'world') this.switchMode('world');
            this.map.flyTo([lat, lng], zoom, { duration: 0.8 });
        });
    }

    // ============================ helpers ============================
    categoryLabel(c: string): string {
        return CATEGORY_LABELS[c] || 'Điểm tham quan';
    }

    private truncate(s: string, n: number): string {
        return s.length > n ? s.slice(0, n).trimEnd() + '…' : s;
    }

    private escape(s: string): string {
        return (s || '').replace(/[&<>"']/g, ch => ({
            '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
        }[ch] as string));
    }

    // ============================ Vietnam check-in (giữ nguyên) ============================
    private onProvinceClick(prov?: Province): void {
        if (!prov) return;
        this.visitedService
            .toggle(prov.province_id)
            .then((now: boolean) => {
                this.restyle(prov.province_id);
                this.ngZone.run(() => {
                    if (now) {
                        this.totalVisited++;
                        this.bump(prov.region, 1);
                    } else {
                        this.totalVisited--;
                        this.bump(prov.region, -1);
                    }
                    this.progress = this.roundProgress();
                    this.messageService.add({
                        severity: now ? 'success' : 'info',
                        summary: prov.province_name,
                        detail: now ? 'Đã check-in' : 'Đã bỏ check-in'
                    });
                });
            })
            .catch((e: any) => {
                this.ngZone.run(() =>
                    this.messageService.add({
                        severity: 'error',
                        summary: 'Lỗi',
                        detail: e?.message || 'Không thể cập nhật'
                    })
                );
            });
    }

    private bump(region: string, delta: number): void {
        if (region === 'north') this.north += delta;
        else if (region === 'central') this.central += delta;
        else if (region === 'south') this.south += delta;
    }

    private restyle(provinceId: string): void {
        const layer = this.layerByProvinceId.get(provinceId);
        const prov = this.allProvinces.find(p => p.province_id === provinceId);
        if (!layer || !prov) return;
        this.ngZone.runOutsideAngular(() => layer.setStyle(this.styleForName(prov.province_name)));
    }

    private restyleAll(): void {
        this.ngZone.runOutsideAngular(() => {
            this.geoLayer?.eachLayer((l: any) => {
                if (l.feature) l.setStyle(this.styleForName(l.feature.properties?.name));
            });
        });
    }

    async syncFromBookings(): Promise<void> {
        this.isSyncing = true;
        try {
            const result = await this.visitedService.autoCheckin();
            await this.loadData();
            this.restyleAll();
            this.messageService.add({
                severity: result.auto_checkins > 0 ? 'success' : 'info',
                summary: 'Đồng bộ từ booking',
                detail:
                    result.auto_checkins > 0
                        ? `Đã thêm ${result.auto_checkins} tỉnh mới${
                              result.matched?.length ? ': ' + result.matched.join(', ') : ''
                          }`
                        : 'Không có tỉnh mới từ booking đã xác nhận.'
            });
        } catch (e: any) {
            this.messageService.add({
                severity: 'error',
                summary: 'Lỗi',
                detail: e?.message || 'Đồng bộ thất bại'
            });
        } finally {
            this.isSyncing = false;
        }
    }

    regionCount(region: 'north' | 'central' | 'south'): number {
        return region === 'north' ? this.north : region === 'central' ? this.central : this.south;
    }
}
