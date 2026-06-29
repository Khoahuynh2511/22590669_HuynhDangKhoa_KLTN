import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { PlaceService, Festival } from '../../services/place.service';
import { FestivalCardComponent } from '../../components/festival-card/festival-card.component';

@Component({
    selector: 'app-festivals',
    imports: [CommonModule, FestivalCardComponent],
    templateUrl: './festivals.component.html',
    styleUrl: './festivals.component.scss'
})
export class FestivalsComponent implements OnInit {
    festivals: Festival[] = [];
    loading = true;
    errorMsg: string | null = null;

    // Bộ lọc
    selectedCountry = '';        // '' = Việt Nam (mặc định); 'world' = toàn cầu; ISO2 = một nước
    selectedRegion = '';
    selectedMonth: number | null = null;

    readonly regions = [
        { key: '', label: 'Cả nước' },
        { key: 'north', label: 'Miền Bắc' },
        { key: 'central', label: 'Miền Trung' },
        { key: 'south', label: 'Miền Nam' },
    ];

    readonly months = [
        { key: 1, label: 'T1' }, { key: 2, label: 'T2' }, { key: 3, label: 'T3' },
        { key: 4, label: 'T4' }, { key: 5, label: 'T5' }, { key: 6, label: 'T6' },
        { key: 7, label: 'T7' }, { key: 8, label: 'T8' }, { key: 9, label: 'T9' },
        { key: 10, label: 'T10' }, { key: 11, label: 'T11' }, { key: 12, label: 'T12' },
    ];

    // value = mã ISO2 gửi backend (resolver khớp cả mã lẫn tên); '' = VN, 'world' = toàn cầu.
    readonly countries = [
        { value: '', label: '🇻🇳 Việt Nam' },
        { value: 'world', label: '🌍 Toàn thế giới' },
        { value: 'TH', label: 'Thái Lan' },
        { value: 'JP', label: 'Nhật Bản' },
        { value: 'KR', label: 'Hàn Quốc' },
        { value: 'CN', label: 'Trung Quốc' },
        { value: 'SG', label: 'Singapore' },
        { value: 'MY', label: 'Malaysia' },
        { value: 'ID', label: 'Indonesia' },
        { value: 'PH', label: 'Philippines' },
        { value: 'KH', label: 'Campuchia' },
        { value: 'LA', label: 'Lào' },
        { value: 'IN', label: 'Ấn Độ' },
        { value: 'US', label: 'Hoa Kỳ' },
        { value: 'CA', label: 'Canada' },
        { value: 'GB', label: 'Vương quốc Anh' },
        { value: 'FR', label: 'Pháp' },
        { value: 'DE', label: 'Đức' },
        { value: 'IT', label: 'Ý' },
        { value: 'ES', label: 'Tây Ban Nha' },
        { value: 'NL', label: 'Hà Lan' },
        { value: 'CH', label: 'Thụy Sĩ' },
        { value: 'GR', label: 'Hy Lạp' },
        { value: 'TR', label: 'Thổ Nhĩ Kỳ' },
        { value: 'AU', label: 'Úc' },
        { value: 'NZ', label: 'New Zealand' },
        { value: 'BR', label: 'Brazil' },
        { value: 'MX', label: 'Mexico' },
        { value: 'EG', label: 'Ai Cập' },
        { value: 'ZA', label: 'Nam Phi' },
    ];

    constructor(private placeService: PlaceService) {}

    ngOnInit(): void {
        this.load();
    }

    async load(): Promise<void> {
        this.loading = true;
        this.errorMsg = null;
        try {
            const res = await this.placeService.festivals('', this.selectedMonth, this.selectedRegion, this.selectedCountry);
            this.festivals = res.festivals || [];
        } catch (e: any) {
            this.errorMsg = e?.message || 'Không tải được danh sách lễ hội.';
        } finally {
            this.loading = false;
        }
    }

    setCountry(value: string): void {
        this.selectedCountry = value;
        // Miền (north/central/south) chỉ áp dụng cho Việt Nam — bỏ khi đổi nước.
        if (value !== '') {
            this.selectedRegion = '';
        }
        this.load();
    }

    setRegion(key: string): void {
        this.selectedRegion = key;
        this.load();
    }

    toggleMonth(m: number): void {
        this.selectedMonth = this.selectedMonth === m ? null : m;
        this.load();
    }

    monthLabel(m?: number | null): string {
        if (!m) return '';
        return 'Tháng ' + m;
    }

    regionLabel(r?: string | null): string {
        const found = this.regions.find(x => x.key === (r || ''));
        return found ? found.label : '';
    }

    countryLabel(value?: string | null): string {
        const found = this.countries.find(c => c.value === (value ?? ''));
        return found ? found.label : (value || '');
    }
}

