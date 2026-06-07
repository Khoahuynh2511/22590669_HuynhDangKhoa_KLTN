import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class HotelService {

  constructor() { }

  public hotelState: BehaviorSubject<any[]> = new BehaviorSubject<any>([
    {
      name: 'Bukit Vipassana Hotel',
      rating: 8.4,
      reviews: 1200,
      location: 'Lembang, Bandung',
      price: 368569,
      originalPrice: 491125,
      discount: 25,
      amenities: ['Khu vui chơi trẻ em', 'Dịch vụ massage', 'Spa'],
      imageUrl: 'img/hotel.jpeg',
    },
    {
      name: 'Bukit Bali Hotel',
      rating: 8.4,
      reviews: 1200,
      location: 'Ubud, Bali',
      price: 368569,
      originalPrice: 491125,
      discount: 25,
      amenities: ['Khu vui chơi trẻ em', 'Dịch vụ massage', 'Bãi biển'],
      imageUrl: 'img/hotel.jpeg',
    },
    {
      name: 'Bukit Papandayan Hotel',
      rating: 8.4,
      reviews: 1200,
      location: 'Papandayan, Garut',
      price: 368569,
      originalPrice: 491125,
      discount: 25,
      amenities: ['Khu vui chơi trẻ em', 'Dịch vụ massage', 'Suối nước nóng'],
      imageUrl: 'img/hotel.jpeg',
    },
  ])

  public filterHotels(
    name?: string,
    location?: string,
    priceRange?: { min: number; max: number }
  ): any[] {
    const hotels = this.hotelState.getValue(); // Get current hotels

    const filteredHotels = hotels.filter((hotel) => {
      const matchesName = name ? hotel.name.toLowerCase().includes(name.toLowerCase()) : true;
      const matchesLocation = location ? hotel.location.toLowerCase().includes(location.toLowerCase()) : true;
      const matchesPrice =
        priceRange && priceRange.min !== undefined && priceRange.max !== undefined
          ? hotel.price >= priceRange.min && hotel.price <= priceRange.max
          : true;

      return matchesName && matchesLocation;
      // return matchesName && matchesLocation && matchesPrice;
    });

    return filteredHotels;
  }






}
