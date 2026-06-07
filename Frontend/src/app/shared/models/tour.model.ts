export interface TourItineraryDay {
  title: string;
  hotel: string;
  meals: string;
  morning?: string;
  afternoon?: string;
  evening?: string;
  late_afternoon?: string;
}

export interface TourItinerary {
  day1?: TourItineraryDay;
  day2?: TourItineraryDay;
  day3?: TourItineraryDay;
  day4?: TourItineraryDay;
  day5?: TourItineraryDay;
  note?: string;
  highlights?: string[];
  best_season?: string[];
  photo_spots?: string[];
  must_try_food?: string[];
  [key: string]: TourItineraryDay | string | string[] | undefined;
}

export interface Tour {
  package_id: string;
  package_name: string;
  destination: string;
  departure_location?: string;
  duration_days: number;
  price: number;
  original_price?: number;
  discount?: number;
  rating?: number;
  reviews?: number;
  description?: string;
  highlights?: string[];
  included_services?: string[];
  image_url?: string;
  image_urls?: string;
  available_dates?: string[];
  max_participants?: number;
  category?: string;
  available_slots?: number;
  start_date?: string;
  end_date?: string;
  includes?: string[];
  excludes?: string[];
  itinerary?: TourItinerary;
  is_active?: boolean;
  cuisine?: string;
  suitable_for?: string;
  created_at?: string;
  updated_at?: string;
}

export interface TourSearchParams {
  destination?: string;
  departure_location?: string;
  price_min?: number;
  price_max?: number;
  duration_min?: number;
  duration_max?: number;
  category?: string;
  date_from?: string;
  date_to?: string;
}

export interface ChatMessage {
  message: string;
  conversation_id?: string | null;
  user_id?: string | null;
}

export interface StreamEvent {
  type: 'start' | 'token' | 'recommendations' | 'complete' | 'error';
  content?: string;
  conversation_id?: string;
  user_id?: string;
  data?: Tour[];
  full_response?: string;
}

export interface TourRecommendation {
  tours: Tour[];
  reason?: string;
  context?: string;
}

export interface TourPackageListResponse {
  EC: number;
  EM: string;
  total: number;
  packages: Tour[];
}

export interface TourPackageParams {
  is_active?: boolean | null;
  destination?: string | null;
  limit?: number | null;
  offset?: number | null;
}

export interface TourPackageDetailResponse {
  EC: number;
  EM: string;
  package: Tour;
}

export interface TourPackageRecommendRequest {
  user_id: string;
  k: number;
}

export interface TourPackageSearchRequest {
  q?: string;
  max_price?: number;
  duration?: number;
  destination?: string;
  limit?: number;
}

export interface TourPackageSearchResponse {
  EC: number;
  EM: string;
  found: number;
  packages: Tour[];
}

