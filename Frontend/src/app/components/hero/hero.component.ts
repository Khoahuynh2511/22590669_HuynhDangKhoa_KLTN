import { Component, OnDestroy, OnInit } from '@angular/core';
import { Router, RouterModule } from '@angular/router';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Subject, Subscription, from, of, forkJoin } from 'rxjs';
import { debounceTime, distinctUntilChanged, switchMap, map, catchError, tap } from 'rxjs/operators';
import { TourService } from '../../services/tour.service';
import { HotelService } from '../../services/hotel.service';
import { FlightService, Airport } from '../../services/flight.service';
import { TrainService, TrainStation } from '../../services/train.service';
import { BusService, BusStation } from '../../services/bus.service';
import { Tour, TourPackageSearchRequest } from '../../shared/models/tour.model';
import { StateHotel } from '../../shared/models/hotelState.model';

@Component({
  selector: 'app-hero',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './hero.component.html',
  styleUrl: './hero.component.scss'
})
export class HeroComponent implements OnInit, OnDestroy {
  // Tab selector state
  activeTab: 'all' | 'tour' | 'hotel' | 'flight' | 'train' | 'bus' = 'all';

  // Search bindings per tab
  searchQuery: string = '';
  tourQuery: string = '';

  hotelQuery: string = '';
  hotelCheckIn: string = '';
  hotelCheckOut: string = '';
  hotelGuests: number = 2;
  hotelRooms: number = 1;

  flightDeparture: string = '';
  flightDestination: string = '';
  flightDate: string = '';
  flightPassengers: number = 1;

  trainDeparture: string = '';
  trainDestination: string = '';
  trainDate: string = '';
  trainPassengers: number = 1;

  busDeparture: string = '';
  busDestination: string = '';
  busDate: string = '';
  busPassengers: number = 1;

  // Dropdown data loaded on init
  hotelLocations: string[] = [];
  airports: Airport[] = [];
  trainStations: TrainStation[] = [];
  busStations: BusStation[] = [];

  // Autocomplete
  searchResults: {
    tours: Tour[];
    hotels: StateHotel[];
    flights: Airport[];
    trains: TrainStation[];
    buses: BusStation[];
  } = { tours: [], hotels: [], flights: [], trains: [], buses: [] };

  isLoading: boolean = false;
  showResults: boolean = false;
  private searchSubject = new Subject<string>();
  private searchSubscription: Subscription | undefined;
  private blurTimeout: any;

  constructor(
    private router: Router,
    private tourService: TourService,
    private hotelService: HotelService,
    private flightService: FlightService,
    private trainService: TrainService,
    private busService: BusService
  ) { }

  ngOnInit() {
    this.loadDropdownData();

    this.searchSubscription = this.searchSubject.pipe(
      debounceTime(300),
      distinctUntilChanged(),
      switchMap(query => {
        const trimmed = query ? query.trim() : '';
        if (!trimmed) {
          this.clearSearchResults();
          this.showResults = false;
          return of(null);
        }

        this.isLoading = true;
        this.showResults = true;

        if (this.activeTab === 'tour') {
          const request: TourPackageSearchRequest = { q: trimmed, limit: 5 };
          return from(this.tourService.searchTourPackages(request)).pipe(
            map(res => ({ tours: res.packages || [], hotels: [], flights: [], trains: [], buses: [] })),
            catchError(err => {
              console.error('Tour search error:', err);
              return of({ tours: [], hotels: [], flights: [], trains: [], buses: [] });
            }),
            tap(() => this.isLoading = false)
          );
        } else if (this.activeTab === 'hotel') {
          return this.hotelService.searchHotels(trimmed, 5).pipe(
            map(res => ({ tours: [], hotels: res.hotels || [], flights: [], trains: [], buses: [] })),
            catchError(err => {
              console.error('Hotel search error:', err);
              return of({ tours: [], hotels: [], flights: [], trains: [], buses: [] });
            }),
            tap(() => this.isLoading = false)
          );
        } else if (this.activeTab === 'flight') {
          const filteredAirports = this.filterAirportsLocally(trimmed);
          this.isLoading = false;
          return of({ tours: [], hotels: [], flights: filteredAirports, trains: [], buses: [] });
        } else if (this.activeTab === 'train') {
          const filteredStations = this.filterTrainStationsLocally(trimmed);
          this.isLoading = false;
          return of({ tours: [], hotels: [], flights: [], trains: filteredStations, buses: [] });
        } else if (this.activeTab === 'bus') {
          const filteredStations = this.filterBusStationsLocally(trimmed);
          this.isLoading = false;
          return of({ tours: [], hotels: [], flights: [], trains: [], buses: filteredStations });
        } else {
          // Global/All tab search - Queries tours and hotels concurrently, filters transport items locally
          const tourObs = from(this.tourService.searchTourPackages({ q: trimmed, limit: 3 })).pipe(
            map(res => res.packages || []),
            catchError(() => of([]))
          );
          const hotelObs = this.hotelService.searchHotels(trimmed, 3).pipe(
            map(res => res.hotels || []),
            catchError(() => of([]))
          );

          return forkJoin([tourObs, hotelObs]).pipe(
            map(([tours, hotels]) => {
              const flights = this.filterAirportsLocally(trimmed).slice(0, 3);
              const trains = this.filterTrainStationsLocally(trimmed).slice(0, 3);
              const buses = this.filterBusStationsLocally(trimmed).slice(0, 3);
              return { tours, hotels, flights, trains, buses };
            }),
            tap(() => this.isLoading = false)
          );
        }
      })
    ).subscribe(results => {
      if (results) {
        this.searchResults = results;
      }
    });
  }

  ngOnDestroy() {
    this.searchSubscription?.unsubscribe();
  }

  async loadDropdownData() {
    try {
      this.hotelService.getLocations().subscribe({
        next: (res) => {
          if (res.EC === 0) this.hotelLocations = res.data;
        },
        error: (err) => console.error('Error loading locations:', err)
      });

      const flightRes = await this.flightService.getAirports();
      if (flightRes.EC === 0) this.airports = flightRes.data;

      const trainRes = await this.trainService.getStations();
      if (trainRes.EC === 0) this.trainStations = trainRes.data;

      const busRes = await this.busService.getStations();
      if (busRes.EC === 0) this.busStations = busRes.data;
    } catch (e) {
      console.error('Error loading dropdown search lists:', e);
    }
  }

  onSearchChange(query: string) {
    this.searchSubject.next(query);
  }

  onFocus(query: string) {
    if (query && query.trim()) {
      this.showResults = true;
      this.onSearchChange(query);
    }
  }

  onBlur() {
    this.blurTimeout = setTimeout(() => {
      this.showResults = false;
    }, 250);
  }

  clearSearchResults() {
    this.searchResults = { tours: [], hotels: [], flights: [], trains: [], buses: [] };
  }

  filterAirportsLocally(query: string): Airport[] {
    const q = query.toLowerCase();
    return this.airports.filter(a =>
      a.code.toLowerCase().includes(q) ||
      a.city.toLowerCase().includes(q) ||
      a.name.toLowerCase().includes(q)
    );
  }

  filterTrainStationsLocally(query: string): TrainStation[] {
    const q = query.toLowerCase();
    return this.trainStations.filter(s =>
      s.code.toLowerCase().includes(q) ||
      s.city.toLowerCase().includes(q) ||
      s.name.toLowerCase().includes(q)
    );
  }

  filterBusStationsLocally(query: string): BusStation[] {
    const q = query.toLowerCase();
    return this.busStations.filter(s =>
      s.code.toLowerCase().includes(q) ||
      s.city.toLowerCase().includes(q) ||
      s.name.toLowerCase().includes(q)
    );
  }

  // Navigation handlers
  selectTour(tour: Tour) {
    this.router.navigate(['/tour-details', tour.package_id]);
    this.showResults = false;
  }

  selectHotel(hotel: StateHotel) {
    this.router.navigate(['/hotel/detail', hotel.hotel_id]);
    this.showResults = false;
  }

  selectAirport(airport: Airport) {
    this.flightDestination = airport.code;
    if (!this.flightDeparture) {
      this.flightDeparture = airport.code === 'SGN' ? 'HAN' : 'SGN';
    }
    this.activeTab = 'flight';
    this.showResults = false;
  }

  selectTrainStation(station: TrainStation) {
    this.trainDestination = station.code;
    if (!this.trainDeparture) {
      this.trainDeparture = station.code === 'SGO' ? 'HNO' : 'SGO';
    }
    this.activeTab = 'train';
    this.showResults = false;
  }

  selectBusStation(station: BusStation) {
    this.busDestination = station.code;
    if (!this.busDeparture) {
      this.busDeparture = station.code === 'BXSG' ? 'BXHN' : 'BXSG';
    }
    this.activeTab = 'bus';
    this.showResults = false;
  }

  // Tab switch
  switchTab(tab: 'all' | 'tour' | 'hotel' | 'flight' | 'train' | 'bus') {
    this.activeTab = tab;
    this.clearSearchResults();
    this.showResults = false;
  }

  // Form Submission/Redirect handlers
  onSearch() {
    if (this.blurTimeout) {
      clearTimeout(this.blurTimeout);
    }
    if (this.searchQuery && this.searchQuery.trim()) {
      this.showResults = true;
      this.onSearchChange(this.searchQuery);
    }
  }

  searchTour() {
    if (this.blurTimeout) {
      clearTimeout(this.blurTimeout);
    }
    if (this.tourQuery && this.tourQuery.trim()) {
      this.showResults = true;
      this.onSearchChange(this.tourQuery);
    }
  }

  searchHotel() {
    if (this.blurTimeout) {
      clearTimeout(this.blurTimeout);
    }
    if (this.hotelQuery && this.hotelQuery.trim()) {
      this.showResults = true;
      this.onSearchChange(this.hotelQuery);
    }
  }

  searchFlight() {
    const queryParams: any = {};
    if (this.flightDeparture) queryParams.departure = this.flightDeparture;
    if (this.flightDestination) queryParams.destination = this.flightDestination;
    if (this.flightDate) queryParams.date = this.flightDate;
    if (this.flightPassengers) queryParams.passengers = this.flightPassengers;
    this.router.navigate(['/flights'], { queryParams });
  }

  searchTrain() {
    const queryParams: any = {};
    if (this.trainDeparture) queryParams.departure = this.trainDeparture;
    if (this.trainDestination) queryParams.destination = this.trainDestination;
    if (this.trainDate) queryParams.date = this.trainDate;
    if (this.trainPassengers) queryParams.passengers = this.trainPassengers;
    this.router.navigate(['/trains'], { queryParams });
  }

  searchBus() {
    const queryParams: any = {};
    if (this.busDeparture) queryParams.departure = this.busDeparture;
    if (this.busDestination) queryParams.destination = this.busDestination;
    if (this.busDate) queryParams.date = this.busDate;
    if (this.busPassengers) queryParams.passengers = this.busPassengers;
    this.router.navigate(['/buses'], { queryParams });
  }

  // Date utilities
  get minDate(): string {
    const today = new Date();
    const yyyy = today.getFullYear();
    const mm = String(today.getMonth() + 1).padStart(2, '0');
    const dd = String(today.getDate()).padStart(2, '0');
    return `${yyyy}-${mm}-${dd}`;
  }

  get minCheckOutDate(): string {
    return this.hotelCheckIn || this.minDate;
  }

  formatPrice(price: number): string {
    if (price === undefined || price === null) return 'Liên hệ';
    return new Intl.NumberFormat('vi-VN', {
      style: 'currency',
      currency: 'VND'
    }).format(price);
  }

  getHotelImageUrl(hotel: StateHotel): string {
    if (!hotel.image_urls) return 'assets/img/default-hotel.jpg';
    const delimiter = hotel.image_urls.includes('|') ? '|' : ',';
    const firstUrl = hotel.image_urls.split(delimiter)[0]?.trim();
    return firstUrl || 'assets/img/default-hotel.jpg';
  }

  getTourImageUrl(tour: Tour): string {
    if (tour.image_url) return tour.image_url;
    if (tour.image_urls) {
      const delimiter = tour.image_urls.includes('|') ? '|' : ',';
      const firstUrl = tour.image_urls.split(delimiter)[0]?.trim();
      if (firstUrl) return firstUrl;
    }
    return 'assets/img/default-tour.jpg';
  }
}
