import { Component, Input, Output, EventEmitter, OnInit, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { BusBookingService } from '../../services/bus-booking.service';
import { TrainBookingService } from '../../services/train-booking.service';
import { FlightBookingService } from '../../services/flight-booking.service';
import { firstValueFrom } from 'rxjs';

interface Seat {
  code: string;
  status: 'available' | 'selected' | 'occupied';
  row: number;
  col: string;
  deck?: 'lower' | 'upper'; // for Bus
  cabin?: number; // for Train
}

@Component({
  selector: 'app-seat-selection',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './seat-selection.component.html',
  styleUrl: './seat-selection.component.scss'
})
export class SeatSelectionComponent implements OnInit, OnChanges {
  @Input() type: 'bus' | 'train' | 'flight' = 'bus';
  @Input() transportId: string = '';
  @Input() selectedSeatTypeOrClass: string = ''; // standard, vip, economy, business etc.
  @Input() maxSeats: number = 9;
  @Input() availableSeatsCount: number = 0;

  @Output() seatsSelected = new EventEmitter<string[]>();

  seats: Seat[] = [];
  occupiedSeats: string[] = [];
  selectedSeatsList: string[] = [];
  isLoading = false;

  // Specific state
  activeDeck: 'lower' | 'upper' = 'lower'; // for bus

  constructor(
    private busBookingService: BusBookingService,
    private trainBookingService: TrainBookingService,
    private flightBookingService: FlightBookingService
  ) {}

  async ngOnInit() {
    await this.loadOccupiedSeats();
    this.generateSeats();
  }

  async ngOnChanges(changes: SimpleChanges) {
    if (changes['transportId'] || changes['selectedSeatTypeOrClass'] || changes['availableSeatsCount']) {
      await this.loadOccupiedSeats();
      this.generateSeats();
    }
  }

  async loadOccupiedSeats() {
    if (!this.transportId) return;
    this.isLoading = true;
    try {
      let res: any;
      if (this.type === 'bus') {
        res = await firstValueFrom(this.busBookingService.getOccupiedSeats(this.transportId));
      } else if (this.type === 'train') {
        res = await firstValueFrom(this.trainBookingService.getOccupiedSeats(this.transportId));
      } else if (this.type === 'flight') {
        res = await firstValueFrom(this.flightBookingService.getOccupiedSeats(this.transportId));
      }
      if (res && res.EC === 0) {
        this.occupiedSeats = res.data || [];
      }
    } catch (error) {
      console.error('Error fetching occupied seats:', error);
    } finally {
      this.isLoading = false;
      this.generatePseudoOccupiedSeats();
    }
  }

  generatePseudoOccupiedSeats() {
    // Generate pseudo-random occupied seats based on transportId to make it look full even if DB is clean
    if (!this.transportId) return;
    const seed = this.transportId.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
    
    let allSeatsCodes: string[] = [];
    if (this.type === 'bus') {
      // 36 seats: A01-A18 (Lower), B01-B18 (Upper)
      for (let i = 1; i <= 18; i++) {
        allSeatsCodes.push(`A${i.toString().padStart(2, '0')}`);
        allSeatsCodes.push(`B${i.toString().padStart(2, '0')}`);
      }
    } else if (this.type === 'train') {
      // 6 cabins x 4 beds = 24 seats (beds)
      for (let c = 1; c <= 6; c++) {
        for (let b = 1; b <= 4; b++) {
          allSeatsCodes.push(`C${c}-B${b}`);
        }
      }
    } else if (this.type === 'flight') {
      // Rows 1-3 (Business A C D F), Rows 4-15 (Economy A B C D E F)
      const economyCols = ['A', 'B', 'C', 'D', 'E', 'F'];
      const businessCols = ['A', 'C', 'D', 'F'];
      for (let r = 1; r <= 3; r++) {
        businessCols.forEach(col => allSeatsCodes.push(`${r}${col}`));
      }
      for (let r = 4; r <= 15; r++) {
        economyCols.forEach(col => allSeatsCodes.push(`${r}${col}`));
      }
    }

    let pseudoOccupied: string[] = [];

    // Helper to sort seat codes deterministically based on seed
    const sortSeats = (codes: string[]) => {
      return [...codes].map((code, idx) => {
        const val = Math.sin(seed + idx + code.charCodeAt(0)) * 10000;
        const score = val - Math.floor(val);
        return { code, score };
      })
      .sort((a, b) => a.score - b.score)
      .map(item => item.code);
    };

    if (this.availableSeatsCount && this.availableSeatsCount > 0) {
      if (this.type === 'flight') {
        const userClass = this.selectedSeatTypeOrClass?.toLowerCase() || 'economy';
        const isBusiness = userClass === 'business' || userClass === 'first_class';
        
        // Filter seat codes for the selected class
        const targetSeats = allSeatsCodes.filter(code => {
          const row = parseInt(code.match(/^\d+/)?.[0] || '0', 10);
          const isSeatBusiness = row >= 1 && row <= 3;
          return isBusiness ? isSeatBusiness : !isSeatBusiness;
        });

        const sortedTargetSeats = sortSeats(targetSeats);
        const totalClassSeats = targetSeats.length;
        const targetOccupiedCount = Math.max(0, totalClassSeats - this.availableSeatsCount);
        
        // Find existing occupied seats for this class
        const existingClassOccupied = this.occupiedSeats.filter(code => targetSeats.includes(code));
        
        // Add pseudo occupied seats until target count is met
        let addedCount = existingClassOccupied.length;
        for (const code of sortedTargetSeats) {
          if (addedCount >= targetOccupiedCount) break;
          if (!this.occupiedSeats.includes(code)) {
            pseudoOccupied.push(code);
            addedCount++;
          }
        }

        // For the mismatching class, mark all as occupied
        const mismatchSeats = allSeatsCodes.filter(code => !targetSeats.includes(code));
        pseudoOccupied.push(...mismatchSeats);
      } else {
        // For bus or train, all seats are of the same type in the selection grid
        const sortedSeats = sortSeats(allSeatsCodes);
        const targetOccupiedCount = Math.max(0, allSeatsCodes.length - this.availableSeatsCount);
        
        let addedCount = this.occupiedSeats.length;
        for (const code of sortedSeats) {
          if (addedCount >= targetOccupiedCount) break;
          if (!this.occupiedSeats.includes(code)) {
            pseudoOccupied.push(code);
            addedCount++;
          }
        }
      }
    } else {
      // Fallback to old behavior if availableSeatsCount is not provided or <= 0
      allSeatsCodes.forEach((code, idx) => {
        const val = Math.sin(seed + idx) * 10000;
        const isOccupied = (val - Math.floor(val)) < 0.35;
        if (isOccupied) {
          pseudoOccupied.push(code);
        }
      });
    }

    // Merge actual occupied seats with pseudo-occupied seats
    this.occupiedSeats = Array.from(new Set([...this.occupiedSeats, ...pseudoOccupied]));
  }

  generateSeats() {
    this.seats = [];
    this.selectedSeatsList = [];
    this.seatsSelected.emit([]);

    if (this.type === 'bus') {
      this.generateBusSeats();
    } else if (this.type === 'train') {
      this.generateTrainSeats();
    } else if (this.type === 'flight') {
      this.generateFlightSeats();
    }
  }

  generateBusSeats() {
    // Sleeper bus: 3 rows (Trái, Giữa, Phải). Lower Deck (A01-A18), Upper Deck (B01-B18)
    const cols = ['A', 'B', 'C']; // Left, Middle, Right row
    
    // Lower Deck A01 to A18
    for (let r = 1; r <= 6; r++) {
      cols.forEach((col, idx) => {
        const num = (r - 1) * 3 + (idx + 1);
        const code = `A${num.toString().padStart(2, '0')}`;
        this.seats.push({
          code,
          status: this.occupiedSeats.includes(code) ? 'occupied' : 'available',
          row: r,
          col,
          deck: 'lower'
        });
      });
    }

    // Upper Deck B01 to B18
    for (let r = 1; r <= 6; r++) {
      cols.forEach((col, idx) => {
        const num = (r - 1) * 3 + (idx + 1);
        const code = `B${num.toString().padStart(2, '0')}`;
        this.seats.push({
          code,
          status: this.occupiedSeats.includes(code) ? 'occupied' : 'available',
          row: r,
          col,
          deck: 'upper'
        });
      });
    }
  }

  generateTrainSeats() {
    // Train coach: 6 compartments (Cabins 1 to 6).
    // Let's assume standard soft sleeper: 4 beds per compartment.
    for (let cabin = 1; cabin <= 6; cabin++) {
      for (let bed = 1; bed <= 4; bed++) {
        const code = `C${cabin}-B${bed}`;
        this.seats.push({
          code,
          status: this.occupiedSeats.includes(code) ? 'occupied' : 'available',
          row: cabin,
          col: `B${bed}`,
          cabin
        });
      }
    }
  }

  generateFlightSeats() {
    // Business: rows 1-3, layout 2-2 (A C - D F)
    // Economy: rows 4-15, layout 3-3 (A B C - D E F)
    const economyCols = ['A', 'B', 'C', 'D', 'E', 'F'];
    const businessCols = ['A', 'C', 'D', 'F'];

    // If user selected Business Class, we only allow selecting business seats (and highlight them).
    // If user selected Economy Class, we only allow economy seats.
    const userClass = this.selectedSeatTypeOrClass?.toLowerCase() || 'economy';

    // Business seats
    for (let r = 1; r <= 3; r++) {
      businessCols.forEach(col => {
        const code = `${r}${col}`;
        const isOccupied = this.occupiedSeats.includes(code);
        const isClassMismatch = userClass !== 'business' && userClass !== 'first_class';
        this.seats.push({
          code,
          status: isOccupied ? 'occupied' : (isClassMismatch ? 'occupied' : 'available'),
          row: r,
          col
        });
      });
    }

    // Economy seats
    for (let r = 4; r <= 15; r++) {
      economyCols.forEach(col => {
        const code = `${r}${col}`;
        const isOccupied = this.occupiedSeats.includes(code);
        const isClassMismatch = userClass === 'business' || userClass === 'first_class';
        this.seats.push({
          code,
          status: isOccupied ? 'occupied' : (isClassMismatch ? 'occupied' : 'available'),
          row: r,
          col
        });
      });
    }
  }

  selectSeat(seat: Seat) {
    if (seat.status === 'occupied') return;

    if (seat.status === 'selected') {
      seat.status = 'available';
      this.selectedSeatsList = this.selectedSeatsList.filter(s => s !== seat.code);
    } else {
      if (this.selectedSeatsList.length >= this.maxSeats) {
        alert(`Bạn chỉ được chọn tối đa ${this.maxSeats} ghế!`);
        return;
      }
      seat.status = 'selected';
      this.selectedSeatsList.push(seat.code);
    }

    this.seatsSelected.emit(this.selectedSeatsList);
  }

  getSeatsByDeck(deck: 'lower' | 'upper'): Seat[] {
    return this.seats.filter(s => s.deck === deck);
  }

  getSeatsByCabin(cabin: number): Seat[] {
    return this.seats.filter(s => s.cabin === cabin);
  }

  getSeatsByRow(row: number): Seat[] {
    return this.seats.filter(s => s.row === row && s.cabin === undefined && s.deck === undefined);
  }

  getFlightRows(): number[] {
    return Array.from({ length: 15 }, (_, i) => i + 1);
  }
}
