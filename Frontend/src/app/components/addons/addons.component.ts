import { NgFor } from '@angular/common';
import { Component } from '@angular/core';

@Component({
  selector: 'app-addons',
  imports: [NgFor],
  templateUrl: './addons.component.html',
  styleUrl: './addons.component.scss'
})
export class AddonsComponent {

  addons: Addon[] = [
    {
      name: 'Bảo hiểm khách sạn',
      description: 'Bảo vệ kế hoạch lưu trú của bạn khỏi hủy đặt phòng và các sự kiện không lường trước khác.',
      price: 13000,
      details: 'Lên đến 500.000đ mỗi phòng mỗi đêm cho đơn đặt phòng khách sạn bị hủy\nLên đến 2.000.000đ cho việc hủy khách sạn vì lý do cụ thể\nLên đến 2.500.000đ cho mất mát hoặc hư hỏng hành lý và tài sản cá nhân\nLên đến 30.000.000đ cho bảo vệ tai nạn\nLên đến 3.000.000đ cho chi phí y tế do tai nạn',
    },
    {
      name: 'Bảo vệ nhận phòng',
      description: 'Nhận bồi thường vì không thể nhận phòng khách sạn do sự kiện không lường trước (ví dụ: hết phòng)',
      price: 10000,
      details: '',
    },
    {
      name: 'Hoàn tiền sau khi nhận phòng',
      description: 'Không hài lòng với khách sạn của bạn sau khi nhận phòng? Dù lý do gì, chỉ cần đặt khách sạn khác!',
      price: 77000,
      details: 'Chúng tôi sẽ hoàn lại 50% (lên đến 500.000đ) từ khách sạn bạn hủy sau khi bạn đặt khách sạn mới.',
    },
  ];

}

interface Addon {
  name: string;
  description: string;
  price: number;
  details: string;
}
