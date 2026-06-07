export interface TravelNews {
  news_id: string;
  title: string;
  url: string;
  snippet?: string;
  date?: string;
  last_updated?: string;
  source_type: 'news' | 'guide';
  destination?: string;
  created_at?: string;
  updated_at?: string;
}

export interface TravelNewsResponse {
  EC: number;
  EM: string;
  data: TravelNews[];
  count: number;
  date: string;
  source: string;
  total: number;
}

export interface TravelNewsSearchResponse {
  EC: number;
  EM: string;
  data: TravelNews[];
  page: number;
  limit: number;
  total: number;
  total_pages: number;
}
