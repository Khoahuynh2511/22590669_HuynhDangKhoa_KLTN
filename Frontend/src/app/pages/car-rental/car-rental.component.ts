import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';

@Component({
  selector: 'app-car-rental',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './car-rental.component.html',
  styleUrl: './car-rental.component.scss'
})
export class CarRentalComponent {
  constructor(private router: Router) {}

  openAIChat() {
    this.router.navigate(['/chat-room']);
  }
}
