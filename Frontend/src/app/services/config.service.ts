import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';
import { environment } from '../../environments/environment';

export interface AppConfig {
  apiUrl: string;
}

@Injectable({
  providedIn: 'root'
})
export class ConfigService {
  private config: AppConfig | null = null;
  private configLoaded = false;

  constructor(private http: HttpClient) {}

  async loadConfig(): Promise<AppConfig> {
    if (this.configLoaded && this.config) {
      return this.config;
    }

    // Development mode: always use environment config (localhost backend)
    if (!environment.production) {
      this.config = {
        apiUrl: environment.apiUrl
      };
      this.configLoaded = true;
      console.log('[ConfigService] Development mode - using environment config:', this.config.apiUrl);
      return this.config;
    }

    // Production mode: load from config.json (served by Nginx, can be relative path)
    try {
      const config = await firstValueFrom(
        this.http.get<AppConfig>('/assets/config.json')
      );
      this.config = config;
      this.configLoaded = true;
      console.log('[ConfigService] Production mode - loaded config.json:', this.config.apiUrl);
      return config;
    } catch (error) {
      console.warn('Failed to load config.json, falling back to environment config');
      this.config = {
        apiUrl: environment.apiUrl
      };
      this.configLoaded = true;
      return this.config;
    }
  }

  getApiUrl(): string {
    if (!this.config) {
      return environment.apiUrl;
    }
    return this.config.apiUrl;
  }

  setConfig(config: AppConfig): void {
    this.config = config;
    this.configLoaded = true;
  }
}

