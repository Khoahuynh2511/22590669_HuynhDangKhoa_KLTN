import { Injectable } from '@angular/core';
import { ConfigService } from './../config.service';

export interface TourPackage {
  package_id?: string;
  package_name: string;
  destination: string;
  description: string;
  duration_days: number;
  price: number;
  available_slots: number;
  start_date: string;
  end_date: string;
  image_urls: string;
  cuisine: string;
  suitable_for: string;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface TourPackageListResponse {
  EC: number;
  EM: string;
  total: number;
  packages: TourPackage[];
}

export interface TourPackageDetailResponse {
  EC: number;
  EM: string;
  package: TourPackage;
}

export interface TourPackageCreateRequest {
  package_name: string;
  destination: string;
  description: string;
  duration_days: number;
  price: number;
  available_slots: number;
  start_date: string;
  end_date: string;
  image_urls: string;
  cuisine: string;
  suitable_for: string;
  is_active: boolean;
}

export interface TourPackageUpdateRequest {
  package_name?: string;
  destination?: string;
  description?: string;
  duration_days?: number;
  price?: number;
  available_slots?: number;
  start_date?: string;
  end_date?: string;
  image_urls?: string;
  cuisine?: string;
  suitable_for?: string;
  is_active?: boolean;
}

export interface ManageImagesResponse {
  EC: number;
  EM: string;
  image_urls: string[];
  total_images: number;
}

export interface BulkCreateResponse {
  EC: number;
  EM: string;
  total_processed: number;
  successful: number;
  failed: number;
  created_packages: TourPackage[];
  errors: Array<{
    row: number;
    error: string;
  }>;
  parsing_errors: string[];
}

@Injectable({
  providedIn: 'root'
})
export class AdminTourService {
  constructor(private configService: ConfigService) { }

  private get apiBaseUrl(): string {
    return `${this.configService.getApiUrl()}/tour-packages`;
  }

  async getTourPackages(
    is_active?: boolean,
    destination?: string,
    limit: number = 100,
    offset: number = 0
  ): Promise<TourPackageListResponse> {
    try {
      const params = new URLSearchParams();
      if (is_active !== undefined) params.append('is_active', is_active.toString());
      if (destination) params.append('destination', destination);
      params.append('limit', limit.toString());
      params.append('offset', offset.toString());

      const response = await fetch(`${this.apiBaseUrl}/?${params}`);
      if (!response.ok) {
        throw new Error(`Failed to fetch tour packages: ${response.status}`);
      }
      return await response.json();
    } catch (error) {
      console.error('Error fetching tour packages:', error);
      throw error;
    }
  }

  async getTourPackageById(packageId: string): Promise<TourPackageDetailResponse> {
    try {
      const response = await fetch(`${this.apiBaseUrl}/${packageId}`);
      if (!response.ok) {
        throw new Error(`Failed to fetch tour package: ${response.status}`);
      }
      return await response.json();
    } catch (error) {
      console.error('Error fetching tour package:', error);
      throw error;
    }
  }

  async createTourPackage(packageData: TourPackageCreateRequest): Promise<TourPackageDetailResponse> {
    try {
      const response = await fetch(this.apiBaseUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(packageData),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || `Failed to create tour package: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error creating tour package:', error);
      throw error;
    }
  }

  async updateTourPackage(
    packageId: string,
    packageData: TourPackageUpdateRequest
  ): Promise<TourPackageDetailResponse> {
    try {
      const response = await fetch(`${this.apiBaseUrl}/${packageId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(packageData),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || `Failed to update tour package: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error updating tour package:', error);
      throw error;
    }
  }

  async deleteTourPackage(packageId: string): Promise<{ EC: number; EM: string }> {
    try {
      const response = await fetch(`${this.apiBaseUrl}/${packageId}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        throw new Error(`Failed to delete tour package: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error deleting tour package:', error);
      throw error;
    }
  }

  async createTourPackageWithImages(
    packageData: Omit<TourPackageCreateRequest, 'image_urls'>,
    images: File[]
  ): Promise<TourPackageDetailResponse> {
    try {
      const formData = new FormData();

      // Append package data
      Object.entries(packageData).forEach(([key, value]) => {
        formData.append(key, value.toString());
      });

      // Append images
      images.forEach((file) => {
        formData.append('images', file);
      });

      const response = await fetch(`${this.apiBaseUrl}/`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || `Failed to create tour package: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error creating tour package with images:', error);
      throw error;
    }
  }

  async manageImages(
    packageId: string,
    images: File[],
    replaceExisting: boolean = false
  ): Promise<ManageImagesResponse> {
    try {
      const formData = new FormData();
      images.forEach((file) => {
        formData.append('images', file);
      });

      const response = await fetch(
        `${this.apiBaseUrl}/${packageId}/images?replace_existing=${replaceExisting}`,
        {
          method: 'POST',
          body: formData,
        }
      );

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || `Failed to manage images: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error managing images:', error);
      throw error;
    }
  }

  async createTourPackagesFromCSV(file: File): Promise<BulkCreateResponse> {
    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch(`${this.apiBaseUrl}/bulk/csv`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || `Failed to upload CSV: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error uploading CSV:', error);
      throw error;
    }
  }

  // Filter APIs
  async filterToursByMonth(
    month: number,
    year: number,
    dateType: 'start_date' | 'end_date' = 'start_date',
    isActive?: boolean,
    limit: number = 100,
    offset: number = 0
  ): Promise<TourPackageListResponse> {
    try {
      const params = new URLSearchParams();
      params.append('month', month.toString());
      params.append('year', year.toString());
      params.append('date_type', dateType);
      if (isActive !== undefined) params.append('is_active', isActive.toString());
      params.append('limit', limit.toString());
      params.append('offset', offset.toString());

      const response = await fetch(`${this.apiBaseUrl}/filter/by-month?${params}`);
      if (!response.ok) {
        throw new Error(`Failed to filter tours by month: ${response.status}`);
      }
      return await response.json();
    } catch (error) {
      console.error('Error filtering tours by month:', error);
      throw error;
    }
  }

  async filterToursByYear(
    year: number,
    dateType: 'start_date' | 'end_date' = 'start_date',
    isActive?: boolean,
    limit: number = 100,
    offset: number = 0
  ): Promise<TourPackageListResponse> {
    try {
      const params = new URLSearchParams();
      params.append('year', year.toString());
      params.append('date_type', dateType);
      if (isActive !== undefined) params.append('is_active', isActive.toString());
      params.append('limit', limit.toString());
      params.append('offset', offset.toString());

      const response = await fetch(`${this.apiBaseUrl}/filter/by-year?${params}`);
      if (!response.ok) {
        throw new Error(`Failed to filter tours by year: ${response.status}`);
      }
      return await response.json();
    } catch (error) {
      console.error('Error filtering tours by year:', error);
      throw error;
    }
  }

  async filterToursByDate(
    startDate: string,
    endDate: string,
    isActive?: boolean,
    limit: number = 100,
    offset: number = 0
  ): Promise<TourPackageListResponse> {
    try {
      const params = new URLSearchParams();
      params.append('start_date', startDate);
      params.append('end_date', endDate);
      if (isActive !== undefined) params.append('is_active', isActive.toString());
      params.append('limit', limit.toString());
      params.append('offset', offset.toString());

      const response = await fetch(`${this.apiBaseUrl}/filter/by-date?${params}`);
      if (!response.ok) {
        throw new Error(`Failed to filter tours by date: ${response.status}`);
      }
      return await response.json();
    } catch (error) {
      console.error('Error filtering tours by date:', error);
      throw error;
    }
  }

  async filterToursByPriceRange(
    minPrice?: number,
    maxPrice?: number,
    priceSegment?: 'budget' | 'mid' | 'premium',
    isActive?: boolean,
    limit: number = 100,
    offset: number = 0
  ): Promise<TourPackageListResponse> {
    try {
      const params = new URLSearchParams();
      if (minPrice !== undefined) params.append('min_price', minPrice.toString());
      if (maxPrice !== undefined) params.append('max_price', maxPrice.toString());
      if (priceSegment) params.append('price_segment', priceSegment);
      if (isActive !== undefined) params.append('is_active', isActive.toString());
      params.append('limit', limit.toString());
      params.append('offset', offset.toString());

      const response = await fetch(`${this.apiBaseUrl}/filter/by-price-range?${params}`);
      if (!response.ok) {
        throw new Error(`Failed to filter tours by price range: ${response.status}`);
      }
      return await response.json();
    } catch (error) {
      console.error('Error filtering tours by price range:', error);
      throw error;
    }
  }

  /**
   * Cancel tour package and all related bookings
   */
  async cancelTourPackage(packageId: string, reason?: string): Promise<{ EC: number; EM: string; cancelled_bookings: number; notifications_sent: number }> {
    try {
      const token = localStorage.getItem('access_token');
      const params = new URLSearchParams();
      if (reason) params.append('reason', reason);

      const response = await fetch(`${this.apiBaseUrl}/${packageId}/cancel?${params}`, {
        method: 'POST',
        headers: {
          'Authorization': token ? `Bearer ${token}` : '',
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || `Failed to cancel tour package: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error cancelling tour package:', error);
      throw error;
    }
  }
}
