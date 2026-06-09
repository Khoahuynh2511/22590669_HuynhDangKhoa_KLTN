
export interface StateHotel {
  hotel_id: string;
  hotel_name: string;
  location: string;
  description?: string;
  address?: string;
  star_rating: number;
  review_score: number;
  review_count: number;
  price: number;
  original_price: number;
  discount: number;
  amenities: string[];
  image_urls: string;
  available_rooms: number;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
}
