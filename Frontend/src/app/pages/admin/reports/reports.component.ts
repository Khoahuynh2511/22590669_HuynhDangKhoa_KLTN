import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ReportService, RevenuePeriod, PriceRangeData } from '../../../services/admin/admin-report.service';

@Component({
  selector: 'app-reports',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './reports.component.html',
  styleUrls: ['./reports.component.scss']
})
export class ReportsComponent implements OnInit {
  // Revenue Report
  revenuePeriodType: 'week' | 'month' = 'month';
  revenueStartDate: string = '';
  revenueEndDate: string = '';
  revenueData: RevenuePeriod[] = [];
  totalRevenue: number = 0;
  totalBookings: number = 0;
  isLoadingRevenue: boolean = false;

  // People by Price Range
  priceRangePeriodType: 'week' | 'month' = 'week';
  priceRangeTargetDate: string = '';
  priceRangeData: PriceRangeData[] = [];
  totalPeople: number = 0;
  totalBookingsPriceRange: number = 0;
  periodStart: string = '';
  periodEnd: string = '';
  isLoadingPriceRange: boolean = false;

  errorMessage: string = '';

  constructor(private reportService: ReportService) {
    // Mặc định: tháng hiện tại
    const now = new Date();
    const year = now.getFullYear();
    const month = now.getMonth() + 1;
    this.revenueStartDate = `${year}-${String(month).padStart(2, '0')}-01`;
    this.revenueEndDate = `${year}-${String(month).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
  }

  ngOnInit() {
    this.loadRevenueReport();
    this.loadPriceRangeReport();
  }

  loadRevenueReport() {
    this.isLoadingRevenue = true;
    this.errorMessage = '';

    console.log('📈 Loading revenue report...');
    console.log('📈 Period:', this.revenuePeriodType, 'Start:', this.revenueStartDate, 'End:', this.revenueEndDate);

    this.reportService.getRevenueReport({
      period_type: this.revenuePeriodType,
      start_date: this.revenueStartDate || undefined,
      end_date: this.revenueEndDate || undefined
    }).subscribe({
      next: (response) => {
        console.log('📈 Revenue report response:', response);
        if (response.EC === 0) {
          this.revenueData = response.data || [];
          this.totalRevenue = response.total_revenue || 0;
          this.totalBookings = response.total_bookings || 0;
        } else {
          console.error('❌ Revenue report error:', response.EM);
          this.errorMessage = response.EM || 'Không thể tải báo cáo doanh thu';
          this.revenueData = [];
          this.totalRevenue = 0;
          this.totalBookings = 0;
        }
        this.isLoadingRevenue = false;
      },
      error: (error) => {
        console.error('❌ Error loading revenue report:', error);
        this.errorMessage = 'Lỗi khi tải báo cáo doanh thu';
        this.revenueData = [];
        this.totalRevenue = 0;
        this.totalBookings = 0;
        this.isLoadingRevenue = false;
      }
    });
  }

  onRevenueDateChange() {
    this.loadRevenueReport();
  }

  loadPriceRangeReport() {
    this.isLoadingPriceRange = true;
    this.errorMessage = '';

    this.reportService.getPeopleByPriceRange({
      period_type: this.priceRangePeriodType,
      target_date: this.priceRangeTargetDate || undefined
    }).subscribe({
      next: (response) => {
        if (response.EC === 0) {
          this.priceRangeData = response.data || [];
          this.totalPeople = response.total_people_all_ranges || 0;
          this.totalBookingsPriceRange = response.total_bookings_all_ranges || 0;
          this.periodStart = response.period_start || '';
          this.periodEnd = response.period_end || '';
        } else {
          this.errorMessage = response.EM || 'Không thể tải báo cáo phân khúc giá';
        }
        this.isLoadingPriceRange = false;
      },
      error: (error) => {
        console.error('Error loading price range report:', error);
        this.errorMessage = 'Lỗi khi tải báo cáo phân khúc giá';
        this.isLoadingPriceRange = false;
      }
    });
  }

  onRevenuePeriodChange() {
    this.loadRevenueReport();
  }

  onPriceRangePeriodChange() {
    this.loadPriceRangeReport();
  }

  onPriceRangeDateChange() {
    this.loadPriceRangeReport();
  }

  formatPrice(price: number): string {
    if (price === null || price === undefined || isNaN(price)) {
      return '0 VNĐ';
    }
    return new Intl.NumberFormat('vi-VN').format(price) + ' VNĐ';
  }

  formatDate(date: string): string {
    if (!date) return '';
    try {
      return new Date(date).toLocaleDateString('vi-VN');
    } catch {
      return date;
    }
  }

  getPriceRangeLabel(range: string): string {
    const labels: { [key: string]: string } = {
      'budget': 'Tiết kiệm',
      'medium': 'Trung bình',
      'premium': 'Cao cấp'
    };
    return labels[range] || range;
  }

  getPriceRangeText(range: string): string {
    const ranges: { [key: string]: string } = {
      'budget': '< 5,000,000 VNĐ',
      'medium': '5,000,000 - 15,000,000 VNĐ',
      'premium': '> 15,000,000 VNĐ'
    };
    return ranges[range] || 'N/A';
  }

  getPriceRangeColor(range: string): string {
    const colors: { [key: string]: string } = {
      'budget': 'bg-blue-100 text-blue-800',
      'medium': 'bg-green-100 text-green-800',
      'premium': 'bg-purple-100 text-purple-800'
    };
    return colors[range] || 'bg-gray-100 text-gray-800';
  }

  getPriceRangePercentage(people: number): number {
    return this.totalPeople > 0 ? (people / this.totalPeople) * 100 : 0;
  }

  getRevenueMax(): number {
    if (this.revenueData.length === 0) return 0;
    return Math.max(...this.revenueData.map(d => d.total_revenue));
  }

  getRevenueBarHeight(revenue: number): string {
    if (revenue === null || revenue === undefined || isNaN(revenue) || revenue < 0) {
      return '20px';
    }
    
    const max = this.getRevenueMax();
    if (max === 0 || max === null || max === undefined || isNaN(max)) {
      return '20px';
    }
    
    const percentage = (revenue / max) * 100;
    const minHeight = 20;
    const maxHeight = 256;
    const calculatedHeight = Math.max(minHeight, (percentage / 100) * maxHeight);
    return `${Math.min(maxHeight, Math.round(calculatedHeight))}px`;
  }

  formatPeriodLabel(item: RevenuePeriod): string {
    // Format period_start to readable label
    const start = new Date(item.period_start);
    const end = new Date(item.period_end);
    
    if (this.revenuePeriodType === 'month') {
      return `T${start.getMonth() + 1}/${start.getFullYear()}`;
    } else {
      // Week format
      return `${start.getDate()}/${start.getMonth() + 1} - ${end.getDate()}/${end.getMonth() + 1}`;
    }
  }

  formatShortPrice(price: number): string {
    if (price >= 1000000000) {
      return `${(price / 1000000000).toFixed(1)}B`;
    } else if (price >= 1000000) {
      return `${(price / 1000000).toFixed(0)}M`;
    } else if (price >= 1000) {
      return `${(price / 1000).toFixed(0)}K`;
    }
    return price.toString();
  }

  getLineChartPath(): string {
    if (this.revenueData.length === 0) return '';
    
    const width = 800;
    const height = 250;
    const padding = 50;
    const maxRevenue = this.getRevenueMax();
    
    if (maxRevenue === 0) return '';
    
    const points = this.revenueData.map((item, index) => {
      const x = padding + (index * (width - padding * 2) / (this.revenueData.length - 1 || 1));
      const y = height - padding - ((item.total_revenue / maxRevenue) * (height - padding * 2));
      return { x, y };
    });
    
    let path = `M ${points[0].x},${points[0].y}`;
    for (let i = 1; i < points.length; i++) {
      path += ` L ${points[i].x},${points[i].y}`;
    }
    
    return path;
  }

  getLineChartPoints(): Array<{x: number, y: number, revenue: number, label: string}> {
    if (this.revenueData.length === 0) return [];
    
    const width = 800;
    const height = 250;
    const padding = 50;
    const maxRevenue = this.getRevenueMax();
    
    if (maxRevenue === 0) return [];
    
    return this.revenueData.map((item, index) => {
      const x = padding + (index * (width - padding * 2) / (this.revenueData.length - 1 || 1));
      const y = height - padding - ((item.total_revenue / maxRevenue) * (height - padding * 2));
      return {
        x,
        y,
        revenue: item.total_revenue,
        label: this.formatPeriodLabel(item)
      };
    });
  }

  getAreaPath(): string {
    if (this.revenueData.length === 0) return '';
    
    const linePath = this.getLineChartPath();
    const width = 800;
    const height = 250;
    const padding = 50;
    
    const points = this.getLineChartPoints();
    if (points.length === 0) return '';
    
    const lastPoint = points[points.length - 1];
    const firstPoint = points[0];
    
    return `${linePath} L ${lastPoint.x},${height - padding} L ${firstPoint.x},${height - padding} Z`;
  }

}
