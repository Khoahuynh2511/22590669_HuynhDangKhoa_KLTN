import { Tour } from '../models/tour.model';

type TourPriceFields = Pick<Tour, 'price' | 'original_price' | 'discount'>;

export function getTourUnitPrice(tour: TourPriceFields | null | undefined): number {
  if (!tour) {
    return 0;
  }

  if (tour.discount && tour.original_price) {
    return Math.round(tour.original_price * (1 - tour.discount / 100));
  }

  return tour.price || 0;
}

export function clampTourPeopleCount(value: number, availableSlots?: number): number {
  let people = Number.isFinite(value) ? Math.floor(value) : 1;
  if (people < 1) {
    people = 1;
  }

  if (availableSlots !== undefined && availableSlots > 0 && people > availableSlots) {
    people = availableSlots;
  }

  return people;
}

export function calculateTourSubtotal(
  tour: TourPriceFields | null | undefined,
  numberOfPeople: number
): number {
  const people = clampTourPeopleCount(numberOfPeople);
  return getTourUnitPrice(tour) * people;
}
