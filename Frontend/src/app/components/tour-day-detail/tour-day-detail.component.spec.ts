import { ComponentFixture, TestBed } from '@angular/core/testing';
import { TourDayDetailComponent } from './tour-day-detail.component';

describe('TourDayDetailComponent', () => {
  let component: TourDayDetailComponent;
  let fixture: ComponentFixture<TourDayDetailComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TourDayDetailComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(TourDayDetailComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
