import { ComponentFixture, TestBed } from '@angular/core/testing';
import { TourDayNavigatorComponent } from './tour-day-navigator.component';

describe('TourDayNavigatorComponent', () => {
  let component: TourDayNavigatorComponent;
  let fixture: ComponentFixture<TourDayNavigatorComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TourDayNavigatorComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(TourDayNavigatorComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
