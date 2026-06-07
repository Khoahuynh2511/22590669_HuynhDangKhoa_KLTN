import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { AdminDialogService } from '../../../services/admin/admin-dialog.service';
import { 
  AdminUserService, 
  UserProfile, 
  CreateUserRequest,
  UpdateUserRequest,
  ChatRoom,
  UserBooking
} from '../../../services/admin/admin-user.service';
import { AdminReviewService } from '../../../services/admin/admin-review.service';

interface UserSummaryData {
  user: UserProfile;
  kpi: {
    total_bookings: number;
    pending_bookings: number;
    confirmed_bookings: number;
    completed_tours: number;
    cancelled_bookings: number;
    total_paid_amount: number;
    currency: string;
  };
  recent: {
    recent_bookings: any[];
    recent_payments: any[];
  };
}

@Component({
  selector: 'app-customer-list',
  standalone: true,
  imports: [CommonModule, FormsModule, ReactiveFormsModule],
  templateUrl: './customer-list.component.html',
  styleUrls: ['./customer-list.component.scss']
})
export class CustomerListComponent implements OnInit {
  allUsers: UserProfile[] = [];
  filteredUsers: UserProfile[] = [];
  isLoadingUsers: boolean = false;
  searchTerm: string = '';
  
  // Filter properties
  filterHasBooking: 'all' | 'has' | 'no' = 'all';
  filterIsActive: 'all' | 'active' | 'inactive' = 'all';
  filterHasChat: 'all' | 'has' | 'no' = 'all';
  filterTourId: string = '';
  
  selectedUser: UserProfile | null = null;
  userSummary: UserSummaryData | null = null;
  userBookings: UserBooking[] = [];
  userChatRooms: ChatRoom[] = [];
  userReviews: any[] = [];
  
  bookingsPage: number = 1;
  bookingsLimit: number = 10;
  bookingsTotalPages: number = 0;
  bookingsTotal: number = 0;
  bookingsSort: string = 'created_at_desc';
  bookingsStatus: string = '';
  
  showUserDetailModal: boolean = false;
  showCreateUserModal: boolean = false;
  showEditUserModal: boolean = false;
  showDeleteConfirmModal: boolean = false;
  
  activeTab: 'info' | 'bookings' | 'chat' | 'summary' | 'reviews' = 'info';
  selectedChatRoom: ChatRoom | null = null;
  
  createUserForm: FormGroup;
  editUserForm: FormGroup;
  
  isCreating: boolean = false;
  isUpdating: boolean = false;
  isDeleting: boolean = false;
  isLoadingDetails: boolean = false;
  isLoadingBookings: boolean = false;
  isLoadingChat: boolean = false;
  
  errorMessage: string = '';
  successMessage: string = '';
  
  constructor(
    private adminUserService: AdminUserService,
    private adminReviewService: AdminReviewService,
    private fb: FormBuilder,
    private dialogService: AdminDialogService
  ) {
    this.createUserForm = this.fb.group({
      email: ['', [Validators.required, Validators.email]],
      full_name: ['', Validators.required],
      phone_number: ['', Validators.required],
      password: [''],
      role: ['user', Validators.required],
      is_active: [true]
    });
    
    this.editUserForm = this.fb.group({
      email: ['', [Validators.required, Validators.email]],
      full_name: ['', Validators.required],
      phone_number: ['', Validators.required],
      password: [''],
      is_active: [true]
    });
  }

  ngOnInit() {
    this.loadAllUsers();
  }

  async loadAllUsers() {
    this.isLoadingUsers = true;
    this.errorMessage = '';
    
    try {
      const response = await this.adminUserService.getAllUsers().toPromise();
      if (response?.EC === 0 && response?.data) {
        // Chỉ lấy những user có role là 'user', loại bỏ admin
        this.allUsers = response.data.users.filter((user: UserProfile) => user.role === 'user');
        this.filteredUsers = [...this.allUsers];
      } else {
        this.errorMessage = response?.EM || 'Không thể tải danh sách users';
      }
    } catch (error: any) {
      this.errorMessage = error?.error?.EM || 'Lỗi khi tải danh sách users';
      console.error('Error loading users:', error);
    } finally {
      this.isLoadingUsers = false;
    }
  }

  async filterUsers() {
    this.isLoadingUsers = true;
    this.errorMessage = '';
    
    const term = this.searchTerm.toLowerCase().trim();
    
    let filtered = [...this.allUsers];
    
    // Search by text (email, name, phone, ID)
    if (term) {
      filtered = filtered.filter(user =>
        user.email.toLowerCase().includes(term) ||
        user.full_name.toLowerCase().includes(term) ||
        user.user_id.toLowerCase().includes(term) ||
        (user.phone_number && user.phone_number.includes(term))
      );
    }
    
    // Filter by active status
    if (this.filterIsActive !== 'all') {
      const isActive = this.filterIsActive === 'active';
      filtered = filtered.filter(user => user.is_active === isActive);
    }
    
    // For advanced filters (booking, chat, tour), we need to fetch additional data
    if (this.filterHasBooking !== 'all' || this.filterHasChat !== 'all' || this.filterTourId) {
      const promises = filtered.map(async (user) => {
        try {
          // Check booking filter
          if (this.filterHasBooking !== 'all') {
            const summaryResponse = await this.adminUserService.getUserSummary(user.user_id).toPromise();
            const totalBookings = summaryResponse?.data?.kpi?.total_bookings ?? 0;
            const hasBookings = totalBookings > 0;
            
            if (this.filterHasBooking === 'has' && !hasBookings) {
              return null;
            }
            if (this.filterHasBooking === 'no' && hasBookings) {
              return null;
            }
          }
          
          // Check chat filter
          if (this.filterHasChat !== 'all') {
            const chatResponse = await this.adminUserService.getUserChatHistory(user.user_id).toPromise();
            const totalRooms = chatResponse?.data?.rooms?.length ?? 0;
            const hasChat = totalRooms > 0;
            
            if (this.filterHasChat === 'has' && !hasChat) {
              return null;
            }
            if (this.filterHasChat === 'no' && hasChat) {
              return null;
            }
          }
          
          // Check tour ID filter
          if (this.filterTourId) {
            const bookingsResponse = await this.adminUserService.getUserBookings(user.user_id, {
              page: 1,
              limit: 100
            }).toPromise();
            const hasBookingForTour = bookingsResponse?.data?.items?.some(
              (booking: any) => booking.package_id === this.filterTourId
            ) ?? false;
            
            if (!hasBookingForTour) {
              return null;
            }
          }
          
          return user;
        } catch (error) {
          console.error('Error filtering user:', user.user_id, error);
          // If API call fails, exclude the user from results to be safe
          return null;
        }
      });
      
      const results = await Promise.all(promises);
      filtered = results.filter((user): user is UserProfile => user !== null);
    }
    
    this.filteredUsers = filtered;
    this.isLoadingUsers = false;
  }

  openCreateUserModal() {
    this.createUserForm.reset({
      role: 'user',
      is_active: true
    });
    this.showCreateUserModal = true;
    this.errorMessage = '';
  }

  closeCreateUserModal() {
    this.showCreateUserModal = false;
    this.createUserForm.reset();
    this.errorMessage = '';
  }

  async createUser() {
    if (this.createUserForm.invalid) {
      this.errorMessage = 'Vui lòng điền đầy đủ thông tin';
      return;
    }
    
    this.isCreating = true;
    this.errorMessage = '';
    
    try {
      const request: CreateUserRequest = {
        ...this.createUserForm.value,
        role: 'user' // Force role to be 'user'
      };
      const response = await this.adminUserService.createUser(request).toPromise();
      
      if (response?.EC === 0) {
        this.successMessage = 'Tạo user thành công!';
        if (response.data.password) {
          await this.dialogService.alert('Tạo user thành công', `User đã được tạo với mật khẩu: ${response.data.password}`);
        }
        this.closeCreateUserModal();
        await this.loadAllUsers();
        setTimeout(() => this.successMessage = '', 3000);
      } else {
        this.errorMessage = response?.EM || 'Không thể tạo user';
      }
    } catch (error: any) {
      console.error('Error creating user:', error);
      
      // Get error message from various sources
      const errorMessage = error?.error?.EM || error?.error?.message || error?.message || '';
      const errorStatus = error?.status || error?.error?.EC;
      
      // Check for duplicate email error (HTTP 400 or specific message)
      const isDuplicateEmail = 
        errorStatus === 400 || 
        errorMessage.toLowerCase().includes('email') && 
        (errorMessage.toLowerCase().includes('exists') || 
         errorMessage.toLowerCase().includes('already') ||
         errorMessage.toLowerCase().includes('tồn tại') || 
         errorMessage.toLowerCase().includes('trùng') ||
         errorMessage.toLowerCase().includes('duplicate'));
      
      if (isDuplicateEmail) {
        this.errorMessage = `Email "${this.createUserForm.value.email}" đã tồn tại trong hệ thống. Vui lòng sử dụng email khác.`;
      } else {
        this.errorMessage = errorMessage || 'Lỗi khi tạo user. Vui lòng thử lại.';
      }
    } finally {
      this.isCreating = false;
    }
  }

  async viewUserDetails(user: UserProfile) {
    this.selectedUser = user;
    this.showUserDetailModal = true;
    this.activeTab = 'info';
    this.isLoadingDetails = true;
    this.errorMessage = '';
    
    try {
      const response = await this.adminUserService.getUserSummary(user.user_id).toPromise();
      if (response?.EC === 0 && response?.data) {
        this.userSummary = response.data;
      }
    } catch (error: any) {
      this.errorMessage = 'Không thể tải thông tin chi tiết';
      console.error('Error loading user summary:', error);
    } finally {
      this.isLoadingDetails = false;
    }
  }

  closeUserDetailModal() {
    this.showUserDetailModal = false;
    this.selectedUser = null;
    this.userSummary = null;
    this.userBookings = [];
    this.userChatRooms = [];
    this.activeTab = 'info';
  }

  async switchTab(tab: 'info' | 'bookings' | 'chat' | 'summary' | 'reviews') {
    this.activeTab = tab;
    
    if (tab === 'bookings' && this.selectedUser && this.userBookings.length === 0) {
      await this.loadUserBookings();
    } else if (tab === 'chat' && this.selectedUser && this.userChatRooms.length === 0) {
      await this.loadUserChatHistory();
    } else if (tab === 'reviews' && this.selectedUser && this.userReviews.length === 0) {
      await this.loadUserReviews();
    }
  }

  async loadUserBookings() {
    if (!this.selectedUser) return;
    
    this.isLoadingBookings = true;
    this.errorMessage = '';
    
    try {
      const params: any = {
        page: this.bookingsPage,
        limit: this.bookingsLimit,
        sort: this.bookingsSort
      };
      
      if (this.bookingsStatus) {
        params.status = this.bookingsStatus;
      }
      
      const response = await this.adminUserService.getUserBookings(this.selectedUser.user_id, params).toPromise();
      if (response?.EC === 0 && response?.data) {
        this.userBookings = response.data.items;
        this.bookingsTotalPages = response.data.total_pages;
        this.bookingsTotal = response.data.total;
      }
    } catch (error: any) {
      this.errorMessage = 'Không thể tải danh sách bookings';
      console.error('Error loading bookings:', error);
    } finally {
      this.isLoadingBookings = false;
    }
  }

  async changeBookingsPage(page: number) {
    if (page < 1 || page > this.bookingsTotalPages) return;
    this.bookingsPage = page;
    await this.loadUserBookings();
  }

  async loadUserChatHistory() {
    if (!this.selectedUser) return;
    
    this.isLoadingChat = true;
    this.errorMessage = '';
    
    try {
      const response = await this.adminUserService.getUserChatHistory(this.selectedUser.user_id).toPromise();
      if (response?.EC === 0 && response?.data) {
        this.userChatRooms = response.data.rooms;
      }
    } catch (error: any) {
      this.errorMessage = 'Không thể tải lịch sử chat';
      console.error('Error loading chat history:', error);
    } finally {
      this.isLoadingChat = false;
    }
  }

  async loadUserReviews() {
    if (!this.selectedUser) return;
    
    this.isLoadingDetails = true;
    this.errorMessage = '';
    
    try {
      const response = await this.adminReviewService.getReviews({
        user_id: this.selectedUser.user_id,
        limit: 100
      }).toPromise();
      
      if (response?.EC === 0 && response?.data) {
        this.userReviews = response.data;
      }
    } catch (error: any) {
      this.errorMessage = 'Không thể tải danh sách reviews';
      console.error('Error loading user reviews:', error);
    } finally {
      this.isLoadingDetails = false;
    }
  }

  selectChatRoom(room: ChatRoom) {
    this.selectedChatRoom = room;
  }

  openEditUserModal(user: UserProfile) {
    this.selectedUser = user;
    this.editUserForm.patchValue({
      email: user.email,
      full_name: user.full_name,
      phone_number: user.phone_number,
      is_active: user.is_active,
      password: ''
    });
    this.showEditUserModal = true;
    this.errorMessage = '';
  }

  closeEditUserModal() {
    this.showEditUserModal = false;
    this.selectedUser = null;
    this.editUserForm.reset();
    this.errorMessage = '';
  }

  async updateUser() {
    if (this.editUserForm.invalid || !this.selectedUser) {
      this.errorMessage = 'Vui lòng điền đầy đủ thông tin';
      return;
    }
    
    this.isUpdating = true;
    this.errorMessage = '';
    
    try {
      // Không gửi role trong request, chỉ cập nhật các trường khác
      const formValue = this.editUserForm.value;
      const request: UpdateUserRequest = {
        email: formValue.email,
        full_name: formValue.full_name,
        phone_number: formValue.phone_number,
        is_active: formValue.is_active
      };
      
      if (formValue.password) {
        request.password = formValue.password;
      }
      
      const response = await this.adminUserService.updateUser(this.selectedUser.user_id, request).toPromise();
      
      if (response?.EC === 0) {
        this.successMessage = 'Cập nhật user thành công!';
        this.closeEditUserModal();
        await this.loadAllUsers();
        setTimeout(() => this.successMessage = '', 3000);
      } else {
        this.errorMessage = response?.EM || 'Không thể cập nhật user';
      }
    } catch (error: any) {
      this.errorMessage = error?.error?.EM || 'Lỗi khi cập nhật user';
      console.error('Error updating user:', error);
    } finally {
      this.isUpdating = false;
    }
  }

  openDeleteConfirmModal(user: UserProfile) {
    this.selectedUser = user;
    this.showDeleteConfirmModal = true;
    this.errorMessage = '';
  }

  closeDeleteConfirmModal() {
    this.showDeleteConfirmModal = false;
    this.selectedUser = null;
    this.errorMessage = '';
  }

  async deleteUser() {
    if (!this.selectedUser) return;
    
    this.isDeleting = true;
    this.errorMessage = '';
    
    try {
      const response = await this.adminUserService.deleteUser(this.selectedUser.user_id).toPromise();
      
      if (response?.EC === 0) {
        this.successMessage = 'Xóa user thành công!';
        this.closeDeleteConfirmModal();
        await this.loadAllUsers();
        setTimeout(() => this.successMessage = '', 3000);
      } else {
        this.errorMessage = response?.EM || 'Không thể xóa user';
      }
    } catch (error: any) {
      this.errorMessage = error?.error?.EM || 'Lỗi khi xóa user. User có thể có dữ liệu liên quan.';
      console.error('Error deleting user:', error);
    } finally {
      this.isDeleting = false;
    }
  }

  reloadData() {
    this.loadAllUsers();
  }

  resetFilters() {
    this.searchTerm = '';
    this.filterHasBooking = 'all';
    this.filterIsActive = 'all';
    this.filterHasChat = 'all';
    this.filterTourId = '';
    this.filteredUsers = [...this.allUsers];
  }

  applyFilters() {
    this.filterUsers();
  }

  async toggleUserStatus(user: UserProfile) {
    const newStatus = !user.is_active;
    const confirmMsg = newStatus 
      ? `Kích hoạt tài khoản ${user.email}?`
      : `Vô hiệu hóa tài khoản ${user.email}?`;
    
    if (!confirm(confirmMsg)) return;
    
    try {
      const response = await this.adminUserService.updateUserStatus(user.user_id, {
        is_active: newStatus
      }).toPromise();
      
      if (response?.EC === 0) {
        this.successMessage = `${newStatus ? 'Kích hoạt' : 'Vô hiệu hóa'} tài khoản thành công!`;
        await this.loadAllUsers();
        setTimeout(() => this.successMessage = '', 3000);
      }
    } catch (error: any) {
      this.errorMessage = error?.error?.EM || 'Lỗi khi cập nhật trạng thái';
      console.error('Error updating status:', error);
    }
  }

  formatDate(dateString: string): string {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleString('vi-VN');
  }

  formatCurrency(amount: number): string {
    return new Intl.NumberFormat('vi-VN').format(amount);
  }

  getRoleBadgeClass(role: string): string {
    switch (role) {
      case 'admin': return 'bg-red-100 text-red-800';
      case 'user': return 'bg-blue-100 text-blue-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  }

  getStatusBadgeClass(isActive: boolean): string {
    return isActive ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800';
  }

  getBookingStatusBadgeClass(status: string): string {
    switch (status) {
      case 'confirmed': return 'bg-green-100 text-green-800';
      case 'pending': return 'bg-yellow-100 text-yellow-800';
      case 'completed': return 'bg-blue-100 text-blue-800';
      case 'cancelled': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  }

  // Copy to clipboard
  async copyToClipboard(text: string) {
    try {
      await navigator.clipboard.writeText(text);
      await this.dialogService.alert('Thành công', 'Đã copy vào clipboard!');
    } catch (err) {
      console.error('Failed to copy:', err);
      await this.dialogService.alert('Lỗi', 'Không thể copy vào clipboard!');
    }
  }
}
