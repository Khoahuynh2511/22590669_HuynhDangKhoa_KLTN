import { Component, ViewEncapsulation } from '@angular/core';
import { AccordionModule } from 'primeng/accordion';
import { CheckboxModule } from 'primeng/checkbox';


@Component({
  selector: 'app-accordion-filter',
  imports: [
    AccordionModule, CheckboxModule

  ],
  templateUrl: './accordion-filter.component.html',
  styleUrl: './accordion-filter.component.scss',
  encapsulation: ViewEncapsulation.None
})
export class AccordionFilterComponent {
  checkboxs: any[] = [
    { label: 'Ấn tượng', value: '' },
    { label: 'Khách sạn', value: '' },
    { label: 'Biệt thự', value: '' },
    { label: 'Khu nghỉ dưỡng', value: '' },
  ]
}
