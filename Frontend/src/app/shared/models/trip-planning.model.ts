/**
 * Shared models for Trip Planning feature.
 * Used by AI Chatbot component, TripPlannerService, and ChatWidget.
 */

export interface ActivitySlot {
  activity_id: string;
  name: string;
  description?: string;
  price: number;
  category?: string;
  time_slot?: string;
  location?: string;
  image_url?: string;
  duration_hours?: number;
  difficulty?: string;
  included_services?: string[];
}

export interface ItineraryDay {
  morning: ActivitySlot | null;
  afternoon: ActivitySlot | null;
  evening: ActivitySlot | null;
}

export interface TransportData {
  flights?: any[];
  trains?: any[];
}

export interface CheckoutData {
  plan_id?: string;
  booking_id?: string;
  payment_id?: string;
  payment_url?: string;
  total_price?: number;
  booking_completed?: boolean;
  awaiting_payment?: boolean;
}

export interface TripPlanStreamEvent {
  type: 'start' | 'step' | 'token' | 'activities' | 'itinerary_confirmed' | 'flights' | 'trains' | 'checkout' | 'done' | 'error';
  conversation_id?: string;
  user_id?: string;
  room_id?: string;
  step?: number;
  message?: string;
  content?: string;
  waiting_for_input?: boolean;
  suggestions?: string[];
  is_complete?: boolean;
  data?: any;
  error?: string;
}
