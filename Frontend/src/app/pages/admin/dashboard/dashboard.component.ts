import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { ReportService } from '../../../services/admin/admin-report.service';
import { AdminBookingService } from '../../../services/admin/admin-booking.service';
import { AdminReviewService } from '../../../services/admin/admin-review.service';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.scss'
})
export class DashboardComponent implements OnInit {
  // Stats
  totalRevenue = 0;
  revenueGrowth = 0;
  pendingBookings = 0;
  otpSentBookings = 0;
  totalBookings = 0;
  confirmedBookings = 0;
  cancelledBookings = 0;
  completedBookings = 0;
  
  // Review stats
  totalReviews = 0;
  averageRating = 0;
  
  // Loading states
  isLoading = true;
  errorMessage = '';

  // Revenue data for chart
  revenueData: any[] = [];
  revenueChartData: { period: string; revenue: number; bookings: number }[] = [];

  // Booking status distribution
  bookingStatusData: { status: string; count: number; color: string; label: string }[] = [];

  constructor(
    private reportService: ReportService,
    private bookingService: AdminBookingService,
    private reviewService: AdminReviewService
  ) {}

  ngOnInit() {
    this.loadDashboardData();
  }

  loadDashboardData() {
    this.isLoading = true;
    this.errorMessage = '';

    // Load all data
    Promise.all([
      this.loadRevenueData(),
      this.loadBookingStats(),
      this.loadReviewStats()
    ]).then(() => {
      this.isLoading = false;
    }).catch(error => {
      this.errorMessage = 'Không thể tải dữ liệu dashboard';
      this.isLoading = false;
      console.error('Dashboard error:', error);
    });
  }

  async loadRevenueData() {
    try {
      console.log('📈 ========== LOADING REVENUE DATA FROM BOOKINGS ==========');
      
      // Lấy tất cả bookings - backend limit max 100, nên lấy nhiều lần
      let allBookings: any[] = [];
      let offset = 0;
      const limit = 100;
      let hasMore = true;
      
      while (hasMore) {
        const response = await this.bookingService.getAllBookingsAdmin({
          limit: limit,
          offset: offset
        }).toPromise();

        console.log(`📈 Fetching bookings: offset=${offset}, limit=${limit}`);
        console.log('📈 Response:', response);

        if (response && response.EC === 0 && response.data) {
          allBookings = allBookings.concat(response.data);
          console.log(`📈 Fetched ${response.data.length} bookings, total so far: ${allBookings.length}`);
          
          // Nếu lấy được ít hơn limit, nghĩa là hết data
          if (response.data.length < limit) {
            hasMore = false;
          } else {
            offset += limit;
          }
          
          // Safety: không lấy quá 500 bookings để tránh vòng lặp vô hạn
          if (allBookings.length >= 500) {
            console.log('📈 Reached 500 bookings limit, stopping fetch');
            hasMore = false;
          }
        } else {
          console.error('❌ Failed to fetch bookings at offset', offset);
          hasMore = false;
        }
      }

      console.log('📈 Total bookings fetched:', allBookings.length);
      
      if (allBookings.length > 0) {
        // Filter bookings: loại bỏ cancelled
        const validBookings = allBookings.filter(b => b.status !== 'cancelled');
        console.log('📈 Valid bookings (not cancelled):', validBookings.length);
        
        // Nhóm bookings theo tháng và tính doanh thu
        const monthlyData = new Map<string, { revenue: number; bookings: number }>();
        
        validBookings.forEach(booking => {
          const date = new Date(booking.created_at);
          const monthKey = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
          
          if (!monthlyData.has(monthKey)) {
            monthlyData.set(monthKey, { revenue: 0, bookings: 0 });
          }
          
          const data = monthlyData.get(monthKey)!;
          data.revenue += booking.total_amount || 0;
          data.bookings += 1;
        });
        
        console.log('📈 Monthly data map:', monthlyData);
        
        // Tạo array cho 12 tháng gần nhất
        const now = new Date();
        const chartData: { period: string; revenue: number; bookings: number }[] = [];
        
        for (let i = 11; i >= 0; i--) {
          const targetDate = new Date(now.getFullYear(), now.getMonth() - i, 1);
          const monthKey = `${targetDate.getFullYear()}-${String(targetDate.getMonth() + 1).padStart(2, '0')}`;
          const data = monthlyData.get(monthKey) || { revenue: 0, bookings: 0 };
          
          chartData.push({
            period: `Tháng ${targetDate.getMonth() + 1}`,
            revenue: data.revenue,
            bookings: data.bookings
          });
        }
        
        this.revenueChartData = chartData;
        this.totalRevenue = validBookings.reduce((sum, b) => sum + (b.total_amount || 0), 0);
        
        console.log('📈 ✅ Final revenue chart data:', this.revenueChartData);
        console.log('📈 ✅ Chart data length:', this.revenueChartData.length);
        console.log('📈 ✅ Total revenue:', this.totalRevenue);
        
        // Calculate growth (compare last 2 months)
        if (this.revenueChartData.length >= 2) {
          const lastMonth = this.revenueChartData[this.revenueChartData.length - 1].revenue;
          const previousMonth = this.revenueChartData[this.revenueChartData.length - 2].revenue;
          if (previousMonth > 0) {
            this.revenueGrowth = ((lastMonth - previousMonth) / previousMonth) * 100;
          } else {
            this.revenueGrowth = lastMonth > 0 ? 100 : 0;
          }
          console.log('📈 Revenue growth:', this.revenueGrowth);
        }
      } else {
        console.log('📈 No bookings found, showing empty chart');
        this.totalRevenue = 0;
        this.revenueChartData = [];
        this.revenueGrowth = 0;
      }
    } catch (error: any) {
      console.error('❌ ========== ERROR LOADING REVENUE ==========');
      console.error('❌ Error:', error);
      console.error('❌ Error message:', error?.message);
      this.totalRevenue = 0;
      this.revenueChartData = [];
      this.revenueGrowth = 0;
    }
    console.log('📈 ========== END LOADING REVENUE DATA ==========');
  }

  async loadBookingStats() {
    try {
      // Load all bookings to get total (use limit=100 to match backend constraint)
      const allBookings = await this.bookingService.getAllBookingsAdmin({
        limit: 100
      }).toPromise();

      if (allBookings && allBookings.EC === 0) {
        this.totalBookings = allBookings.total || 0;
        
        // Count by status
        const bookings = allBookings.data || [];
        this.confirmedBookings = bookings.filter((b: any) => b.status === 'confirmed').length;
        this.completedBookings = bookings.filter((b: any) => b.status === 'completed').length;
        this.cancelledBookings = bookings.filter((b: any) => b.status === 'cancelled').length;
        this.otpSentBookings = bookings.filter((b: any) => b.status === 'otp_sent').length;
        
        // Prepare status distribution data
        this.bookingStatusData = [
          { status: 'pending', count: 0, color: 'bg-yellow-500', label: 'Chờ thanh toán' },
          { status: 'otp_sent', count: this.otpSentBookings, color: 'bg-cyan-500', label: 'OTP đã gửi' },
          { status: 'confirmed', count: this.confirmedBookings, color: 'bg-green-500', label: 'Đã xác nhận' },
          { status: 'completed', count: this.completedBookings, color: 'bg-blue-500', label: 'Hoàn thành' },
          { status: 'cancelled', count: this.cancelledBookings, color: 'bg-red-500', label: 'Đã hủy' }
        ];
      }

      // Load pending bookings
      const pendingBookings = await this.bookingService.getAllBookingsAdmin({
        status: 'pending',
        limit: 100
      }).toPromise();

      if (pendingBookings && pendingBookings.EC === 0) {
        this.pendingBookings = pendingBookings.total || 0;
        // Update pending count in status data
        const pendingIndex = this.bookingStatusData.findIndex(s => s.status === 'pending');
        if (pendingIndex !== -1) {
          this.bookingStatusData[pendingIndex].count = this.pendingBookings;
        }
      }
    } catch (error) {
      console.error('Error loading bookings:', error);
    }
  }

  async loadReviewStats() {
    try {
      console.log('⭐ Loading review stats...');
      const response = await this.reviewService.getReviews({ limit: 100 }).toPromise();
      
      if (response && response.EC === 0) {
        this.totalReviews = response.total || 0;
        
        // Calculate average rating
        const reviews = response.data || [];
        if (reviews.length > 0) {
          const totalRating = reviews.reduce((sum: number, review: any) => sum + (review.rating || 0), 0);
          this.averageRating = totalRating / reviews.length;
        }
        
        console.log('⭐ Review stats loaded:', this.totalReviews, 'avg:', this.averageRating);
      }
    } catch (error) {
      // Bỏ qua lỗi review vì endpoint có thể chưa có hoặc không cần thiết cho dashboard
      console.warn('⚠️ Review endpoint not available, skipping review stats:', error);
      this.totalReviews = 0;
      this.averageRating = 0;
    }
  }

  formatPrice(price: number): string {
    if (price === null || price === undefined || isNaN(price)) {
      return '0 ₫';
    }
    return new Intl.NumberFormat('vi-VN', {
      style: 'currency',
      currency: 'VND'
    }).format(price);
  }

  formatNumber(num: number): string {
    if (num === null || num === undefined || isNaN(num)) {
      return '0';
    }
    return new Intl.NumberFormat('vi-VN').format(num);
  }

  getRevenueBarHeight(revenue: number): string {
    if (!this.revenueChartData || this.revenueChartData.length === 0) return '20px';
    if (revenue === null || revenue === undefined || isNaN(revenue)) return '20px';
    
    const maxRevenue = Math.max(...this.revenueChartData.map(d => d.revenue || 0));
    if (maxRevenue === 0) return '20px';
    
    const percentage = (revenue / maxRevenue) * 100;
    // Minimum 20px height for visibility
    const minHeight = 20;
    const calculatedHeight = Math.max(minHeight, (percentage / 100) * 256); // 256px = max height
    return `${Math.min(256, calculatedHeight)}px`;
  }

  getStatusPercentage(count: number): number {
    if (this.totalBookings === 0) return 0;
    return (count / this.totalBookings) * 100;
  }

  getStatusWidth(count: number): string {
    return `${this.getStatusPercentage(count)}%`;
  }

  // Line chart helpers
  getMaxRevenue(): number {
    if (!this.revenueChartData || this.revenueChartData.length === 0) return 1;
    const max = Math.max(...this.revenueChartData.map(d => d.revenue || 0));
    return max > 0 ? max : 1;
  }

  getRevenueLinePath(): string {
    if (!this.revenueChartData || this.revenueChartData.length === 0) return '';
    
    const maxRevenue = this.getMaxRevenue();
    const points = this.revenueChartData.map((item, index) => {
      const x = 50 + (index * (730 / (this.revenueChartData.length - 1 || 1)));
      const y = 250 - ((item.revenue || 0) / maxRevenue * 230);
      return `${x},${y}`;
    });
    
    return 'M ' + points.join(' L ');
  }

  formatPeriodToMonth(period: string): string {
    // Convert "2024-W52" to "12/2024" or "2024-12" to "12/2024"
    if (period.includes('-W')) {
      // Week format: extract year and approximate month
      const [year] = period.split('-W');
      return `${year}`;
    } else if (period.includes('-')) {
      // Month format: 2024-12 -> 12/2024
      const [year, month] = period.split('-');
      return `${month}/${year}`;
    }
    return period;
  }
}
