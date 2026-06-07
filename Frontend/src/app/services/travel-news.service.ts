import { Injectable } from '@angular/core';
import { ConfigService } from './config.service';
import { TravelNews, TravelNewsResponse, TravelNewsSearchResponse } from '../shared/models/travel-news.model';

@Injectable({
  providedIn: 'root'
})
export class TravelNewsService {
  constructor(private configService: ConfigService) { }

  private get apiBaseUrl(): string {
    return this.configService.getApiUrl();
  }

  async getTravelNews(
    k: number = 6,
    sourceType?: string,
    destination?: string
  ): Promise<TravelNewsResponse> {
    try {
      const queryParams = new URLSearchParams();
      
      if (sourceType) {
        queryParams.append('source_type', sourceType);
      }
      if (destination) {
        queryParams.append('destination', destination);
      }

      const basePath = `${this.apiBaseUrl}/travel-news/${k}`;
      const url = `${basePath}${queryParams.toString() ? '?' + queryParams.toString() : ''}`;
      
      console.log('Fetching travel news from URL:', url);
      
      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json'
        }
      });
      
      console.log('Travel news response status:', response.status, response.statusText);
      
      if (!response.ok) {
        let errorMessage = '';
        if (response.status === 404) {
          errorMessage = 'Không tìm thấy endpoint tin tức du lịch.';
        } else if (response.status === 422) {
          errorMessage = 'Dữ liệu yêu cầu không hợp lệ.';
          try {
            const errorData = await response.json();
            if (errorData.detail && Array.isArray(errorData.detail)) {
              const validationErrors = errorData.detail.map((d: any) => d.msg).join(', ');
              errorMessage = `Lỗi validation: ${validationErrors}`;
            } else if (errorData.EM) {
              errorMessage = errorData.EM;
            }
          } catch {
            const errorText = await response.text();
            if (errorText) {
              console.error('API Error Response:', errorText);
            }
          }
        } else if (response.status === 500) {
          errorMessage = 'Lỗi máy chủ khi tải tin tức du lịch. Vui lòng thử lại sau.';
        } else if (response.status >= 400 && response.status < 500) {
          errorMessage = 'Yêu cầu không hợp lệ khi tải tin tức du lịch.';
        } else {
          errorMessage = `Lỗi khi tải tin tức du lịch (${response.status}).`;
        }
        
        if (response.status !== 422) {
          try {
            const errorData = await response.json();
            if (errorData.EM) {
              errorMessage = errorData.EM;
            }
          } catch {
            const errorText = await response.text();
            if (errorText) {
              console.error('API Error Response:', errorText);
            }
          }
        }
        
        throw new Error(errorMessage);
      }
      
      const data: TravelNewsResponse = await response.json();
      console.log('API Response data:', data);
      
      if (data.EC !== 0) {
        console.error('API returned error code:', data.EC, 'Message:', data.EM);
        throw new Error(data.EM || 'Lỗi khi tải tin tức du lịch từ server.');
      }
      
      if (!data.data || !Array.isArray(data.data)) {
        console.error('Invalid data format:', data);
        throw new Error('Định dạng dữ liệu không hợp lệ: data không phải là mảng.');
      }
      
      console.log('Travel news loaded from API:', data.data.length, 'Total:', data.total);
      
      return data;
    } catch (error: any) {
      console.error('Error fetching travel news from API:', error);
      if (error instanceof TypeError && error.message.includes('fetch')) {
        throw new Error('Không thể kết nối đến server. Vui lòng kiểm tra kết nối internet.');
      }
      throw error;
    }
  }

  async searchTravelNews(
    keywords: string,
    sourceType?: string,
    page: number = 1,
    limit: number = 20
  ): Promise<TravelNewsSearchResponse> {
    try {
      const requestBody: any = {
        keywords: keywords.trim(),
        page: Math.floor(page),
        limit: Math.floor(limit)
      };

      if (sourceType && sourceType !== 'all') {
        requestBody.source_type = sourceType;
      }

      const url = `${this.apiBaseUrl}/travel-news/search`;
      
      console.log('Searching travel news from URL:', url);
      console.log('Request body:', requestBody);
      
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(requestBody)
      });
      
      console.log('Travel news search response status:', response.status, response.statusText);
      
      if (!response.ok) {
        let errorMessage = '';
        if (response.status === 404) {
          errorMessage = 'Không tìm thấy endpoint tìm kiếm tin tức du lịch.';
        } else if (response.status === 422) {
          errorMessage = 'Dữ liệu yêu cầu không hợp lệ.';
          try {
            const errorData = await response.json();
            if (errorData.detail && Array.isArray(errorData.detail)) {
              const validationErrors = errorData.detail.map((d: any) => d.msg).join(', ');
              errorMessage = `Lỗi validation: ${validationErrors}`;
            } else if (errorData.EM) {
              errorMessage = errorData.EM;
            }
          } catch {
            const errorText = await response.text();
            if (errorText) {
              console.error('API Error Response:', errorText);
            }
          }
        } else if (response.status === 500) {
          errorMessage = 'Lỗi máy chủ khi tìm kiếm tin tức du lịch. Vui lòng thử lại sau.';
        } else if (response.status >= 400 && response.status < 500) {
          errorMessage = 'Yêu cầu không hợp lệ khi tìm kiếm tin tức du lịch.';
        } else {
          errorMessage = `Lỗi khi tìm kiếm tin tức du lịch (${response.status}).`;
        }
        
        if (response.status !== 422) {
          try {
            const errorData = await response.json();
            if (errorData.EM) {
              errorMessage = errorData.EM;
            }
          } catch {
            const errorText = await response.text();
            if (errorText) {
              console.error('API Error Response:', errorText);
            }
          }
        }
        
        throw new Error(errorMessage);
      }
      
      const data: TravelNewsSearchResponse = await response.json();
      console.log('API Response data:', data);
      
      if (data.EC !== 0) {
        console.error('API returned error code:', data.EC, 'Message:', data.EM);
        throw new Error(data.EM || 'Lỗi khi tìm kiếm tin tức du lịch từ server.');
      }
      
      if (!data.data || !Array.isArray(data.data)) {
        console.error('Invalid data format:', data);
        throw new Error('Định dạng dữ liệu không hợp lệ: data không phải là mảng.');
      }
      
      console.log('Travel news search results:', data.data.length, 'Total:', data.total, 'Pages:', data.total_pages);
      
      return data;
    } catch (error: any) {
      console.error('Error searching travel news from API:', error);
      if (error instanceof TypeError && error.message.includes('fetch')) {
        throw new Error('Không thể kết nối đến server. Vui lòng kiểm tra kết nối internet.');
      }
      throw error;
    }
  }

  async getPaginatedTravelNews(
    sourceType?: string,
    page: number = 1,
    limit: number = 20
  ): Promise<TravelNewsSearchResponse> {
    try {
      const queryParams = new URLSearchParams();
      
      if (sourceType && sourceType !== 'all') {
        queryParams.append('source_type', sourceType);
      }
      queryParams.append('page', Math.floor(page).toString());
      queryParams.append('limit', Math.floor(limit).toString());

      const url = `${this.apiBaseUrl}/travel-news/all${queryParams.toString() ? '?' + queryParams.toString() : ''}`;
      
      console.log('Fetching paginated travel news from URL:', url);
      
      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json'
        }
      });
      
      console.log('Paginated travel news response status:', response.status, response.statusText);
      
      if (!response.ok) {
        let errorMessage = '';
        if (response.status === 404) {
          errorMessage = 'Không tìm thấy endpoint danh sách tin tức du lịch.';
        } else if (response.status === 422) {
          errorMessage = 'Dữ liệu yêu cầu không hợp lệ.';
          try {
            const errorData = await response.json();
            if (errorData.detail && Array.isArray(errorData.detail)) {
              const validationErrors = errorData.detail.map((d: any) => d.msg).join(', ');
              errorMessage = `Lỗi validation: ${validationErrors}`;
            } else if (errorData.EM) {
              errorMessage = errorData.EM;
            }
          } catch {
            const errorText = await response.text();
            if (errorText) {
              console.error('API Error Response:', errorText);
            }
          }
        } else if (response.status === 500) {
          errorMessage = 'Lỗi máy chủ khi tải danh sách tin tức du lịch. Vui lòng thử lại sau.';
        } else if (response.status >= 400 && response.status < 500) {
          errorMessage = 'Yêu cầu không hợp lệ khi tải danh sách tin tức du lịch.';
        } else {
          errorMessage = `Lỗi khi tải danh sách tin tức du lịch (${response.status}).`;
        }
        
        if (response.status !== 422) {
          try {
            const errorData = await response.json();
            if (errorData.EM) {
              errorMessage = errorData.EM;
            }
          } catch {
            const errorText = await response.text();
            if (errorText) {
              console.error('API Error Response:', errorText);
            }
          }
        }
        
        throw new Error(errorMessage);
      }
      
      const data: TravelNewsSearchResponse = await response.json();
      console.log('API Response data:', data);
      
      if (data.EC !== 0) {
        console.error('API returned error code:', data.EC, 'Message:', data.EM);
        throw new Error(data.EM || 'Lỗi khi tải danh sách tin tức du lịch từ server.');
      }
      
      if (!data.data || !Array.isArray(data.data)) {
        console.error('Invalid data format:', data);
        throw new Error('Định dạng dữ liệu không hợp lệ: data không phải là mảng.');
      }
      
      console.log('Paginated travel news loaded:', data.data.length, 'Total:', data.total, 'Pages:', data.total_pages);
      
      return data;
    } catch (error: any) {
      console.error('Error fetching paginated travel news from API:', error);
      if (error instanceof TypeError && error.message.includes('fetch')) {
        throw new Error('Không thể kết nối đến server. Vui lòng kiểm tra kết nối internet.');
      }
      throw error;
    }
  }
}
