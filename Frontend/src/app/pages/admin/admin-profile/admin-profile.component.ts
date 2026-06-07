import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { UserProfileService, UserProfile, UpdateProfileRequest, ChangePasswordRequest } from '../../../services/admin/admin-user-profile.service';
import { AdminDialogService } from '../../../services/admin/admin-dialog.service';
import { AuthStateService } from '../../../services/auth-state.service';

@Component({
  selector: 'app-admin-profile',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './admin-profile.component.html',
  styleUrls: ['./admin-profile.component.scss']
})
export class AdminProfileComponent implements OnInit {
  profile: UserProfile | null = null;
  isLoading: boolean = false;
  errorMessage: string = '';
  successMessage: string = '';

  // Edit mode
  isEditing: boolean = false;
  editForm: UpdateProfileRequest = {};

  // Change password
  showPasswordModal: boolean = false;
  passwordForm: ChangePasswordRequest = {
    current_password: '',
    new_password: ''
  };
  confirmPassword: string = '';

  // Avatar upload
  selectedAvatarFile: File | null = null;
  previewAvatarUrl: string | null = null;

  constructor(
    private userProfileService: UserProfileService,
    private router: Router,
    private dialogService: AdminDialogService,
    private authStateService: AuthStateService
  ) {}

  ngOnInit() {
    this.loadProfile();
  }

  loadProfile() {
    this.isLoading = true;
    this.errorMessage = '';

    this.userProfileService.getMyProfile().subscribe({
      next: (response) => {
        if (response.EC === 0 && response.data) {
          this.profile = response.data;
          this.editForm = {
            full_name: this.profile.full_name,
            phone_number: this.profile.phone_number,
            profile_picture: this.profile.profile_picture
          };
        } else {
          this.errorMessage = response.EM || 'Không thể tải thông tin tài khoản';
        }
        this.isLoading = false;
      },
      error: (error) => {
        console.error('Error loading profile:', error);
        this.errorMessage = error?.error?.EM || 'Lỗi khi tải thông tin tài khoản';
        this.isLoading = false;
      }
    });
  }

  startEdit() {
    this.isEditing = true;
    this.editForm = {
      full_name: this.profile?.full_name,
      phone_number: this.profile?.phone_number,
      profile_picture: this.profile?.profile_picture
    };
  }

  cancelEdit() {
    this.isEditing = false;
    this.editForm = {};
  }

  saveProfile() {
    if (!this.editForm.full_name?.trim()) {
      this.errorMessage = 'Vui lòng nhập họ tên';
      return;
    }

    this.isLoading = true;
    this.errorMessage = '';
    this.successMessage = '';

    this.userProfileService.updateMyProfile(this.editForm).subscribe({
      next: (response) => {
        if (response.EC === 0 && response.data) {
          this.profile = response.data;
          this.isEditing = false;
          this.successMessage = 'Cập nhật thông tin thành công';
          setTimeout(() => this.successMessage = '', 3000);
        } else {
          this.errorMessage = response.EM || 'Không thể cập nhật thông tin';
        }
        this.isLoading = false;
      },
      error: (error) => {
        console.error('Error updating profile:', error);
        this.errorMessage = error?.error?.EM || 'Lỗi khi cập nhật thông tin';
        this.isLoading = false;
      }
    });
  }

  onAvatarFileSelected(event: any) {
    const file = event.target.files[0];
    if (file) {
      // Validate file type
      if (!file.type.startsWith('image/')) {
        this.errorMessage = 'Vui lòng chọn file ảnh';
        return;
      }

      // Validate file size (max 5MB)
      if (file.size > 5 * 1024 * 1024) {
        this.errorMessage = 'Kích thước ảnh tối đa 5MB';
        return;
      }

      this.selectedAvatarFile = file;

      // Preview
      const reader = new FileReader();
      reader.onload = (e: any) => {
        this.previewAvatarUrl = e.target.result;
      };
      reader.readAsDataURL(file);
    }
  }

  uploadAvatar() {
    if (!this.selectedAvatarFile) {
      this.errorMessage = 'Vui lòng chọn ảnh';
      return;
    }

    this.isLoading = true;
    this.errorMessage = '';
    this.successMessage = '';

    this.userProfileService.uploadAvatar(this.selectedAvatarFile).subscribe({
      next: (response) => {
        if (response.EC === 0 && response.data) {
          this.profile = response.data;
          this.selectedAvatarFile = null;
          this.previewAvatarUrl = null;
          this.successMessage = 'Cập nhật ảnh đại diện thành công';
          setTimeout(() => this.successMessage = '', 3000);
        } else {
          this.errorMessage = response.EM || 'Không thể tải ảnh lên';
        }
        this.isLoading = false;
      },
      error: (error) => {
        console.error('Error uploading avatar:', error);
        this.errorMessage = error?.error?.EM || 'Lỗi khi tải ảnh lên';
        this.isLoading = false;
      }
    });
  }

  openPasswordModal() {
    this.showPasswordModal = true;
    this.passwordForm = {
      current_password: '',
      new_password: ''
    };
    this.confirmPassword = '';
    this.errorMessage = '';
  }

  closePasswordModal() {
    this.showPasswordModal = false;
    this.passwordForm = {
      current_password: '',
      new_password: ''
    };
    this.confirmPassword = '';
  }

  changePassword() {
    if (!this.passwordForm.current_password) {
      this.errorMessage = 'Vui lòng nhập mật khẩu hiện tại';
      return;
    }

    if (!this.passwordForm.new_password) {
      this.errorMessage = 'Vui lòng nhập mật khẩu mới';
      return;
    }

    if (this.passwordForm.new_password.length < 6) {
      this.errorMessage = 'Mật khẩu mới phải có ít nhất 6 ký tự';
      return;
    }

    if (this.passwordForm.new_password !== this.confirmPassword) {
      this.errorMessage = 'Mật khẩu xác nhận không khớp';
      return;
    }

    this.isLoading = true;
    this.errorMessage = '';
    this.successMessage = '';

    this.userProfileService.changePassword(this.passwordForm).subscribe({
      next: (response) => {
        if (response.EC === 0) {
          this.successMessage = 'Đổi mật khẩu thành công';
          setTimeout(() => {
            this.closePasswordModal();
            this.successMessage = '';
          }, 2000);
        } else {
          this.errorMessage = response.EM || 'Không thể đổi mật khẩu';
        }
        this.isLoading = false;
      },
      error: (error) => {
        console.error('Error changing password:', error);
        this.errorMessage = error?.error?.EM || 'Mật khẩu hiện tại không đúng';
        this.isLoading = false;
      }
    });
  }

  async logout() {
    const confirmed = await this.dialogService.confirm({
      title: 'Đăng xuất',
      message: 'Bạn có chắc chắn muốn đăng xuất khỏi hệ thống?',
      confirmText: 'Đăng xuất',
      cancelText: 'Hủy',
      type: 'warning'
    });

    if (confirmed) {
      // Clear all auth state (localStorage + service state)
      this.authStateService.logout();
      this.router.navigate(['/home']);
    }
  }

  formatDate(date: string): string {
    return new Date(date).toLocaleDateString('vi-VN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    });
  }

  getRoleDisplayName(role: string): string {
    const roles: { [key: string]: string } = {
      'admin': 'Quản trị viên',
      'user': 'Người dùng',
      'customer': 'Khách hàng'
    };
    return roles[role] || role;
  }
}
