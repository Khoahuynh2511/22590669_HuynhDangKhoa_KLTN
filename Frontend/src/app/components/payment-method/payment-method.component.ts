import { NgFor, NgIf } from '@angular/common';
import { Component } from '@angular/core';

@Component({
  selector: 'app-payment-method',
  imports: [NgFor, NgIf],
  templateUrl: './payment-method.component.html',
  styleUrl: './payment-method.component.scss'
})
export class PaymentMethodComponent {
  paymentMethods: PaymentMethod[] = [
    { name: 'Tài khoản ảo BCA', description: 'BCA', isNew: true },
    { name: 'Tài khoản ảo Mandiri', description: 'mandiri', isNew: false },
    { name: 'Tài khoản ảo BRI', description: 'BRIVA', isNew: false },
    { name: 'Tài khoản ảo BNI', description: 'BNI', isNew: false },
    { name: 'Tài khoản ảo CIMB Niaga', description: 'CIMB NIAGA', isNew: true },
    { name: 'Tài khoản ảo khác', description: '', isNew: false },
  ];

  selectedMethod: string = '';

  selectMethod(method: string) {
    this.selectedMethod = method;
  }
}

interface PaymentMethod {
  name: string;
  description: string;
  isNew: boolean;
}
