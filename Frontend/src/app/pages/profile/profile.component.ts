import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { MessageService } from 'primeng/api';
import { ButtonModule } from 'primeng/button';
import { CardModule } from 'primeng/card';
import { InputTextModule } from 'primeng/inputtext';
import { PasswordModule } from 'primeng/password';
import { ToastModule } from 'primeng/toast';
import { SkeletonModule } from 'primeng/skeleton';
import { TagModule } from 'primeng/tag';
import { AvatarModule } from 'primeng/avatar';
import { AuthStateService } from '../../services/auth-state.service';
import { AuthService } from '../../services/auth.service';
import { ProfileService } from '../../services/profile.service';
import { UserProfile } from '../../shared/models/user-profile.model';

@Component({
  selector: 'app-profile',
  imports: [
    CommonModule,
    ReactiveFormsModule,
    ButtonModule,
    CardModule,
    InputTextModule,
    PasswordModule,
    ToastModule,
    SkeletonModule,
    TagModule,
    AvatarModule
  ],
  providers: [MessageService],
  templateUrl: './profile.component.html',
  styleUrl: './profile.component.scss'
})
export class ProfileComponent implements OnInit {
  profileForm: FormGroup;
  passwordForm: FormGroup;
  userProfile: UserProfile | null = null;
  isLoading = false;
  isSubmitting = false;
  isUploading = false;
  isEditMode = false;
  isChangingPassword = false;
  showPasswordForm = false;

  constructor(
    private fb: FormBuilder,
    private authStateService: AuthStateService,
    private authService: AuthService,
    private profileService: ProfileService,
    private messageService: MessageService,
    private router: Router
  ) {
    this.profileForm = this.fb.group({
      full_name: ['', [Validators.required, Validators.minLength(2), Validators.maxLength(255)]],
      phone_number: ['', [Validators.pattern(/^[\d+\s()-]*$/), Validators.maxLength(15)]],
      profile_picture: ['', [Validators.maxLength(500)]]
    });

    this.passwordForm = this.fb.group({
      current_password: ['', [Validators.required]],
      new_password: ['', [
        Validators.required,
        Validators.minLength(8),
        Validators.pattern(/^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$/)
      ]],
      confirm_password: ['', [Validators.required]]
    });
  }

  ngOnInit(): void {
    if (!this.authStateService.getIsAuthenticated()) {
      this.router.navigate(['/login']);
      return;
    }

    this.loadProfile();
  }

  loadProfile(): void {
    this.isLoading = true;
    this.profileService.getMyProfile().subscribe({
      next: (response) => {
        if (response.EC === 0 && response.data) {
          this.userProfile = response.data;
          this.profileForm.patchValue({
            full_name: response.data.full_name || '',
            phone_number: response.data.phone_number || '',
            profile_picture: response.data.profile_picture || ''
          });
          this.profileForm.markAsPristine();
        } else {
          this.messageService.add({
            severity: 'error',
            summary: 'Lỗi',
            detail: response.EM || 'Không thể tải thông tin'
          });
        }
        this.isLoading = false;
      },
      error: (error) => {
        console.error('Error loading profile:', error);
        this.messageService.add({
          severity: 'error',
          summary: 'Lỗi',
          detail: 'Không thể tải thông tin tài khoản'
        });
        this.isLoading = false;
        if (error.status === 401 || error.status === 403) {
          setTimeout(() => this.router.navigate(['/login']), 2000);
        }
      }
    });
  }

  onSubmit(): void {
    if (this.profileForm.invalid || this.profileForm.pristine) {
      return;
    }

    this.isSubmitting = true;
    const formValue = this.profileForm.value;

    // Only send changed fields
    const updateData: any = {};
    if (formValue.full_name !== this.userProfile?.full_name) {
      updateData.full_name = formValue.full_name;
    }
    if (formValue.phone_number !== this.userProfile?.phone_number) {
      updateData.phone_number = formValue.phone_number;
    }
    if (formValue.profile_picture !== this.userProfile?.profile_picture) {
      updateData.profile_picture = formValue.profile_picture;
    }

    this.profileService.updateMyProfile(updateData).subscribe({
      next: (response) => {
        if (response.EC === 0 && response.data) {
          this.userProfile = response.data;
          this.profileForm.markAsPristine();
          this.isEditMode = false;
          this.messageService.add({
            severity: 'success',
            summary: 'Thành công',
            detail: 'Cập nhật thông tin thành công'
          });
        } else {
          this.messageService.add({
            severity: 'error',
            summary: 'Lỗi',
            detail: response.EM || 'Không thể cập nhật thông tin'
          });
        }
        this.isSubmitting = false;
      },
      error: (error) => {
        console.error('Error updating profile:', error);
        this.messageService.add({
          severity: 'error',
          summary: 'Lỗi',
          detail: error.error?.detail || 'Có lỗi xảy ra khi cập nhật'
        });
        this.isSubmitting = false;
        if (error.status === 401 || error.status === 403) {
          setTimeout(() => this.router.navigate(['/login']), 2000);
        }
      }
    });
  }

  onCancel(): void {
    if (this.userProfile) {
      this.profileForm.patchValue({
        full_name: this.userProfile.full_name || '',
        phone_number: this.userProfile.phone_number || '',
        profile_picture: this.userProfile.profile_picture || ''
      });
      this.profileForm.markAsPristine();
      this.isEditMode = false;
    }
  }

  toggleEdit(): void {
    if (!this.isEditMode) {
      this.isEditMode = true;
      return;
    }
    this.onSubmit();
  }

  onLogout(): void {
    this.authStateService.logout();
    this.router.navigate(['/home']);
  }

  onAvatarSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];

    if (!file) {
      return;
    }

    // reset input so selecting the same file twice still triggers change
    input.value = '';

    if (file.size > 5 * 1024 * 1024) {
      this.messageService.add({
        severity: 'warn',
        summary: 'Ảnh quá lớn',
        detail: 'Giới hạn 5MB',
        life: 3000
      });
      return;
    }

    this.isUploading = true;

    this.profileService.uploadProfilePicture(file).subscribe({
      next: (response) => {
        if (response.EC === 0 && response.data) {
          this.userProfile = response.data;
          this.profileForm.patchValue({
            profile_picture: response.data.profile_picture || ''
          });
          this.profileForm.markAsPristine();
          this.messageService.add({
            severity: 'success',
            summary: 'Đã tải ảnh',
            detail: 'Ảnh đại diện đã được cập nhật'
          });
        } else {
          this.messageService.add({
            severity: 'error',
            summary: 'Lỗi',
            detail: response.EM || 'Không thể tải ảnh'
          });
        }
        this.isUploading = false;
      },
      error: (error) => {
        console.error('Error uploading avatar:', error);
        this.messageService.add({
          severity: 'error',
          summary: 'Lỗi',
          detail: error.error?.detail || 'Tải ảnh thất bại'
        });
        this.isUploading = false;
        if (error.status === 401 || error.status === 403) {
          setTimeout(() => this.router.navigate(['/login']), 2000);
        }
      }
    });
  }

  clearAvatar(): void {
    if (!this.userProfile) {
      return;
    }

    this.isSubmitting = true;

    this.profileService.updateMyProfile({ profile_picture: '' }).subscribe({
      next: (response) => {
        if (response.EC === 0 && response.data) {
          this.userProfile = response.data;
          this.profileForm.patchValue({ profile_picture: '' });
          this.profileForm.markAsPristine();
          this.messageService.add({
            severity: 'success',
            summary: 'Đã gỡ ảnh',
            detail: 'Ảnh đại diện đã được xóa'
          });
        } else {
          this.messageService.add({
            severity: 'error',
            summary: 'Lỗi',
            detail: response.EM || 'Không thể gỡ ảnh'
          });
        }
        this.isSubmitting = false;
      },
      error: (error) => {
        console.error('Error clearing avatar:', error);
        this.messageService.add({
          severity: 'error',
          summary: 'Lỗi',
          detail: error.error?.detail || 'Không thể gỡ ảnh'
        });
        this.isSubmitting = false;
        if (error.status === 401 || error.status === 403) {
          setTimeout(() => this.router.navigate(['/login']), 2000);
        }
      }
    });
  }

  togglePasswordForm(): void {
    this.showPasswordForm = !this.showPasswordForm;
    if (!this.showPasswordForm) {
      this.passwordForm.reset();
    }
  }

  checkPasswordReq(type: 'length' | 'upper' | 'lower' | 'number' | 'special'): boolean {
    const value = this.passwordForm.get('new_password')?.value || '';
    switch (type) {
      case 'length': return value.length >= 8;
      case 'upper': return /[A-Z]/.test(value);
      case 'lower': return /[a-z]/.test(value);
      case 'number': return /[0-9]/.test(value);
      case 'special': return /[@$!%*?&]/.test(value);
      default: return false;
    }
  }

  onChangePassword(): void {
    if (this.passwordForm.invalid) {
      return;
    }

    const { current_password, new_password, confirm_password } = this.passwordForm.value;

    if (new_password !== confirm_password) {
      this.messageService.add({
        severity: 'warn',
        summary: 'Lỗi',
        detail: 'Mật khẩu xác nhận không khớp'
      });
      return;
    }

    this.isChangingPassword = true;

    this.profileService.changePassword({ current_password, new_password }).subscribe({
      next: (response) => {
        if (response.EC === 0) {
          this.messageService.add({
            severity: 'success',
            summary: 'Thành công',
            detail: 'Đổi mật khẩu thành công'
          });
          this.passwordForm.reset();
          this.showPasswordForm = false;
        } else {
          this.messageService.add({
            severity: 'error',
            summary: 'Lỗi',
            detail: response.EM || 'Không thể đổi mật khẩu'
          });
        }
        this.isChangingPassword = false;
      },
      error: (error) => {
        console.error('Error changing password:', error);
        this.messageService.add({
          severity: 'error',
          summary: 'Lỗi',
          detail: error.error?.detail || 'Đổi mật khẩu thất bại'
        });
        this.isChangingPassword = false;
        if (error.status === 401 || error.status === 403) {
          setTimeout(() => this.router.navigate(['/login']), 2000);
        }
      }
    });
  }
}
