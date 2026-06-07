<p align="center">
  <img src="https://img.shields.io/badge/Angular-19.0-DD0031?style=for-the-badge&logo=angular&logoColor=white" alt="Angular">
  <img src="https://img.shields.io/badge/TypeScript-5.6-3178C6?style=for-the-badge&logo=typescript&logoColor=white" alt="TypeScript">
  <img src="https://img.shields.io/badge/PrimeNG-19.0-007ACC?style=for-the-badge&logo=primeng&logoColor=white" alt="PrimeNG">
  <img src="https://img.shields.io/badge/TailwindCSS-3.4-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=white" alt="TailwindCSS">
  <img src="https://img.shields.io/badge/RxJS-7.8-B7178C?style=for-the-badge&logo=reactivex&logoColor=white" alt="RxJS">
</p>

<h1 align="center">🌍 AI Tour Booking System - Frontend</h1>

<p align="center">
  <strong>Modern Angular SPA với AI Chatbot, Real-time Notifications và Responsive Design</strong>
</p>

<p align="center">
  <a href="#-tính-năng">Tính năng</a> •
  <a href="#-system-architecture">Architecture</a> •
  <a href="#-tech-stack">Tech Stack</a> •
  <a href="#-cài-đặt">Cài đặt</a> •
  <a href="#-project-structure">Structure</a>
</p>

---

## ✨ Tính năng

### 🔐 Authentication & User Management
- Đăng nhập/Đăng ký với Email & Password
- Google OAuth 2.0 Integration
- JWT Token Management với Auto-refresh
- Role-based Access Control (Admin/User)
- User Profile Management

### 🎫 Tour & Booking Features
- **Tour Search**: Tìm kiếm với filters (destination, price, date)
- **AI-Powered Search**: Semantic search với natural language
- **Tour Details**: Gallery, itinerary, reviews, ratings
- **Booking Flow**: Multi-step booking với OTP verification
- **My Bookings**: Quản lý booking history với status tracking

### 💳 Payment Integration
- VNPay Payment Gateway
- Payment History & Receipts
- Promotion/Voucher Application
- Real-time Payment Status Updates

### 🤖 AI Features
- **AI Chatbot**: Streaming responses với SSE
- **Admin AI Assistant**: AI hỗ trợ quản trị viên
- **Smart Recommendations**: AI-powered tour suggestions
- **Natural Language Search**: Tìm kiếm bằng ngôn ngữ tự nhiên

### 👨‍💼 Admin Dashboard
- Tour Package Management (CRUD)
- Booking Management
- User Management
- Payment Reports & Analytics
- Promotion Management
- Featured Tours Configuration

### 🔔 Real-time Features
- Push Notifications
- Real-time Booking Updates
- Live Chat với AI
- Payment Status Notifications

### 📱 Responsive Design
- Mobile-first approach
- Tablet & Desktop optimized
- Touch-friendly UI
- Progressive Web App ready

---

## 🏗 System Architecture

### High-Level Architecture

```mermaid
graph TB
    subgraph "User Interface Layer"
        BROWSER[Web Browser]
        PWA[Progressive Web App]
    end
    
    subgraph "Angular Application"
        ROUTER[Angular Router]
        GUARDS[Route Guards]
        
        subgraph "Feature Modules"
            AUTH[Auth Module]
            TOURS[Tours Module]
            BOOKING[Booking Module]
            PAYMENT[Payment Module]
            ADMIN[Admin Module]
            PROFILE[Profile Module]
        end
        
        subgraph "Shared Layer"
            COMPONENTS[Shared Components]
            SERVICES[Services Layer]
            MODELS[Models & Interfaces]
            DIRECTIVES[Custom Directives]
        end
    end
    
    subgraph "State Management"
        RXJS[RxJS Observables]
        BEHAVIOR[BehaviorSubjects]
        LOCAL[LocalStorage]
    end
    
    subgraph "Backend Integration"
        HTTP[HTTP Client]
        SSE[Server-Sent Events]
        INTERCEPTOR[HTTP Interceptors]
    end
    
    subgraph "External Services"
        API[FastAPI Backend]
        GOOGLE[Google OAuth]
        VNPAY[VNPay Gateway]
    end
    
    BROWSER --> ROUTER
    PWA --> ROUTER
    ROUTER --> GUARDS
    GUARDS --> AUTH
    GUARDS --> TOURS
    GUARDS --> BOOKING
    GUARDS --> PAYMENT
    GUARDS --> ADMIN
    GUARDS --> PROFILE
    
    AUTH --> SERVICES
    TOURS --> SERVICES
    BOOKING --> SERVICES
    PAYMENT --> SERVICES
    ADMIN --> SERVICES
    PROFILE --> SERVICES
    
    SERVICES --> RXJS
    SERVICES --> BEHAVIOR
    SERVICES --> LOCAL
    
    SERVICES --> HTTP
    SERVICES --> SSE
    HTTP --> INTERCEPTOR
    
    INTERCEPTOR --> API
    AUTH --> GOOGLE
    PAYMENT --> VNPAY
    
    style ROUTER fill:#dd0031
    style GUARDS fill:#dd0031
    style SERVICES fill:#3178c6
```

### Component Architecture

```mermaid
graph LR
    subgraph "Pages (Smart Components)"
        HOME[HomePage]
        TOURS_PAGE[ToursPage]
        BOOKING_PAGE[BookingPage]
        ADMIN_PAGE[AdminPage]
    end
    
    subgraph "Components (Presentational)"
        HERO[HeroComponent]
        TOUR_CARD[TourCardComponent]
        SEARCH_BAR[SearchBarComponent]
        AI_CHAT[AIChatbotComponent]
        NOTIFICATION[NotificationBellComponent]
    end
    
    subgraph "Services"
        TOUR_SVC[TourService]
        BOOKING_SVC[BookingService]
        AUTH_SVC[AuthService]
        PAYMENT_SVC[PaymentService]
        CHATBOT_SVC[ChatbotService]
    end
    
    subgraph "Backend API"
        API[FastAPI Server]
    end
    
    HOME --> HERO
    HOME --> TOUR_CARD
    HOME --> SEARCH_BAR
    
    TOURS_PAGE --> TOUR_CARD
    TOURS_PAGE --> AI_CHAT
    
    BOOKING_PAGE --> NOTIFICATION
    
    HERO --> TOUR_SVC
    TOUR_CARD --> TOUR_SVC
    SEARCH_BAR --> TOUR_SVC
    AI_CHAT --> CHATBOT_SVC
    
    TOUR_SVC --> API
    BOOKING_SVC --> API
    AUTH_SVC --> API
    PAYMENT_SVC --> API
    CHATBOT_SVC --> API
    
    style HOME fill:#dd0031
    style TOURS_PAGE fill:#dd0031
    style TOUR_SVC fill:#3178c6
    style CHATBOT_SVC fill:#3178c6
```

### Authentication Flow

```mermaid
sequenceDiagram
    participant U as User
    participant C as LoginComponent
    participant AS as AuthService
    participant I as HTTP Interceptor
    participant API as Backend API
    participant LS as LocalStorage
    
    U->>C: Enter credentials
    C->>AS: login(email, password)
    AS->>API: POST /auth/login
    API-->>AS: {access_token, user}
    AS->>LS: Store token & user
    AS-->>C: Login success
    C->>U: Redirect to home
    
    Note over I: Subsequent requests
    C->>AS: getTours()
    AS->>I: HTTP Request
    I->>LS: Get token
    LS-->>I: access_token
    I->>API: Request + Bearer token
    API-->>I: Response
    I-->>AS: Data
    AS-->>C: Tours data
```

### State Management Pattern

```mermaid
graph TB
    subgraph "Component Layer"
        COMP[Component]
    end
    
    subgraph "Service Layer"
        SVC[Service]
        SUBJECT[BehaviorSubject]
        OBS[Observable]
    end
    
    subgraph "Data Layer"
        API[HTTP Client]
        CACHE[LocalStorage]
    end
    
    COMP -->|Subscribe| OBS
    COMP -->|Call Method| SVC
    
    SVC -->|Update| SUBJECT
    SUBJECT -->|Emit| OBS
    
    SVC -->|Fetch| API
    SVC -->|Read/Write| CACHE
    
    API -->|Response| SVC
    CACHE -->|Data| SVC
    
    style SUBJECT fill:#b7178c
    style OBS fill:#b7178c
```

### Routing Architecture

```
/
├── auth/
│   ├── login
│   ├── register
│   └── google-callback
├── home
├── tours/
│   ├── :id (tour details)
│   └── search
├── booking/
│   ├── :tourId (booking form)
│   └── confirmation
├── my-bookings
├── my-payments
├── profile
├── promotions
├── travel-news
└── admin/ (Protected)
    ├── dashboard
    ├── tours
    ├── bookings
    ├── users
    ├── payments
    └── promotions
```

---

## 🛠 Tech Stack

| Category | Technologies |
|----------|-------------|
| **Framework** | Angular 19.0 |
| **Language** | TypeScript 5.6 |
| **UI Library** | PrimeNG 19.0 |
| **Styling** | TailwindCSS 3.4, SCSS |
| **State Management** | RxJS 7.8, BehaviorSubjects |
| **HTTP Client** | Angular HttpClient |
| **Routing** | Angular Router with Guards |
| **Forms** | Reactive Forms |
| **Animations** | Angular Animations |
| **3D Graphics** | Three.js 0.181 |
| **Carousel** | ngx-owl-carousel-o |
| **Testing** | Jasmine, Karma |
| **Build Tool** | Angular CLI 19.0 |
| **Package Manager** | npm |

---

## 📁 Project Structure

```
SE347_IE104_Frontend/
├── src/
│   ├── app/
│   │   ├── pages/                  # Smart Components (Container)
│   │   │   ├── auth/
│   │   │   │   ├── login/
│   │   │   │   ├── register/
│   │   │   │   └── google-callback/
│   │   │   ├── home/
│   │   │   ├── tours/
│   │   │   ├── booking-pages/
│   │   │   ├── my-bookings/
│   │   │   ├── my-payments/
│   │   │   ├── payment/
│   │   │   ├── profile/
│   │   │   ├── promotions/
│   │   │   ├── reviews/
│   │   │   ├── travel-news/
│   │   │   └── admin/              # Admin Dashboard
│   │   │       ├── dashboard/
│   │   │       ├── tours/
│   │   │       ├── bookings/
│   │   │       ├── users/
│   │   │       ├── payments/
│   │   │       └── promotions/
│   │   │
│   │   ├── components/             # Presentational Components
│   │   │   ├── hero/
│   │   │   ├── search-bar/
│   │   │   ├── tour-card/
│   │   │   ├── booking-card/
│   │   │   ├── ai-chatbot/
│   │   │   ├── admin-chatbot/
│   │   │   ├── notification-bell/
│   │   │   ├── payment-method/
│   │   │   ├── promotion-banner/
│   │   │   ├── travel-news-card/
│   │   │   └── ...
│   │   │
│   │   ├── services/               # Business Logic
│   │   │   ├── auth.service.ts
│   │   │   ├── auth-state.service.ts
│   │   │   ├── tour.service.ts
│   │   │   ├── booking.service.ts
│   │   │   ├── payment.service.ts
│   │   │   ├── chatbot.service.ts
│   │   │   ├── notification.service.ts
│   │   │   ├── profile.service.ts
│   │   │   ├── review.service.ts
│   │   │   ├── promotion.service.ts
│   │   │   ├── config.service.ts
│   │   │   └── admin/
│   │   │       ├── admin-tour.service.ts
│   │   │       ├── admin-booking.service.ts
│   │   │       └── admin-user.service.ts
│   │   │
│   │   ├── guards/                 # Route Guards
│   │   │   ├── auth.guard.ts
│   │   │   └── admin.guard.ts
│   │   │
│   │   ├── layouts/                # Layout Components
│   │   │   ├── header/
│   │   │   ├── footer/
│   │   │   └── admin-layout/
│   │   │
│   │   ├── shared/                 # Shared Resources
│   │   │   ├── models/
│   │   │   │   ├── tour.model.ts
│   │   │   │   ├── booking.model.ts
│   │   │   │   ├── user.model.ts
│   │   │   │   └── payment.model.ts
│   │   │   ├── interceptors/
│   │   │   │   └── auth.interceptor.ts
│   │   │   └── utils/
│   │   │
│   │   ├── directives/             # Custom Directives
│   │   │
│   │   ├── app.component.ts        # Root Component
│   │   ├── app.config.ts           # App Configuration
│   │   └── app.routes.ts           # Route Configuration
│   │
│   ├── assets/                     # Static Assets
│   │   ├── images/
│   │   ├── icons/
│   │   └── fonts/
│   │
│   ├── styles/                     # Global Styles
│   │   └── styles.scss
│   │
│   └── environments/               # Environment Config
│       ├── environment.ts
│       └── environment.prod.ts
│
├── public/                         # Public Assets
├── angular.json                    # Angular CLI Config
├── package.json                    # Dependencies
├── tailwind.config.js              # TailwindCSS Config
├── tsconfig.json                   # TypeScript Config
├── Dockerfile                      # Docker Config
└── nginx.conf                      # Nginx Config
```

---

## 🚀 Cài đặt

### Prerequisites

- Node.js 18+ và npm
- Angular CLI 19.0+

### 1. Install Angular CLI

```bash
npm install -g @angular/cli@19
```

### 2. Install Dependencies

```bash
npm install
```

### 3. Configure Environment

Tạo file `src/environments/environment.ts`:

```typescript
export const environment = {
  production: false,
  apiUrl: 'http://localhost:8000/api/v1',
  googleClientId: 'your_google_client_id'
};
```

### 4. Run Development Server

```bash
ng serve
```

Ứng dụng sẽ chạy tại: `http://localhost:4200`

---

## ▶️ Available Scripts

### Development

```bash
# Start dev server
ng serve

# Start with specific port
ng serve --port 4300

# Open browser automatically
ng serve --open
```

### Build

```bash
# Development build
ng build

# Production build
ng build --configuration production

# Build with stats
ng build --stats-json
```

### Testing

```bash
# Run unit tests
ng test

# Run tests with coverage
ng test --code-coverage

# Run tests in headless mode
ng test --browsers=ChromeHeadless --watch=false
```

### Code Quality

```bash
# Lint code
ng lint

# Format code
npm run format
```

---

## 🐳 Docker Deployment

### Build Docker Image

```bash
docker build -t tour-booking-frontend .
```

### Run Container

```bash
docker run -p 80:80 tour-booking-frontend
```

### Docker Compose

```bash
docker-compose up -d
```

---

## 📦 Key Features Implementation

### 1. AI Chatbot with SSE

```typescript
// chatbot.service.ts
streamChat(message: string): Observable<string> {
  const eventSource = new EventSource(
    `${this.apiUrl}/chat/stream?message=${message}`
  );
  
  return new Observable(observer => {
    eventSource.onmessage = (event) => {
      observer.next(event.data);
    };
    
    eventSource.onerror = () => {
      observer.error('Connection error');
      eventSource.close();
    };
  });
}
```

### 2. JWT Authentication Interceptor

```typescript
// auth.interceptor.ts
intercept(req: HttpRequest<any>, next: HttpHandler) {
  const token = this.authService.getToken();
  
  if (token) {
    req = req.clone({
      setHeaders: {
        Authorization: `Bearer ${token}`
      }
    });
  }
  
  return next.handle(req);
}
```

### 3. Route Guards

```typescript
// auth.guard.ts
canActivate(): boolean {
  if (this.authService.isAuthenticated()) {
    return true;
  }
  
  this.router.navigate(['/auth/login']);
  return false;
}
```

### 4. Reactive Forms with Validation

```typescript
// booking.component.ts
bookingForm = this.fb.group({
  numberOfPeople: [1, [Validators.required, Validators.min(1)]],
  contactName: ['', Validators.required],
  contactPhone: ['', [Validators.required, Validators.pattern(/^[0-9]{10}$/)]],
  specialRequests: ['']
});
```

---

## 🎨 UI/UX Features

- **Responsive Design**: Mobile-first với breakpoints cho tablet & desktop
- **Dark Mode Ready**: Theme switching support
- **Smooth Animations**: Angular Animations cho transitions
- **Loading States**: Skeleton loaders và spinners
- **Error Handling**: User-friendly error messages
- **Toast Notifications**: Real-time feedback với PrimeNG Toast
- **Accessibility**: ARIA labels và keyboard navigation

---

## 🔒 Security Features

- **XSS Protection**: Angular's built-in sanitization
- **CSRF Protection**: Token-based authentication
- **Route Guards**: Protected routes cho admin
- **Input Validation**: Client-side validation với Reactive Forms
- **Secure Storage**: Encrypted token storage

---

## 📊 Performance Optimization

- **Lazy Loading**: Feature modules loaded on demand
- **OnPush Change Detection**: Optimized rendering
- **TrackBy Functions**: Efficient ngFor rendering
- **Image Optimization**: Lazy loading images
- **Bundle Optimization**: Tree-shaking và code splitting

---

## 📄 License

MIT License © 2024

---

<p align="center">
  Made with ❤️ by SE347 Team
</p>
