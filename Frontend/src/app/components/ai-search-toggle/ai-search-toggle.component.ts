import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { AuthStateService } from '../../services/auth-state.service';

@Component({
  selector: 'app-ai-search-toggle',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './ai-search-toggle.component.html',
  styleUrl: './ai-search-toggle.component.scss'
})
export class AiSearchToggleComponent {
  @Input() isAIMode: boolean = false;
  @Output() modeChange = new EventEmitter<boolean>();

  constructor(
    private authStateService: AuthStateService,
    private router: Router
  ) {}

  get isAuthenticated(): boolean {
    return this.authStateService.getIsAuthenticated();
  }

  onToggleClick(): void {
    if (!this.isAuthenticated) {
      // Redirect to login if not authenticated
      this.router.navigate(['/login']);
      return;
    }

    // Toggle mode
    this.modeChange.emit(!this.isAIMode);
  }
}
