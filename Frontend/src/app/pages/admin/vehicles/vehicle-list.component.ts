import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AdminBusService, BusItem, CompanyItem, StationItem as BusStationItem } from '../../../services/admin/admin-bus.service';
import { AdminFlightService, FlightItem, AirlineItem, AirportItem } from '../../../services/admin/admin-flight.service';
import { AdminTrainService, TrainItem, TrainStationItem, TrainTypeItem } from '../../../services/admin/admin-train.service';
import { AdminDialogService } from '../../../services/admin/admin-dialog.service';

type VehicleTab = 'flights' | 'buses' | 'trains';

@Component({
  selector: 'app-vehicle-list',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './vehicle-list.component.html',
  styleUrl: './vehicle-list.component.scss'
})
export class VehicleListComponent implements OnInit {
  activeTab: VehicleTab = 'flights';

  // ─── Shared State ───
  isLoading = true;
  searchTerm = '';
  statusFilter = '';

  // ─── Flights ───
  flights: FlightItem[] = [];
  filteredFlights: FlightItem[] = [];
  airlines: AirlineItem[] = [];
  airports: AirportItem[] = [];
  flightFormData: any = {};
  currentFlight: Partial<FlightItem> = {};

  // ─── Buses ───
  buses: BusItem[] = [];
  filteredBuses: BusItem[] = [];
  companies: CompanyItem[] = [];
  busStations: BusStationItem[] = [];
  busFormData: any = {};
  currentBus: Partial<BusItem> = {};

  // ─── Trains ───
  trains: TrainItem[] = [];
  filteredTrains: TrainItem[] = [];
  trainStations: TrainStationItem[] = [];
  trainTypes: TrainTypeItem[] = [];
  trainFormData: any = {};
  currentTrain: Partial<TrainItem> = {};

  // ─── Modal States ───
  showAddModal = false;
  showEditModal = false;
  showCsvModal = false;
  csvText = '';
  csvImportResult: any = null;

  // ─── Reference Data ───
  busTypeList = [
    { id: 'limousine_9', name: 'Limousine 9 chỗ' },
    { id: 'limousine_11', name: 'Limousine 11 chỗ' },
    { id: 'sleeper_40', name: 'Giường nằm 40 chỗ' },
    { id: 'sleeper_34', name: 'Cabin 34 chỗ' },
  ];

  flightStatusList = ['scheduled', 'boarding', 'departed', 'arrived', 'cancelled'];
  busStatusList = ['scheduled', 'boarding', 'departed', 'arrived', 'cancelled'];
  trainStatusList = ['scheduled', 'departed', 'arrived', 'cancelled'];

  constructor(
    private busService: AdminBusService,
    private flightService: AdminFlightService,
    private trainService: AdminTrainService,
    private dialogService: AdminDialogService
  ) {}

  async ngOnInit() {
    await this.loadAllData();
  }

  // ═══════════════════════════════════════════
  // DATA LOADING
  // ═══════════════════════════════════════════

  async loadAllData() {
    this.isLoading = true;
    await Promise.all([
      this.loadFlights(),
      this.loadBuses(),
      this.loadTrains()
    ]);
    this.loadReferenceData();
    this.isLoading = false;
  }

  async loadFlights() {
    try {
      const res = await this.flightService.getFlights().toPromise();
      if (res?.EC === 0) {
        this.flights = res.data.flights || [];
        this.applyFlightFilters();
      }
    } catch (e) { console.error('Error loading flights:', e); }
  }

  async loadBuses() {
    try {
      const res = await this.busService.getBuses().toPromise();
      if (res?.EC === 0) {
        this.buses = res.data.buses || [];
        this.applyBusFilters();
      }
    } catch (e) { console.error('Error loading buses:', e); }
  }

  async loadTrains() {
    try {
      const res = await this.trainService.getTrains().toPromise();
      if (res?.EC === 0) {
        this.trains = res.data.trains || [];
        this.applyTrainFilters();
      }
    } catch (e) { console.error('Error loading trains:', e); }
  }

  loadReferenceData() {
    this.flightService.getAirlines().subscribe({ next: (res) => { if (res.EC === 0) this.airlines = res.data || []; }, error: () => {} });
    this.flightService.getAirports().subscribe({ next: (res) => { if (res.EC === 0) this.airports = res.data || []; }, error: () => {} });
    this.busService.getCompanies().subscribe({ next: (res) => { if (res.EC === 0) this.companies = res.data || []; }, error: () => {} });
    this.busService.getStations().subscribe({ next: (res) => { if (res.EC === 0) this.busStations = res.data || []; }, error: () => {} });
    this.trainService.getStations().subscribe({ next: (res) => { if (res.EC === 0) this.trainStations = res.data || []; }, error: () => {} });
    this.trainService.getTypes().subscribe({ next: (res) => { if (res.EC === 0) this.trainTypes = res.data || []; }, error: () => {} });
  }

  // ═══════════════════════════════════════════
  // FILTERS
  // ═══════════════════════════════════════════

  applyFlightFilters() {
    this.filteredFlights = this.flights.filter(f => {
      const matchSearch = !this.searchTerm ||
        f.flight_number?.toLowerCase().includes(this.searchTerm.toLowerCase()) ||
        f.flight_id?.toLowerCase().includes(this.searchTerm.toLowerCase());
      const matchStatus = !this.statusFilter || f.status === this.statusFilter;
      return matchSearch && matchStatus;
    });
  }

  applyBusFilters() {
    this.filteredBuses = this.buses.filter(b => {
      const matchSearch = !this.searchTerm ||
        b.bus_number?.toLowerCase().includes(this.searchTerm.toLowerCase()) ||
        b.bus_id?.toLowerCase().includes(this.searchTerm.toLowerCase());
      const matchStatus = !this.statusFilter || b.status === this.statusFilter;
      return matchSearch && matchStatus;
    });
  }

  applyTrainFilters() {
    this.filteredTrains = this.trains.filter(t => {
      const matchSearch = !this.searchTerm ||
        t.train_number?.toLowerCase().includes(this.searchTerm.toLowerCase()) ||
        t.train_id?.toLowerCase().includes(this.searchTerm.toLowerCase());
      const matchStatus = !this.statusFilter || t.status === this.statusFilter;
      return matchSearch && matchStatus;
    });
  }

  onFilterChange() {
    if (this.activeTab === 'flights') this.applyFlightFilters();
    else if (this.activeTab === 'buses') this.applyBusFilters();
    else this.applyTrainFilters();
  }

  onTabChange(tab: VehicleTab) {
    this.activeTab = tab;
    this.searchTerm = '';
    this.statusFilter = '';
    this.onFilterChange();
  }

  // ═══════════════════════════════════════════
  // STATS
  // ═══════════════════════════════════════════

  get totalItems(): number {
    if (this.activeTab === 'flights') return this.flights.length;
    if (this.activeTab === 'buses') return this.buses.length;
    return this.trains.length;
  }

  get scheduledCount(): number {
    if (this.activeTab === 'flights') return this.flights.filter(f => f.status === 'scheduled').length;
    if (this.activeTab === 'buses') return this.buses.filter(b => b.status === 'scheduled').length;
    return this.trains.filter(t => t.status === 'scheduled').length;
  }

  get activeCount(): number {
    if (this.activeTab === 'flights') return this.flights.filter(f => ['boarding', 'departed'].includes(f.status)).length;
    if (this.activeTab === 'buses') return this.buses.filter(b => ['boarding', 'departed'].includes(b.status)).length;
    return this.trains.filter(t => t.status === 'departed').length;
  }

  get cancelledCount(): number {
    if (this.activeTab === 'flights') return this.flights.filter(f => f.status === 'cancelled').length;
    if (this.activeTab === 'buses') return this.buses.filter(b => b.status === 'cancelled').length;
    return this.trains.filter(t => t.status === 'cancelled').length;
  }

  get filteredCount(): number {
    if (this.activeTab === 'flights') return this.filteredFlights.length;
    if (this.activeTab === 'buses') return this.filteredBuses.length;
    return this.filteredTrains.length;
  }

  get statusList(): string[] {
    if (this.activeTab === 'flights') return this.flightStatusList;
    if (this.activeTab === 'buses') return this.busStatusList;
    return this.trainStatusList;
  }

  // ═══════════════════════════════════════════
  // FLIGHT CRUD
  // ═══════════════════════════════════════════

  openAddFlightModal() {
    this.flightFormData = {
      flight_number: '', airline_id: '', departure_airport: '', arrival_airport: '',
      departure_time: '', arrival_time: '', duration_minutes: 120,
      aircraft: 'Airbus A321', economy_price: 1500000, business_price: 3500000,
      first_class_price: 0, economy_seats: 150, business_seats: 20,
      first_class_seats: 0, status: 'scheduled'
    };
    this.showAddModal = true;
  }

  openEditFlightModal(flight: FlightItem) {
    this.currentFlight = { ...flight };
    this.flightFormData = {
      flight_number: flight.flight_number, airline_id: flight.airline_id,
      departure_airport: flight.departure_airport, arrival_airport: flight.arrival_airport,
      departure_time: flight.departure_time?.slice(0, 16), arrival_time: flight.arrival_time?.slice(0, 16),
      duration_minutes: flight.duration_minutes, aircraft: flight.aircraft,
      economy_price: flight.economy_price, business_price: flight.business_price,
      first_class_price: flight.first_class_price, economy_seats: flight.economy_seats,
      business_seats: flight.business_seats, first_class_seats: flight.first_class_seats,
      status: flight.status
    };
    this.showEditModal = true;
  }

  async saveFlight() {
    try {
      const res = await this.flightService.createFlight(this.flightFormData).toPromise();
      if (res?.EC === 0) {
        await this.dialogService.alert('Thành công', 'Tạo chuyến bay thành công!');
        this.closeModal();
        await this.loadFlights();
      } else {
        await this.dialogService.alert('Lỗi', res?.EM || 'Tạo chuyến bay thất bại');
      }
    } catch (e: any) {
      await this.dialogService.alert('Lỗi', e?.error?.detail || 'Lỗi kết nối server');
    }
  }

  async updateFlight() {
    try {
      const res = await this.flightService.updateFlight(this.currentFlight.flight_id!, this.flightFormData).toPromise();
      if (res?.EC === 0) {
        await this.dialogService.alert('Thành công', 'Cập nhật thành công!');
        this.closeModal();
        await this.loadFlights();
      } else {
        await this.dialogService.alert('Lỗi', res?.EM || 'Cập nhật thất bại');
      }
    } catch (e: any) {
      await this.dialogService.alert('Lỗi', e?.error?.detail || 'Lỗi kết nối server');
    }
  }

  async deleteFlight(flight: FlightItem) {
    const confirmed = await this.dialogService.confirm({
      title: 'Xóa chuyến bay', message: `Bạn có chắc chắn muốn xóa chuyến bay "${flight.flight_number}"?`,
      confirmText: 'Xóa', cancelText: 'Hủy', type: 'warning'
    });
    if (confirmed) {
      try {
        const res = await this.flightService.deleteFlight(flight.flight_id).toPromise();
        if (res?.EC === 0) {
          await this.dialogService.alert('Thành công', 'Xóa chuyến bay thành công!');
          await this.loadFlights();
        }
      } catch (e: any) {
        await this.dialogService.alert('Lỗi', e?.error?.detail || 'Xóa thất bại');
      }
    }
  }

  // ═══════════════════════════════════════════
  // BUS CRUD
  // ═══════════════════════════════════════════

  openAddBusModal() {
    this.busFormData = {
      bus_number: '', company_id: '', bus_type_id: '',
      departure_station: '', arrival_station: '',
      departure_time: '', arrival_time: '', duration_hours: 8,
      total_seats: 40, available_seats: 40, base_price: 300000, status: 'scheduled'
    };
    this.showAddModal = true;
  }

  openEditBusModal(bus: BusItem) {
    this.currentBus = { ...bus };
    this.busFormData = {
      bus_number: bus.bus_number, company_id: bus.company_id, bus_type_id: bus.bus_type_id,
      departure_station: bus.departure_station, arrival_station: bus.arrival_station,
      departure_time: bus.departure_time?.slice(0, 16), arrival_time: bus.arrival_time?.slice(0, 16),
      duration_hours: bus.duration_hours, total_seats: bus.total_seats,
      available_seats: bus.available_seats, base_price: bus.base_price, status: bus.status
    };
    this.showEditModal = true;
  }

  async saveBus() {
    try {
      const res = await this.busService.createBus(this.busFormData).toPromise();
      if (res?.EC === 0) {
        await this.dialogService.alert('Thành công', 'Tạo chuyến xe thành công!');
        this.closeModal();
        await this.loadBuses();
      } else {
        await this.dialogService.alert('Lỗi', res?.EM || 'Tạo chuyến xe thất bại');
      }
    } catch (e: any) {
      await this.dialogService.alert('Lỗi', e?.error?.detail || 'Lỗi kết nối server');
    }
  }

  async updateBus() {
    try {
      const res = await this.busService.updateBus(this.currentBus.bus_id!, this.busFormData).toPromise();
      if (res?.EC === 0) {
        await this.dialogService.alert('Thành công', 'Cập nhật thành công!');
        this.closeModal();
        await this.loadBuses();
      } else {
        await this.dialogService.alert('Lỗi', res?.EM || 'Cập nhật thất bại');
      }
    } catch (e: any) {
      await this.dialogService.alert('Lỗi', e?.error?.detail || 'Lỗi kết nối server');
    }
  }

  async deleteBus(bus: BusItem) {
    const confirmed = await this.dialogService.confirm({
      title: 'Xóa chuyến xe', message: `Bạn có chắc chắn muốn xóa chuyến xe "${bus.bus_number}"?`,
      confirmText: 'Xóa', cancelText: 'Hủy', type: 'warning'
    });
    if (confirmed) {
      try {
        const res = await this.busService.deleteBus(bus.bus_id).toPromise();
        if (res?.EC === 0) {
          await this.dialogService.alert('Thành công', 'Xóa chuyến xe thành công!');
          await this.loadBuses();
        }
      } catch (e: any) {
        await this.dialogService.alert('Lỗi', e?.error?.detail || 'Xóa thất bại');
      }
    }
  }

  // ═══════════════════════════════════════════
  // TRAIN CRUD
  // ═══════════════════════════════════════════

  openAddTrainModal() {
    this.trainFormData = {
      train_number: '', train_type_id: '', departure_station: '', arrival_station: '',
      departure_time: '', arrival_time: '', duration_hours: 8, status: 'scheduled'
    };
    this.showAddModal = true;
  }

  openEditTrainModal(train: TrainItem) {
    this.currentTrain = { ...train };
    this.trainFormData = {
      train_number: train.train_number, train_type_id: train.train_type_id,
      departure_station: train.departure_station, arrival_station: train.arrival_station,
      departure_time: train.departure_time?.slice(0, 16), arrival_time: train.arrival_time?.slice(0, 16),
      duration_hours: train.duration_hours, status: train.status
    };
    this.showEditModal = true;
  }

  async saveTrain() {
    try {
      const res = await this.trainService.createTrain(this.trainFormData).toPromise();
      if (res?.EC === 0) {
        await this.dialogService.alert('Thành công', 'Tạo chuyến tàu thành công!');
        this.closeModal();
        await this.loadTrains();
      } else {
        await this.dialogService.alert('Lỗi', res?.EM || 'Tạo chuyến tàu thất bại');
      }
    } catch (e: any) {
      await this.dialogService.alert('Lỗi', e?.error?.detail || 'Lỗi kết nối server');
    }
  }

  async updateTrain() {
    try {
      const res = await this.trainService.updateTrain(this.currentTrain.train_id!, this.trainFormData).toPromise();
      if (res?.EC === 0) {
        await this.dialogService.alert('Thành công', 'Cập nhật thành công!');
        this.closeModal();
        await this.loadTrains();
      } else {
        await this.dialogService.alert('Lỗi', res?.EM || 'Cập nhật thất bại');
      }
    } catch (e: any) {
      await this.dialogService.alert('Lỗi', e?.error?.detail || 'Lỗi kết nối server');
    }
  }

  async deleteTrain(train: TrainItem) {
    const confirmed = await this.dialogService.confirm({
      title: 'Xóa chuyến tàu', message: `Bạn có chắc chắn muốn xóa chuyến tàu "${train.train_number}"?`,
      confirmText: 'Xóa', cancelText: 'Hủy', type: 'warning'
    });
    if (confirmed) {
      try {
        const res = await this.trainService.deleteTrain(train.train_id).toPromise();
        if (res?.EC === 0) {
          await this.dialogService.alert('Thành công', 'Xóa chuyến tàu thành công!');
          await this.loadTrains();
        }
      } catch (e: any) {
        await this.dialogService.alert('Lỗi', e?.error?.detail || 'Xóa thất bại');
      }
    }
  }

  // ═══════════════════════════════════════════
  // CSV IMPORT
  // ═══════════════════════════════════════════

  getCsvTemplate(): string {
    if (this.activeTab === 'flights') {
      return 'flight_number,airline_id,departure_airport,arrival_airport,departure_time,arrival_time,duration_minutes,aircraft,economy_price,business_price,first_class_price,economy_seats,business_seats,first_class_seats,status';
    } else if (this.activeTab === 'buses') {
      return 'bus_number,company_id,bus_type_id,departure_station,arrival_station,departure_time,arrival_time,duration_hours,total_seats,available_seats,base_price,status';
    } else {
      return 'train_number,train_type_id,departure_station,arrival_station,departure_time,arrival_time,duration_hours,status';
    }
  }

  downloadCsvTemplate() {
    const template = this.getCsvTemplate();
    const blob = new Blob([template + '\n'], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `template_${this.activeTab}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  openCsvModal() {
    this.csvText = '';
    this.csvImportResult = null;
    this.showCsvModal = true;
  }

  async importCsv() {
    if (!this.csvText.trim()) {
      await this.dialogService.alert('Lỗi', 'Vui lòng nhập dữ liệu CSV');
      return;
    }
    try {
      let res: any;
      if (this.activeTab === 'flights') {
        res = await this.flightService.createFlightsFromCSV(this.csvText).toPromise();
      } else if (this.activeTab === 'buses') {
        res = await this.busService.createBusesFromCSV(this.csvText).toPromise();
      } else {
        res = await this.trainService.createTrainsFromCSV(this.csvText).toPromise();
      }

      if (res?.EC === 0) {
        this.csvImportResult = res.data;
        if (this.activeTab === 'flights') await this.loadFlights();
        else if (this.activeTab === 'buses') await this.loadBuses();
        else await this.loadTrains();
      } else {
        await this.dialogService.alert('Lỗi', res?.EM || 'Import thất bại');
      }
    } catch (e: any) {
      await this.dialogService.alert('Lỗi', e?.error?.detail || 'Lỗi kết nối server');
    }
  }

  onCsvFileSelected(event: any) {
    const file = event.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (e) => {
        this.csvText = e.target?.result as string || '';
      };
      reader.readAsText(file);
    }
  }

  // ═══════════════════════════════════════════
  // HELPERS
  // ═══════════════════════════════════════════

  getAirlineName(id: string): string {
    return this.airlines.find(a => a.airline_id === id)?.name || id;
  }

  getAirportName(id: string): string {
    return this.airports.find(a => a.airport_id === id)?.name || id;
  }

  getAirportCity(id: string): string {
    return this.airports.find(a => a.airport_id === id)?.city || id;
  }

  getCompanyName(id: string): string {
    return this.companies.find(c => c.company_id === id)?.name || id;
  }

  getBusStationName(id: string): string {
    return this.busStations.find(s => s.station_id === id)?.name || id;
  }

  getBusTypeName(id: string): string {
    return this.busTypeList.find(t => t.id === id)?.name || id;
  }

  getTrainStationName(id: string): string {
    return this.trainStations.find(s => s.station_id === id)?.name || id;
  }

  getTrainTypeName(id: string): string {
    return this.trainTypes.find(t => t.type_id === id)?.name || id;
  }

  getStatusClass(status: string): string {
    const map: { [key: string]: string } = {
      'scheduled': 'bg-blue-100 text-blue-700',
      'boarding': 'bg-yellow-100 text-yellow-700',
      'departed': 'bg-purple-100 text-purple-700',
      'arrived': 'bg-green-100 text-green-700',
      'cancelled': 'bg-red-100 text-red-700'
    };
    return map[status] || 'bg-gray-100 text-gray-700';
  }

  getStatusLabel(status: string): string {
    const map: { [key: string]: string } = {
      'scheduled': 'Đã lên lịch',
      'boarding': 'Đang lên',
      'departed': 'Đã xuất phát',
      'arrived': 'Đã đến',
      'cancelled': 'Đã hủy'
    };
    return map[status] || status;
  }

  formatPrice(price: number): string {
    return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(price);
  }

  formatDateTime(dt: string | undefined): string {
    if (!dt) return '';
    return new Date(dt).toLocaleString('vi-VN');
  }

  formatDuration(minutes: number): string {
    const h = Math.floor(minutes / 60);
    const m = minutes % 60;
    return m > 0 ? `${h}h ${m}m` : `${h}h`;
  }

  closeModal() {
    this.showAddModal = false;
    this.showEditModal = false;
    this.showCsvModal = false;
    this.csvImportResult = null;
  }
}
