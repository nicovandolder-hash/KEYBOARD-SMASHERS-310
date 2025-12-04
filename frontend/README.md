# Keyboard Smashers Frontend

A Next.js frontend for the Keyboard Smashers movie review platform.

## Features

- User Registration with form validation
- Integration with backend API
- Responsive design with dark theme

## Getting Started

### Prerequisites

- Node.js 18+ 
- npm or yarn

### Development

1. Install dependencies:
```bash
cd frontend
npm install
```

2. Create a `.env.local` file (copy from example):
```bash
cp .env.local.example .env.local
```

3. Run the development server:
```bash
npm run dev
```

4. Open [http://localhost:3000](http://localhost:3000) in your browser.

### Docker

Build and run with Docker:

```bash
docker build -t keyboard-smashers-frontend .
docker run -p 3000:3000 -e NEXT_PUBLIC_API_URL=http://localhost:8000 keyboard-smashers-frontend
```

Or use docker-compose from the root directory:

```bash
docker-compose up --build
```

## Project Structure

```
frontend/
├── src/
│   └── app/
│       ├── layout.tsx      # Root layout
│       ├── page.tsx        # Home page
│       ├── globals.css     # Global styles
│       ├── register/       # Registration page
│       │   ├── page.tsx
│       │   └── page.module.css
│       └── login/          # Login page (placeholder)
│           ├── page.tsx
│           └── page.module.css
├── public/                 # Static assets
├── Dockerfile             # Docker configuration
├── package.json
└── tsconfig.json
```

## API Integration

The frontend connects to the backend API at the URL specified by `NEXT_PUBLIC_API_URL` environment variable.

Default: `http://localhost:8000`

### Registration Endpoint

`POST /users/register`

Request body:
```json
{
  "username": "string",
  "email": "string",
  "password": "string"
}
```

## Acceptance Criteria

- [x] Build registration form
- [x] Send data to backend API
- [x] Display success or error messages
- [x] Required fields validated before submit
- [x] Successful registration → show confirmation
- [x] Duplicate email/username → show backend error
