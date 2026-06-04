/* pvp.routes.ts */
import { Routes } from '@angular/router';

export const PVP_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () => import('./components/pvp-lobby/pvp-lobby.component').then(m => m.PvpLobbyComponent)
  },
  {
    path: 'battle/:id',
    loadComponent: () => import('./components/pvp-battle/pvp-battle.component').then(m => m.PvpBattleComponent)
  },
  {
    path: 'result/:id',
    loadComponent: () => import('./components/pvp-result/pvp-result.component').then(m => m.PvpResultComponent)
  },
  {
    path: 'history',
    loadComponent: () => import('./components/pvp-history/pvp-history.component').then(m => m.PvpHistoryComponent)
  }
];
