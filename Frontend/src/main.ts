import { bootstrapApplication } from '@angular/platform-browser';
import { appConfig } from './app/app.config';
import { AppComponent } from './app/app.component';
import { environment } from './environments/environment';

// Disable console logs in production
if (environment.production) {
  console.log = () => { };
  console.warn = () => { };
  console.info = () => { };
  console.debug = () => { };
  // Keep console.error for critical errors
}

bootstrapApplication(AppComponent, appConfig)
  .catch((err) => console.error(err));
