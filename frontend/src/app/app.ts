import { Component, OnInit, inject } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { LoadingComponent } from './core/components/loading/loading.component';
import { BattlePollService } from './pvp/services/battle-poll.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, LoadingComponent],
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class App implements OnInit { 
  title = 'frontend';
  private pollService = inject(BattlePollService);

  ngOnInit(): void {
    // Start global invite polling if user is logged in
    if (typeof window !== 'undefined' && localStorage.getItem('token')) {
      this.pollService.pollForInvites().subscribe();
    }
  }
}