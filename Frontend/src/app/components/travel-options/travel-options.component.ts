import { NgFor } from '@angular/common';
import { Component } from '@angular/core';

interface TravelOption {
  title: string;
  imageUrl: string;
}

@Component({
  selector: 'app-travel-options',
  imports: [NgFor],
  templateUrl: './travel-options.component.html',
  styleUrl: './travel-options.component.scss'
})
export class TravelOptionsComponent {
  travelOptions: TravelOption[] = [
    {
      title: 'Du thuyền',
      imageUrl: 'https://via.placeholder.com/300x200?text=Kapal+Pesiar',
    },
    {
      title: 'Hoạt động vui chơi',
      imageUrl: 'https://via.placeholder.com/300x200?text=Fun+Activities',
    },
    {
      title: 'Bảo hiểm du lịch',
      imageUrl: 'https://via.placeholder.com/300x200?text=Travel+Insurance',
    },
    {
      title: 'Thanh toán sau',
      imageUrl: 'https://via.placeholder.com/300x200?text=TPayLater',
    },
  ];
}
