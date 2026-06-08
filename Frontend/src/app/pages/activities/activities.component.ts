import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';

@Component({
  selector: 'app-activities',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './activities.component.html',
  styleUrl: './activities.component.scss'
})
export class ActivitiesComponent {
  constructor(private router: Router) {}

  openAIChat() {
    this.router.navigate(['/chat-room']);
  }
}
