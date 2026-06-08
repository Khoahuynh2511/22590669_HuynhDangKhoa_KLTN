import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';

@Component({
  selector: 'app-airport-transfer',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './airport-transfer.component.html',
  styleUrl: './airport-transfer.component.scss'
})
export class AirportTransferComponent {
  constructor(private router: Router) {}

  openAIChat() {
    this.router.navigate(['/chat-room']);
  }
}
