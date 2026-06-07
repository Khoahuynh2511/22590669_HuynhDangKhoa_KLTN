/**
 * User Profile Models
 */

export interface UserProfile {
  user_id: string;
  email: string;
  full_name: string | null;
  phone_number: string | null;
  profile_picture: string | null;
  role: 'user' | 'admin';
  is_active: boolean;
  created_at: string;
  updated_at: string | null;
}

export interface UserProfileResponse {
  EC: number;
  EM: string;
  data: UserProfile | null;
}

export interface UpdateProfileRequest {
  full_name?: string;
  phone_number?: string;
  profile_picture?: string;
}

export interface UpdateProfileResponse {
  EC: number;
  EM: string;
  data: UserProfile | null;
}
