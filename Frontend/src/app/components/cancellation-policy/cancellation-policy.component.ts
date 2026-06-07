import { NgFor } from '@angular/common';
import { Component } from '@angular/core';

@Component({
  selector: 'app-cancellation-policy',
  imports: [NgFor],
  templateUrl: './cancellation-policy.component.html',
  styleUrl: './cancellation-policy.component.scss'
})
export class CancellationPolicyComponent {

  description: string = 'Chính sách hủy và đổi lịch cho tour du lịch của bạn.';
  policies: string[] = [
    'Hủy trước 7 ngày: Hoàn lại 80% giá trị tour',
    'Hủy trước 3-7 ngày: Hoàn lại 50% giá trị tour',
    'Hủy trước 1-3 ngày: Hoàn lại 30% giá trị tour',
    'Hủy trong vòng 24 giờ: Không hoàn tiền',
    'Đổi lịch: Có thể đổi lịch trước 7 ngày với phí 10% giá trị tour'
  ];
}
